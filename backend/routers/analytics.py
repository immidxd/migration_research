"""Aggregation resolver (Group E) — overlap-aware statistics.

Answers "how many migrants from place X, period P, vector V" WITHOUT naive
double counting. It gathers matching flows (origin within X via the territory
hierarchy, period overlap, optional vector), then applies the user-declared
flow_relations:

  - equals          → keep one representative, drop the duplicates
  - contains        → count only the maximal flow; its contained children are
                      already inside it, so they're excluded from the sum
  - disjoint        → additive (the default for unrelated flows too)
  - overlaps_unknown → cannot be safely added; the result is returned as a
                      RANGE [largest single … naive sum] with a warning

Nothing is inferred: only relations the user confirmed are used. REGION-level
records are never split into gubernias. The resolver is read-only.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import get_db


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


_MATCH_SQL = """
    WITH RECURSIVE anc AS (
        SELECT id AS tid, id AS aid FROM territories
        UNION ALL
        SELECT a.tid, t.parent_id
        FROM anc a JOIN territories t ON t.id = a.aid
        WHERE t.parent_id IS NOT NULL
    )
    SELECT
        f.id, f.count, f.count_lower, f.count_upper, f.count_method, f.vector,
        o.name AS origin_name, d.name AS destination_name,
        EXTRACT(YEAR FROM f.date_from)::int AS yf,
        EXTRACT(YEAR FROM f.date_to)::int AS yt
    FROM migration_flows f
    JOIN territories o ON o.id = f.origin_territory_id
    JOIN territories d ON d.id = f.destination_territory_id
    WHERE EXISTS (SELECT 1 FROM anc WHERE tid = f.origin_territory_id AND aid = :origin_id)
      AND (:from_year IS NULL OR f.date_to IS NULL OR EXTRACT(YEAR FROM f.date_to) >= :from_year)
      AND (:to_year IS NULL OR f.date_from IS NULL OR EXTRACT(YEAR FROM f.date_from) <= :to_year)
      AND (:vec_count = 0 OR f.vector::text = ANY(:vectors))
"""


def _effective(row: dict[str, Any]) -> tuple[float, float, float] | None:
    """(point, low, high) magnitude of a flow, or None if unknown."""
    if row["count"] is not None:
        c = float(row["count"])
        return (c, c, c)
    if row["count_lower"] is not None and row["count_upper"] is not None:
        lo, hi = float(row["count_lower"]), float(row["count_upper"])
        return ((lo + hi) / 2, lo, hi)
    return None


def _label(row: dict[str, Any]) -> str:
    yrs = f" ({row['yf']}–{row['yt']})" if row.get("yf") else ""
    return f"{row['origin_name']} → {row['destination_name']}{yrs}"


@router.get("/flow-aggregate")
def flow_aggregate(
    origin_id: int,
    from_year: int | None = None,
    to_year: int | None = None,
    vector: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    params = {
        "origin_id": origin_id,
        "from_year": from_year,
        "to_year": to_year,
        "vectors": vector or [],
        "vec_count": len(vector or []),
    }
    rows = {r["id"]: dict(r) for r in db.execute(text(_MATCH_SQL), params).mappings().all()}
    ids = list(rows)

    origin_name = db.execute(
        text("SELECT COALESCE(name_local, name) FROM territories WHERE id = :i"),
        {"i": origin_id},
    ).scalar()

    if not ids:
        return {
            "query": {"origin_id": origin_id, "origin_name": origin_name,
                      "from_year": from_year, "to_year": to_year, "vector": vector},
            "matched": 0, "resolved": None, "naive_sum": 0,
            "contributors": [], "excluded": [], "overlaps_unknown_pairs": [],
        }

    # Relations among the matched set only.
    rels = db.execute(
        text("""
            SELECT from_flow_id, to_flow_id, kind FROM flow_relations
            WHERE from_flow_id = ANY(:ids) AND to_flow_id = ANY(:ids)
        """),
        {"ids": ids},
    ).mappings().all()

    # 1) equals: union-find to collapse duplicate claims.
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for r in rels:
        if r["kind"] == "equals":
            union(r["from_flow_id"], r["to_flow_id"])

    # representative per equals-class = the member with the best count
    def quality(i):
        m = rows[i]["count_method"]
        rank = {"exact": 3, "estimate": 2, "range": 1, "unknown": 0}.get(m, 0)
        return (rank, rows[i]["count"] is not None)

    classes: dict[int, list[int]] = {}
    for i in ids:
        classes.setdefault(find(i), []).append(i)
    reps: dict[int, int] = {}
    excluded: list[dict[str, Any]] = []
    for root, members in classes.items():
        rep = max(members, key=quality)
        reps[root] = rep
        for m in members:
            if m != rep:
                excluded.append({"flow_id": m, "label": _label(rows[m]),
                                 "reason": f"дубль (=) до #{rep}"})

    rep_ids = set(reps.values())

    # 2) contains: a child contained by a COUNTED parent (also a rep) is excluded.
    contained: dict[int, int] = {}
    for r in rels:
        if r["kind"] != "contains":
            continue
        a, b = find(r["from_flow_id"]), find(r["to_flow_id"])  # a contains b
        pa, pb = reps[a], reps[b]
        if pa in rep_ids and pb in rep_ids and pa != pb and _effective(rows[pa]) is not None:
            contained[pb] = pa

    contributors_ids = [i for i in rep_ids if i not in contained]
    for child, par in contained.items():
        excluded.append({"flow_id": child, "label": _label(rows[child]),
                         "reason": f"входить у ширший потік #{par}"})

    # 3) overlaps_unknown among the contributing set → uncertainty.
    contrib_set = set(contributors_ids)
    overlap_pairs = []
    for r in rels:
        if r["kind"] != "overlaps_unknown":
            continue
        a, b = reps[find(r["from_flow_id"])], reps[find(r["to_flow_id"])]
        if a in contrib_set and b in contrib_set and a != b:
            overlap_pairs.append(sorted((a, b)))

    # sums
    contributors = []
    point = lo = hi = 0.0
    counted_points = []
    any_unknown_count = False
    for i in contributors_ids:
        eff = _effective(rows[i])
        contributors.append({
            "flow_id": i, "label": _label(rows[i]),
            "count": rows[i]["count"], "count_method": rows[i]["count_method"],
            "magnitude": None if eff is None else eff[0],
        })
        if eff is None:
            any_unknown_count = True
            continue
        point += eff[0]; lo += eff[1]; hi += eff[2]
        counted_points.append(eff[0])

    naive = 0.0
    for i in ids:
        eff = _effective(rows[i])
        if eff is not None:
            naive += eff[0]

    has_overlap_uncertainty = len(overlap_pairs) > 0
    if has_overlap_uncertainty and counted_points:
        # worst-case full overlap collapses to the largest single contributor;
        # worst-case disjoint is the additive sum.
        resolved = {"point": point, "low": max(counted_points), "high": point,
                    "has_overlap_uncertainty": True}
    else:
        resolved = {"point": point, "low": lo, "high": hi,
                    "has_overlap_uncertainty": False}
    resolved["some_counts_unknown"] = any_unknown_count

    return {
        "query": {"origin_id": origin_id, "origin_name": origin_name,
                  "from_year": from_year, "to_year": to_year, "vector": vector},
        "matched": len(ids),
        "resolved": resolved,
        "naive_sum": naive,
        "contributors": contributors,
        "excluded": excluded,
        "overlaps_unknown_pairs": overlap_pairs,
    }
