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
 */
function curveLine(coords: [number, number][], steps = 32): [number, number][] {
  if (coords.length !== 2) return coords;
  const [a, b] = coords;
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const len = Math.hypot(dx, dy);
  // Perpendicular unit vector
  const nx = -dy / (len || 1), ny = dx / (len || 1);
  // Curvature: 18% of chord length, capped
  const lift = Math.min(len * 0.18, 12);
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
  const tag = (f: GeoJSON.Feature) => {
    const p: any = f.properties || {};
    const inScope = !scopeR || (
      (p.valid_year_from == null || p.valid_year_from <= scopeR[1]) &&
      (p.valid_year_to == null || p.valid_year_to >= scopeR[0])
    );
    return { ...f, properties: { ...p, in_scope: inScope } };
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
  const scope = useFilters((s) => s.scope);
  const themeMode = useFilters((s) => s.theme);
  const vectorsState = useFilters((s) => s.vectors);

  const countriesQ = useTerritoryLayer(["country"]);
  const regionsQ = useTerritoryLayer(["region"]);
  const regionsLabelsQ = useTerritoryLabels(["region"]);
  const portsQ = useTerritoryLayer(["port", "border_crossing"]);
  const flowsQ = useFlowsGeoJSON({
    covering_year: scope.mode === "year" ? scope.year : undefined,
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

      for (const id of ["countries", "regions", "regions-labels", "ports", "flows"] as const) {
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
        filter: ["!=", ["get", "is_umbrella_region"], true],
        paint: {
          "fill-color": [
            "match",
            ["get", "empire"],
            "russian_empire", C.regionFillRu,
            "austro_hungarian", C.regionFillAh,
            C.regionFillOther,
          ],
          "fill-opacity": [
            "case",
            ["==", ["get", "in_scope"], false], 0.05,
            ["==", ["get", "id"], selectedId ?? -1], 0.7,
            0.32,
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
            ["==", ["get", "id"], selectedId ?? -1], 3.5,
            ["==", ["get", "is_umbrella_region"], true], 1.2,
            2,
          ],
          "line-opacity": [
            "case",
            ["==", ["get", "in_scope"], false], 0.15,
            ["==", ["get", "is_umbrella_region"], true], 0.5,
            0.9,
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
        filter: ["==", ["get", "is_umbrella_region"], true],
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
            ["==", ["get", "is_umbrella_region"], true], 11,
            13,
          ],
          "text-allow-overlap": false,
          "text-ignore-placement": false,
          "text-padding": 8,
        },
        paint: {
          "text-color": [
            "case",
            ["==", ["get", "is_umbrella_region"], true], C.regionLineRu,
            C.text,
          ],
          "text-halo-color": C.halo,
          "text-halo-width": 1.6,
          "text-opacity": [
            "case",
            ["==", ["get", "is_umbrella_region"], true], 0.65,
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

      // Flow arcs — soft glow underlay for legibility
      map.addLayer({
        id: "flows-glow",
        type: "line",
        source: "flows",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": [
            "match", ["get", "vector"],
            "transatlantic", "#ff6b6b",
            "european", "#4cc9f0",
            "intra_imperial_east", "#9b5de5",
            "intra_imperial_other", "#f9c74f",
            "internal", "#90be6d",
            "#cccccc",
          ],
          "line-width": 9,
          "line-blur": 4,
          "line-opacity": 0.32,
        },
      });
      // Per-vector colours now that we know the basic rendering works.
      map.addLayer({
        id: "flows-line",
        type: "line",
        source: "flows",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": [
            "match", ["get", "vector"],
            "transatlantic", "#ff8c8c",
            "european", "#7dd6f6",
            "intra_imperial_east", "#c89bf6",
            "intra_imperial_other", "#fcd968",
            "internal", "#a7d685",
            "#dddddd",
          ],
          "line-width": 3.5,
          "line-opacity": 0.95,
        },
      });
      // flows-label intentionally omitted for now — re-add after confirming
      // the basic line rendering works in WKWebView.

      // Selection halo for any layer
      const haloColor = themeMode === "dark" ? "#ffffff" : "#111111";
      // Wide outer glow for selected region
      map.addLayer({
        id: "selection-region-glow",
        type: "line",
        source: "regions",
        paint: {
          "line-color": haloColor,
          "line-width": 12,
          "line-blur": 6,
          "line-opacity": 0.35,
        },
        filter: ["==", ["get", "id"], -1],
      });
      map.addLayer({
        id: "selection-region",
        type: "line",
        source: "regions",
        paint: { "line-color": haloColor, "line-width": 4 },
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

      for (const lyr of ["regions-fill", "ports-circle", "countries-fill", "flows-line"]) {
        map.on("mouseenter", lyr, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", lyr, () => { map.getCanvas().style.cursor = ""; });
      }
      for (const lyr of ["regions-fill", "ports-circle", "countries-fill"]) {
        map.on("click", lyr, (e) => {
          const f = e.features?.[0] as MapGeoJSONFeature | undefined;
          if (f?.properties?.id != null) selectTerritory(Number(f.properties.id));
        });
      }

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

  }, [countriesQ.data, regionsQ.data, portsQ.data, flowsQ.data, empires, scope, vectorsState]);


  // --- visibility toggles ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const showCountry = kinds.has("country");
    const showRegion = kinds.has("region");
    const showPort = kinds.has("port") || kinds.has("border_crossing");
    const toggle: Array<[string, boolean]> = [
      ["countries-fill", showCountry],
      ["countries-line", showCountry],
      ["regions-fill", showRegion],
      ["regions-outline", showRegion],
      ["regions-label", showRegion],
      ["ports-circle", showPort],
      ["ports-label", showPort],
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
        ["==", ["get", "in_scope"], false], 0.08,
        ["==", ["get", "id"], selectedId ?? -1], 0.85,
        0.55,
      ] as any);
    }
    if (map.getLayer("regions-outline")) {
      map.setPaintProperty("regions-outline", "line-width", [
        "case",
        ["==", ["get", "id"], selectedId ?? -1], 4,
        2.5,
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
