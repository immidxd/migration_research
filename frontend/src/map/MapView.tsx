import React, { useEffect, useRef, useState } from "react";
// CSP-safe build of maplibre-gl: the worker is loaded from an external
// URL (set via `setWorkerUrl` below) instead of an inlined blob URL.
// pywebview's WKWebView blocks blob: workers, which caused every GeoJSON
// tile to fail with "Can't find variable: a" and left the map blank.
import maplibregl, { Map, MapGeoJSONFeature } from "maplibre-gl/dist/maplibre-gl-csp";
import "maplibre-gl/dist/maplibre-gl.css";

import { useFlowsGeoJSON } from "../api/flows";
import { useTerritoryLabels, useTerritoryLayer } from "../api/territories";
import { scopeRange, useFilters } from "../store";

// Point maplibre at the worker file we copied into public/.
// `public/` files are served at site root by CRA.
maplibregl.setWorkerUrl("/maplibre-gl-csp-worker.js");


/** Convert a 2-point LineString into a curved arc (quadratic bezier).
 *  Lifts the midpoint perpendicular to the chord, with curvature
 *  proportional to the chord length so short hops stay subtle.
 *
 *  Antimeridian handling: when |Δlon| > 180°, the shortest geographic
 *  path crosses the 180°/-180° line. We add or subtract 360° to the
 *  destination's longitude so the bezier interpolates the SHORT way.
 *  MapLibre wraps the resulting coords back into the visible map.
 *  Без цього Владивосток→Нью-Йорк йде у "недоречний" бік через всю Європу.
 */
function curveSegment(a: [number, number], b0: [number, number], steps: number): [number, number][] {
  let b = b0;
  // Antimeridian fix: pick the shorter wrap.
  const dxRaw = b[0] - a[0];
  if (dxRaw > 180) b = [b[0] - 360, b[1]];
  else if (dxRaw < -180) b = [b[0] + 360, b[1]];

  const dx = b[0] - a[0], dy = b[1] - a[1];
  const len = Math.hypot(dx, dy);
  const nx = -dy / (len || 1), ny = dx / (len || 1);
  // Gentle, capped curvature — strong lifts turned long arcs into wedge-like
  // blobs at regional zoom.
  const lift = Math.min(len * 0.1, 5);
  const mx = (a[0] + b[0]) / 2 + nx * lift;
  const my = (a[1] + b[1]) / 2 + ny * lift;
  const out: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const u = 1 - t;
    out.push([
      u * u * a[0] + 2 * u * t * mx + t * t * b[0],
      u * u * a[1] + 2 * u * t * my + t * t * b[1],
    ]);
  }
  return out;
}

/** Curve a 2-point line, or a multi-hop path (origin → waypoints → dest) by
 *  curving each consecutive segment and concatenating (deduping join points). */
function curveLine(coords: [number, number][], steps = 32): [number, number][] {
  if (coords.length < 2) return coords;
  const out: [number, number][] = [];
  for (let s = 0; s < coords.length - 1; s++) {
    const seg = curveSegment(coords[s], coords[s + 1], steps);
    out.push(...(s === 0 ? seg : seg.slice(1)));
  }
  return out;
}


// CARTO basemaps — CORS-enabled, no API key, work in pywebview's WKWebView.
// Two flavours: dark_all for our dark theme, light_all (Positron with labels)
// for the light theme. Note: the Carto CDN slug for the light Positron raster
// is `light_all`, NOT `positron` — using the wrong slug 404s every tile and
// leaves the map blank.
function makeBaseStyle(mode: "dark" | "light"): maplibregl.StyleSpecification {
  const slug = mode === "dark" ? "dark_all" : "light_all";
  return {
    version: 8,
    glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
    sources: {
      carto: {
        type: "raster",
        tiles: [
          `https://a.basemaps.cartocdn.com/${slug}/{z}/{x}/{y}@2x.png`,
          `https://b.basemaps.cartocdn.com/${slug}/{z}/{x}/{y}@2x.png`,
          `https://c.basemaps.cartocdn.com/${slug}/{z}/{x}/{y}@2x.png`,
          `https://d.basemaps.cartocdn.com/${slug}/{z}/{x}/{y}@2x.png`,
        ],
        tileSize: 256,
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
      },
    },
    layers: [{ id: "carto", type: "raster", source: "carto" }],
  };
}

function themeColors(mode: "dark" | "light") {
  return mode === "dark"
    ? {
        text: "#f5e9d0",
        halo: "rgba(14,17,24,0.85)",
        countryFill: "#2b3346",
        countryLine: "#586484",
        portStroke: "#0e1118",
        regionFillRu: "#e07b3a",  regionFillAh: "#5fc3c3",  regionFillOther: "#b8a169",
        regionLineRu: "#ffd9a8",  regionLineAh: "#c5f0f0",  regionLineOther: "#f3e2a8",
      }
    : {
        text: "#2a2724",
        halo: "rgba(255,255,255,0.92)",
        countryFill: "#d8cdb4",
        countryLine: "#9c8a66",
        portStroke: "#ffffff",
        // Saturated, slightly darker tones so colours pop on the cream basemap
        regionFillRu: "#c75a1f",  regionFillAh: "#1f8a8a",  regionFillOther: "#9c7a2a",
        regionLineRu: "#8a3a08",  regionLineAh: "#0e5a5a",  regionLineOther: "#5a4413",
      };
}

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };


type SourceSnapshot = {
  countries: GeoJSON.FeatureCollection | undefined;
  regions: GeoJSON.FeatureCollection | undefined;
  regionsLabels: GeoJSON.FeatureCollection | undefined;
  ports: GeoJSON.FeatureCollection | undefined;
  subdivisions: GeoJSON.FeatureCollection | undefined;
  subdivisionLabels: GeoJSON.FeatureCollection | undefined;
  settlements: GeoJSON.FeatureCollection | undefined;
  gubernias: GeoJSON.FeatureCollection | undefined;
  guberniaLabels: GeoJSON.FeatureCollection | undefined;
  uezds: GeoJSON.FeatureCollection | undefined;
  flows: any;
  empires: Set<string>;
  vectors: Set<string>;
  scope: any;
};

/** Single point of truth for pushing data into the four map sources.
 *  Called both inside the style 'load' handler (synchronous initial push)
 *  and from a useEffect whenever inputs change — same logic either way so
 *  there's no second code path that can drift. */
function pushAllData(
  map: Map,
  s: SourceSnapshot,
  setCounts: (c: { c: number; r: number; p: number; f: number }) => void,
) {
  const scopeR = scopeRange(s.scope);
  // Region role from the (vector-filtered) flows: a region that is a flow
  // DESTINATION reads as a receiver (saturated fill); an ORIGIN as a homeland
  // (medium fill); neither → faint. Drives the fill gradation the user asked for.
  const receiverIds = new Set<number>();
  const originIds = new Set<number>();
  for (const f of (s.flows?.features ?? []) as any[]) {
    if (!s.vectors.has(f.properties.vector)) continue;
    if (f.properties.destination_territory_id != null) receiverIds.add(f.properties.destination_territory_id);
    if (f.properties.origin_territory_id != null) originIds.add(f.properties.origin_territory_id);
  }
  const roleOf = (id: any): string =>
    receiverIds.has(id) ? "receiver" : originIds.has(id) ? "origin" : "none";

  const tag = (f: GeoJSON.Feature) => {
    const p: any = f.properties || {};
    const inScope = !scopeR || (
      (p.valid_year_from == null || p.valid_year_from <= scopeR[1]) &&
      (p.valid_year_to == null || p.valid_year_to >= scopeR[0])
    );
    return { ...f, properties: { ...p, in_scope: inScope, role: roleOf(p.id) } };
  };
  const empiresFilter = (fc: GeoJSON.FeatureCollection | undefined) => {
    if (!fc) return EMPTY_FC;
    const features = fc.features
      .filter((f) => {
        const e = (f.properties as any)?.empire;
        return !e || s.empires.has(e);
      })
      .map(tag);
    return { type: "FeatureCollection" as const, features };
  };

  const cFC = empiresFilter(s.countries);
  const rFC = empiresFilter(s.regions);
  const rLFC = empiresFilter(s.regionsLabels);
  const pFC = empiresFilter(s.ports);
  const subFC = empiresFilter(s.subdivisions);
  const subLFC = empiresFilter(s.subdivisionLabels);
  const setFC = empiresFilter(s.settlements);
  const gubFC = empiresFilter(s.gubernias);
  const gubLFC = empiresFilter(s.guberniaLabels);
  const uezdFC = empiresFilter(s.uezds);

  const flowFC = s.flows
    ? {
        type: "FeatureCollection" as const,
        features: (s.flows.features as any[])
          .filter((f) => s.vectors.has(f.properties.vector))
          .map((f) => ({
            ...f,
            geometry: {
              type: "LineString" as const,
              coordinates: curveLine(f.geometry.coordinates as [number, number][]),
            },
          })),
      }
    : EMPTY_FC;

  (map.getSource("countries") as maplibregl.GeoJSONSource | undefined)?.setData(cFC);
  (map.getSource("regions") as maplibregl.GeoJSONSource | undefined)?.setData(rFC);
  (map.getSource("regions-labels") as maplibregl.GeoJSONSource | undefined)?.setData(rLFC);
  (map.getSource("ports") as maplibregl.GeoJSONSource | undefined)?.setData(pFC);
  (map.getSource("subdivisions") as maplibregl.GeoJSONSource | undefined)?.setData(subFC);
  (map.getSource("subdivisions-labels") as maplibregl.GeoJSONSource | undefined)?.setData(subLFC);
  (map.getSource("settlements") as maplibregl.GeoJSONSource | undefined)?.setData(setFC);
  (map.getSource("gubernias") as maplibregl.GeoJSONSource | undefined)?.setData(gubFC);
  (map.getSource("gubernias-labels") as maplibregl.GeoJSONSource | undefined)?.setData(gubLFC);
  (map.getSource("uezds") as maplibregl.GeoJSONSource | undefined)?.setData(uezdFC);
  (map.getSource("flows") as maplibregl.GeoJSONSource | undefined)?.setData(flowFC);

  setCounts({
    c: cFC.features.length,
    r: rFC.features.length,
    p: pFC.features.length,
    f: flowFC.features.length,
  });
}

const MapView: React.FC = () => {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const loadedRef = useRef(false);

  const kinds = useFilters((s) => s.kinds);
  const empires = useFilters((s) => s.empires);
  const selectedId = useFilters((s) => s.selectedTerritoryId);
  const selectTerritory = useFilters((s) => s.selectTerritory);
  const openFlowEditor = useFilters((s) => s.openFlowEditor);
  const scope = useFilters((s) => s.scope);
  const themeMode = useFilters((s) => s.theme);
  const vectorsState = useFilters((s) => s.vectors);

  const countriesQ = useTerritoryLayer(["country"]);
  const regionsQ = useTerritoryLayer(["region"]);
  // Labels reflect the period-appropriate name for a single chosen year
  // (e.g. "Королівство Гаваї" vs "Гаваї (США)"); only meaningful in year mode.
  const labelYear = scope.mode === "year" ? scope.year : undefined;
  const regionsLabelsQ = useTerritoryLabels(["region"], labelYear);
  const portsQ = useTerritoryLayer(["port", "border_crossing"]);
  // Destination layers (North America etc.): states/provinces as polygons and
  // cities as points. Subdivision labels are year-aware (Hawaii Kingdom → US).
  const subdivisionsQ = useTerritoryLayer(["subdivision"]);
  const subdivisionLabelsQ = useTerritoryLabels(["subdivision"], labelYear);
  const settlementsQ = useTerritoryLayer(["settlement"]);
  // Gubernias: real RiStat borders, the main unit migrants are recorded from.
  // Uezds are heavier (824 polygons) so only fetched when their toggle is on.
  const guberniasQ = useTerritoryLayer(["gubernia"]);
  const guberniaLabelsQ = useTerritoryLabels(["gubernia"]);
  const uezdsQ = useTerritoryLayer(kinds.has("uezd") ? ["uezd"] : []);
  // Filter flows by the active temporal scope's canonical year range — works
  // for year / range / label modes alike (null when no scope is set).
  const scopeR = scopeRange(scope);
  const flowsQ = useFlowsGeoJSON({
    from_year: scopeR?.[0],
    to_year: scopeR?.[1],
  });

  // --- Ref that always holds the freshest query data + filter state.
  // Used so the synchronous load-handler can push initial data without
  // depending on React's effect-scheduling order (which was the source of
  // the "polygons never appear" bug).
  const stateRef = useRef({
    countries: undefined as GeoJSON.FeatureCollection | undefined,
    regions: undefined as GeoJSON.FeatureCollection | undefined,
    regionsLabels: undefined as GeoJSON.FeatureCollection | undefined,
    ports: undefined as GeoJSON.FeatureCollection | undefined,
    subdivisions: undefined as GeoJSON.FeatureCollection | undefined,
    subdivisionLabels: undefined as GeoJSON.FeatureCollection | undefined,
    settlements: undefined as GeoJSON.FeatureCollection | undefined,
    gubernias: undefined as GeoJSON.FeatureCollection | undefined,
    guberniaLabels: undefined as GeoJSON.FeatureCollection | undefined,
    uezds: undefined as GeoJSON.FeatureCollection | undefined,
    flows: undefined as any,
    empires,
    vectors: vectorsState,
    scope,
  });
  stateRef.current = {
    countries: countriesQ.data,
    regions: regionsQ.data,
    regionsLabels: regionsLabelsQ.data,
    ports: portsQ.data,
    subdivisions: subdivisionsQ.data,
    subdivisionLabels: subdivisionLabelsQ.data,
    settlements: settlementsQ.data,
    gubernias: guberniasQ.data,
    guberniaLabels: guberniaLabelsQ.data,
    uezds: uezdsQ.data,
    flows: flowsQ.data,
    empires,
    vectors: vectorsState,
    scope,
  };

  // Counts after empires/vectors filtering, surfaced in the bottom-left chip
  const [renderedCounts, setRenderedCounts] = useState({ c: 0, r: 0, p: 0, f: 0 });

  // --- init map once ---
  useEffect(() => {
    if (!ref.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: ref.current,
      style: makeBaseStyle(themeMode),
      // Fit to Ukraine + neighbours so the umbrella regions are immediately
      // visible without scrolling. Roughly: from Galicia (21°E) to the Don
      // (40°E) and from the Baltic (52°N) down to the Crimean coast (44°N).
      bounds: [[20, 43], [42, 53]],
      fitBoundsOptions: { padding: 24 },
      attributionControl: false,
    });
    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    // Surface maplibre runtime errors with full detail (not just "fire" frames).
    map.on("error", (e: any) => {
      const err = e && e.error ? e.error : e;
      // eslint-disable-next-line no-console
      console.error("[MAP ERROR]", err && err.message, err && err.stack, e);
    });

    const onLoad = () => {
      try {
        loadedRef.current = true;
      const C = themeColors(themeMode);

      for (const id of [
        "countries", "regions", "regions-labels", "ports",
        "subdivisions", "subdivisions-labels", "settlements",
        "gubernias", "gubernias-labels", "uezds", "flows",
      ] as const) {
        map.addSource(id, { type: "geojson", data: EMPTY_FC });
      }


      // Country contours — subtle, just for spatial context above the basemap
      map.addLayer({
        id: "countries-fill",
        type: "fill",
        source: "countries",
        paint: {
          "fill-color": C.countryFill,
          "fill-opacity": 0.18,
        },
      });
      map.addLayer({
        id: "countries-line",
        type: "line",
        source: "countries",
        paint: {
          "line-color": C.countryLine,
          "line-width": 0.6,
          "line-opacity": 0.7,
        },
      });

      // Umbrella regions (`is_umbrella_region=true`, e.g. Treadgold's
      // European/Asiatic Russia) get OUTLINE ONLY at low opacity — they
      // are conceptual containers and shouldn't paint over the regions
      // nested inside them. Regular regions get a soft fill.
      map.addLayer({
        id: "regions-fill",
        type: "fill",
        source: "regions",
        // Fill every meaningful region; the big aggregation containers
        // (Наддніпрянщина, European/Asian Russia, the empire) are flagged
        // is_container and stay outline-only so they don't paint over nested
        // regions.
        filter: ["!=", ["get", "is_container"], true],
        paint: {
          "fill-color": [
            "match",
            ["get", "empire"],
            "russian_empire", C.regionFillRu,
            "austro_hungarian", C.regionFillAh,
            C.regionFillOther,
          ],
          // Visual gradation by role: receiver (flow destination) strongest,
          // origin (homeland) medium, unused region faint.
          "fill-opacity": [
            "case",
            ["==", ["get", "in_scope"], false], 0.06,
            ["==", ["get", "id"], selectedId ?? -1], 0.82,
            ["==", ["get", "role"], "receiver"], 0.62,
            ["==", ["get", "role"], "origin"], 0.42,
            0.26,
          ],
        },
      });
      map.addLayer({
        id: "regions-outline",
        type: "line",
        source: "regions",
        paint: {
          "line-color": [
            "match", ["get", "empire"],
            "russian_empire", C.regionLineRu,
            "austro_hungarian", C.regionLineAh,
            C.regionLineOther,
          ],
          "line-width": [
            "case",
            ["==", ["get", "id"], selectedId ?? -1], 2,
            ["==", ["get", "is_container"], true], 0.8,
            1.2,
          ],
          "line-opacity": [
            "case",
            ["==", ["get", "in_scope"], false], 0.15,
            ["==", ["get", "is_container"], true], 0.45,
            0.75,
          ],
          "line-dasharray": [1, 0],
        },
      });
      // Optional dashed outline ONLY for umbrella regions, painted on top
      // of the solid outline. Adds visual distinction without expression
      // problems (constant dasharray, layer filter does the selection).
      map.addLayer({
        id: "regions-outline-umbrella",
        type: "line",
        source: "regions",
        filter: ["==", ["get", "is_container"], true],
        paint: {
          "line-color": [
            "match", ["get", "empire"],
            "russian_empire", C.regionLineRu,
            "austro_hungarian", C.regionLineAh,
            C.regionLineOther,
          ],
          "line-width": 1.5,
          "line-opacity": 0.6,
          "line-dasharray": [4, 4],
        },
      });
      // Labels come from a SEPARATE source whose features are Point geoms
      // (one ST_PointOnSurface per Territory, computed server-side). This
      // eliminates the maplibre default of placing one label per polygon
      // PART in MultiPolygons — Сибір used to label every island.
      map.addLayer({
        id: "regions-label",
        type: "symbol",
        source: "regions-labels",
        layout: {
          "text-field": ["coalesce", ["get", "name_local"], ["get", "name"]],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": [
            "case",
            ["==", ["get", "is_container"], true], 11,
            13,
          ],
          "text-allow-overlap": false,
          "text-ignore-placement": false,
          "text-padding": 8,
        },
        paint: {
          "text-color": [
            "case",
            ["==", ["get", "is_container"], true], C.regionLineRu,
            C.text,
          ],
          "text-halo-color": C.halo,
          "text-halo-width": 1.6,
          "text-opacity": [
            "case",
            ["==", ["get", "is_container"], true], 0.65,
            1,
          ],
        },
      });

      // Ports & border crossings
      map.addLayer({
        id: "ports-circle",
        type: "circle",
        source: "ports",
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            3, 6, 6, 9, 10, 13,
          ],
          "circle-color": [
            "case",
            ["==", ["get", "kind"], "port"], "#ffd166",
            "#c084fc",
          ],
          "circle-stroke-color": C.portStroke,
          "circle-stroke-width": 2,
          "circle-opacity": 1,
        },
      });
      map.addLayer({
        id: "ports-label",
        type: "symbol",
        source: "ports",
        minzoom: 4,
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 11,
          "text-offset": [0, 1.1],
          "text-anchor": "top",
          "text-optional": true,
        },
        paint: {
          "text-color": C.text,
          "text-halo-color": C.halo,
          "text-halo-width": 1.4,
        },
      });

      // Uezds (districts) — finest level, faint borders, only at deep zoom.
      map.addLayer({
        id: "uezds-line",
        type: "line",
        source: "uezds",
        minzoom: 6.5,
        paint: {
          "line-color": "#9a8c6e",
          "line-width": 0.5,
          "line-opacity": ["interpolate", ["linear"], ["zoom"], 6.5, 0, 8, 0.5],
        },
      });
      map.addLayer({
        id: "uezds-label",
        type: "symbol",
        source: "uezds",
        minzoom: 8,
        layout: {
          "text-field": ["coalesce", ["get", "name_local"], ["get", "name"]],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 9,
          "text-allow-overlap": false,
          "text-padding": 4,
        },
        paint: { "text-color": C.text, "text-halo-color": C.halo, "text-halo-width": 1.1, "text-opacity": 0.8 },
      });

      // Gubernias — the main working unit: real RiStat borders. Drawn above
      // region fills so they subdivide the macro-regions; appear from mid zoom.
      map.addLayer({
        id: "gubernias-line",
        type: "line",
        source: "gubernias",
        minzoom: 4,
        paint: {
          "line-color": "#cdb98c",
          "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.5, 7, 1.4],
          "line-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.45, 6, 0.85],
        },
      });
      map.addLayer({
        id: "gubernias-label",
        type: "symbol",
        source: "gubernias-labels",
        minzoom: 5.5,
        layout: {
          "text-field": ["coalesce", ["get", "name_local"], ["get", "name"]],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 11,
          "text-allow-overlap": false,
          "text-padding": 6,
        },
        paint: { "text-color": C.text, "text-halo-color": C.halo, "text-halo-width": 1.3 },
      });

      // Subdivisions (US states / Canadian provinces) — soft fill + outline,
      // drawn above countries so destination units read clearly.
      map.addLayer({
        id: "subdivisions-fill",
        type: "fill",
        source: "subdivisions",
        paint: { "fill-color": "#6b8cce", "fill-opacity": 0.12 },
      });
      map.addLayer({
        id: "subdivisions-line",
        type: "line",
        source: "subdivisions",
        paint: { "line-color": "#8aa4d8", "line-width": 0.8, "line-opacity": 0.65 },
      });
      map.addLayer({
        id: "subdivisions-label",
        type: "symbol",
        source: "subdivisions-labels",
        minzoom: 3.5,
        layout: {
          "text-field": ["coalesce", ["get", "name_local"], ["get", "name"]],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 11,
          "text-allow-overlap": false,
          "text-padding": 6,
        },
        paint: {
          "text-color": C.text,
          "text-halo-color": C.halo,
          "text-halo-width": 1.4,
        },
      });

      // Settlements (destination cities) — small circles + labels.
      map.addLayer({
        id: "settlements-circle",
        type: "circle",
        source: "settlements",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 8, 6],
          "circle-color": "#7dd6f6",
          "circle-stroke-color": C.portStroke,
          "circle-stroke-width": 1.5,
        },
      });
      map.addLayer({
        id: "settlements-label",
        type: "symbol",
        source: "settlements",
        minzoom: 4.5,
        layout: {
          "text-field": ["coalesce", ["get", "name_local"], ["get", "name"]],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 10,
          "text-offset": [0, 1],
          "text-anchor": "top",
          "text-optional": true,
        },
        paint: {
          "text-color": C.text,
          "text-halo-color": C.halo,
          "text-halo-width": 1.3,
        },
      });

      // --- Flow arcs: minimalist. Width scales with the number of people, so
      // big movements read as thick ribbons and small ones as hairlines.
      const VECTOR_COLOR: any = [
        "match", ["get", "vector"],
        "transatlantic", "#ff8c8c",
        "european", "#7dd6f6",
        "intra_imperial_east", "#c89bf6",
        "intra_imperial_other", "#fcd968",
        "internal", "#a7d685",
        "#cfcfcf",
      ];
      const FLOW_WIDTH: any = [
        "interpolate", ["linear"], ["coalesce", ["get", "count"], 5000],
        0, 1,
        20000, 1.6,
        100000, 2.6,
        400000, 3.8,
        1200000, 5.5,
      ];

      // Faint underlay glow (thin, low opacity) — just enough to lift arcs off
      // the basemap without the old fat blur.
      map.addLayer({
        id: "flows-glow",
        type: "line",
        source: "flows",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": VECTOR_COLOR,
          "line-width": ["*", FLOW_WIDTH, 2.4],
          "line-blur": 2.5,
          "line-opacity": 0.12,
        },
      });
      map.addLayer({
        id: "flows-line",
        type: "line",
        source: "flows",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": VECTOR_COLOR,
          "line-width": FLOW_WIDTH,
          "line-opacity": ["case", ["get", "provisional"], 0.45, 0.78],
        },
      });
      // Hover highlight: brightened, slightly thicker copy drawn only for the
      // hovered flow + its sub-flows (filter set on mousemove).
      map.addLayer({
        id: "flows-hover",
        type: "line",
        source: "flows",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": VECTOR_COLOR,
          "line-width": ["+", FLOW_WIDTH, 1.5],
          "line-opacity": 1,
        },
        filter: ["==", ["get", "id"], -1],
      });
      // Direction arrows — subtle, only on the hovered flow to avoid clutter.
      map.addLayer({
        id: "flows-arrow",
        type: "symbol",
        source: "flows",
        layout: {
          "symbol-placement": "line",
          "symbol-spacing": 140,
          "text-field": "▶",
          "text-size": 12,
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-keep-upright": false,
          "text-rotation-alignment": "map",
          "text-pitch-alignment": "map",
          "text-allow-overlap": true,
          "text-ignore-placement": true,
        },
        paint: {
          "text-color": VECTOR_COLOR,
          "text-halo-color": C.halo,
          "text-halo-width": 1.4,
          "text-opacity": 0.95,
        },
        filter: ["==", ["get", "id"], -1],
      });

      // Selection halo for any layer
      const haloColor = themeMode === "dark" ? "#ffffff" : "#111111";
      // Wide outer glow for selected region
      map.addLayer({
        id: "selection-region-glow",
        type: "line",
        source: "regions",
        paint: {
          "line-color": haloColor,
          "line-width": 5,
          "line-blur": 3,
          "line-opacity": 0.2,
        },
        filter: ["==", ["get", "id"], -1],
      });
      map.addLayer({
        id: "selection-region",
        type: "line",
        source: "regions",
        paint: { "line-color": haloColor, "line-width": 1.6, "line-opacity": 0.85 },
        filter: ["==", ["get", "id"], -1],
      });
      map.addLayer({
        id: "selection-port",
        type: "circle",
        source: "ports",
        paint: {
          "circle-radius": 16,
          "circle-color": themeMode === "dark"
            ? "rgba(255,255,255,0.15)"
            : "rgba(0,0,0,0.15)",
          "circle-stroke-color": haloColor,
          "circle-stroke-width": 3,
        },
        filter: ["==", ["get", "id"], -1],
      });

      for (const lyr of ["regions-fill", "ports-circle", "countries-fill", "subdivisions-fill", "settlements-circle", "flows-line"]) {
        map.on("mouseenter", lyr, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", lyr, () => { map.getCanvas().style.cursor = ""; });
      }
      for (const lyr of ["regions-fill", "ports-circle", "countries-fill", "subdivisions-fill", "settlements-circle"]) {
        map.on("click", lyr, (e) => {
          const f = e.features?.[0] as MapGeoJSONFeature | undefined;
          if (f?.properties?.id != null) selectTerritory(Number(f.properties.id));
        });
      }

      // --- Flow hover: highlight the hovered flow + its sub-flows, show a
      // summary popup, and open the editor on click.
      const flowPopup = new maplibregl.Popup({
        closeButton: false, closeOnClick: false, offset: 12, className: "flow-popup",
      });
      const fmtNum = (n: any) => (n == null ? null : Number(n).toLocaleString("uk"));
      const onFlowMove = (e: any) => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const p: any = f.properties || {};
        let kids: number[] = [];
        try {
          kids = typeof p.child_ids === "string" ? JSON.parse(p.child_ids) : (p.child_ids || []);
        } catch { kids = []; }
        const ids = [Number(p.id), ...kids.map(Number)];
        const filt = ["in", ["get", "id"], ["literal", ids]] as any;
        map.setFilter("flows-hover", filt);
        map.setFilter("flows-arrow", filt);
        const amount = p.count != null ? `${fmtNum(p.count)} осіб`
          : p.count_lower != null ? `${fmtNum(p.count_lower)}–${fmtNum(p.count_upper)} осіб`
          : "кількість невідома";
        const period = p.temporal_label || (p.date_from ? `${p.date_from}→${p.date_to}` : "");
        const sub = ids.length > 1 ? `<div style="opacity:.6;margin-top:3px">+ ${ids.length - 1} підпотік(ів)</div>` : "";
        flowPopup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div style="font:12px/1.35 system-ui">
               <div style="font-weight:600">${p.origin_name} → ${p.destination_name}</div>
               <div style="opacity:.75;margin-top:2px">${amount}${period ? " · " + period : ""}</div>
               ${sub}
               <div style="opacity:.5;margin-top:5px">клік — редагувати</div>
             </div>`
          )
          .addTo(map);
      };
      const onFlowLeave = () => {
        map.getCanvas().style.cursor = "";
        map.setFilter("flows-hover", ["==", ["get", "id"], -1] as any);
        map.setFilter("flows-arrow", ["==", ["get", "id"], -1] as any);
        flowPopup.remove();
      };
      map.on("mousemove", "flows-line", onFlowMove);
      map.on("mouseleave", "flows-line", onFlowLeave);
      map.on("click", "flows-line", (e) => {
        const f = e.features?.[0];
        if (f?.properties?.id != null) openFlowEditor(Number(f.properties.id));
      });

      // Force a resize after one tick — pywebview sometimes mounts the
      // container with no width on first paint.
      setTimeout(() => map.resize(), 50);

      // --- Synchronous initial data push, using the freshest values from
      // the ref. This sidesteps any React effect-scheduling race; the
      // sources are now never left empty after style load.
      pushAllData(map, stateRef.current, setRenderedCounts);
      console.log("[MapView] load complete. layers:", map.getStyle().layers.map((l: any) => l.id));
      } catch (err) {
        console.error("[MapView] load handler crashed:", err);
      }
    };
    map.on("load", onLoad);

    // Also resize whenever the window changes
    const onResize = () => map.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
    // Re-init when the theme changes so the basemap, label colors, and
    // selection halos all swap together. (Avoids per-layer paint updates.)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [themeMode]);

  // --- push data into sources whenever queries land ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    pushAllData(map, stateRef.current, setRenderedCounts);

  }, [countriesQ.data, regionsQ.data, portsQ.data, subdivisionsQ.data, subdivisionLabelsQ.data, settlementsQ.data, guberniasQ.data, guberniaLabelsQ.data, uezdsQ.data, flowsQ.data, empires, scope, vectorsState]);


  // --- visibility toggles ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const showCountry = kinds.has("country");
    const showRegion = kinds.has("region");
    const showPort = kinds.has("port") || kinds.has("border_crossing");
    const showSubdivision = kinds.has("subdivision");
    const showSettlement = kinds.has("settlement");
    const showGubernia = kinds.has("gubernia");
    const showUezd = kinds.has("uezd");
    const toggle: Array<[string, boolean]> = [
      ["countries-fill", showCountry],
      ["countries-line", showCountry],
      ["regions-fill", showRegion],
      ["regions-outline", showRegion],
      ["regions-label", showRegion],
      ["ports-circle", showPort],
      ["ports-label", showPort],
      ["subdivisions-fill", showSubdivision],
      ["subdivisions-line", showSubdivision],
      ["subdivisions-label", showSubdivision],
      ["settlements-circle", showSettlement],
      ["settlements-label", showSettlement],
      ["gubernias-line", showGubernia],
      ["gubernias-label", showGubernia],
      ["uezds-line", showUezd],
      ["uezds-label", showUezd],
    ];
    for (const [id, on] of toggle) {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
      }
    }
  }, [kinds]);

  // --- selection halo + flyTo ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const selFilter = ["==", ["get", "id"], selectedId ?? -1] as any;
    if (map.getLayer("selection-region-glow")) map.setFilter("selection-region-glow", selFilter);
    if (map.getLayer("selection-region")) map.setFilter("selection-region", selFilter);
    if (map.getLayer("selection-port")) map.setFilter("selection-port", selFilter);
    // Also re-run the regions-fill paint so the selected polygon brightens
    if (map.getLayer("regions-fill")) {
      map.setPaintProperty("regions-fill", "fill-opacity", [
        "case",
        ["==", ["get", "in_scope"], false], 0.06,
        ["==", ["get", "id"], selectedId ?? -1], 0.85,
        ["==", ["get", "role"], "receiver"], 0.62,
        ["==", ["get", "role"], "origin"], 0.42,
        0.26,
      ] as any);
    }
    if (map.getLayer("regions-outline")) {
      map.setPaintProperty("regions-outline", "line-width", [
        "case",
        ["==", ["get", "id"], selectedId ?? -1], 2,
        1.2,
      ] as any);
    }

    if (selectedId == null) return;
    const findIn = (fc?: GeoJSON.FeatureCollection) =>
      fc?.features.find((f) => (f.properties as any)?.id === selectedId);
    const f = findIn(regionsQ.data) || findIn(portsQ.data) || findIn(countriesQ.data);
    if (!f) return;
    const g = f.geometry as any;
    if (g?.type === "Point") {
      map.flyTo({ center: g.coordinates, zoom: 6, speed: 1.2 });
    } else if (g?.type === "Polygon" || g?.type === "MultiPolygon") {
      // crude bounding box from coordinates
      const coords: number[][] = g.type === "Polygon" ? g.coordinates[0] : g.coordinates[0][0];
      const xs = coords.map((c) => c[0]);
      const ys = coords.map((c) => c[1]);
      map.fitBounds(
        [[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]],
        { padding: 80, maxZoom: 7, duration: 800 }
      );
    }
  }, [selectedId, regionsQ.data, portsQ.data, countriesQ.data]);

  const loading = countriesQ.isLoading || regionsQ.isLoading || portsQ.isLoading;

  return (
    <>
      <div ref={ref} style={{ position: "absolute", inset: 0 }} />
      {loading && (
        <div
          className="absolute top-3 left-3 text-xs px-3 py-1.5 rounded-md"
          style={{
            background: "var(--bg-panel-soft)",
            color: "var(--text-muted)",
            border: "1px solid var(--border)",
          }}
        >
          завантаження шарів…
        </div>
      )}
      <div
        className="absolute bottom-3 left-3 text-[10px] px-2 py-1 rounded"
        style={{
          background: "var(--bg-panel-soft)",
          color: "var(--text-muted)",
          border: "1px solid var(--border)",
        }}
      >
        намальовано: країн {renderedCounts.c} · регіонів {renderedCounts.r} ·
        точок {renderedCounts.p} · потоків {renderedCounts.f}
        {scope.mode !== "none" && (
          <span className="ml-2 text-accent">
            ↳ {scope.mode === "year" ? `рік ${scope.year}` :
                scope.mode === "range" ? `${scope.yearFrom}–${scope.yearTo}` :
                scope.label.label}
          </span>
        )}
      </div>
    </>
  );
};

export default MapView;
