import React, { useEffect, useMemo, useRef } from "react";
import maplibregl, { Map, MapGeoJSONFeature } from "maplibre-gl";

import { useTerritoryLayer } from "../api/territories";
import { useFilters } from "../store";


// CARTO Dark Matter — CORS-enabled, no API key, looks great as a backdrop
// for thematic overlays. Works in pywebview's WKWebView (unlike some
// straight-OSM endpoints which 403 on certain user agents).
const BASE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {
    carto: {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
  layers: [
    { id: "carto", type: "raster", source: "carto" },
  ],
};

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

const MapView: React.FC = () => {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const loadedRef = useRef(false);

  const kinds = useFilters((s) => s.kinds);
  const empires = useFilters((s) => s.empires);
  const selectedId = useFilters((s) => s.selectedTerritoryId);
  const selectTerritory = useFilters((s) => s.selectTerritory);

  const countriesQ = useTerritoryLayer(["country"]);
  const regionsQ = useTerritoryLayer(["region"]);
  const portsQ = useTerritoryLayer(["port", "border_crossing"]);

  // --- init map once ---
  useEffect(() => {
    if (!ref.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: ref.current,
      style: BASE_STYLE,
      center: [25.0, 50.0],
      zoom: 4,
      attributionControl: false,
    });
    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    map.on("load", () => {
      loadedRef.current = true;

      for (const id of ["countries", "regions", "ports"] as const) {
        map.addSource(id, { type: "geojson", data: EMPTY_FC });
      }

      // Country contours — subtle, just for spatial context above the basemap
      map.addLayer({
        id: "countries-fill",
        type: "fill",
        source: "countries",
        paint: {
          "fill-color": "#2b3346",
          "fill-opacity": 0.18,
        },
      });
      map.addLayer({
        id: "countries-line",
        type: "line",
        source: "countries",
        paint: {
          "line-color": "#586484",
          "line-width": 0.6,
          "line-opacity": 0.7,
        },
      });

      // Umbrella regions — high-contrast tinted by empire so they pop
      map.addLayer({
        id: "regions-fill",
        type: "fill",
        source: "regions",
        paint: {
          "fill-color": [
            "match",
            ["get", "empire"],
            "russian_empire", "#e07b3a",
            "austro_hungarian", "#5fc3c3",
            "#b8a169",
          ],
          "fill-opacity": [
            "case",
            ["==", ["get", "id"], ["literal", -1]], 0.55,
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
            "match",
            ["get", "empire"],
            "russian_empire", "#ffcf99",
            "austro_hungarian", "#b3ecec",
            "#e9d8a6",
          ],
          "line-width": 1.5,
          "line-opacity": 0.9,
        },
      });
      map.addLayer({
        id: "regions-label",
        type: "symbol",
        source: "regions",
        layout: {
          "text-field": ["coalesce", ["get", "name_local"], ["get", "name"]],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 12,
          "text-anchor": "center",
          "text-allow-overlap": false,
          "text-padding": 4,
        },
        paint: {
          "text-color": "#f5e9d0",
          "text-halo-color": "rgba(14,17,24,0.85)",
          "text-halo-width": 1.5,
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
            3, 4, 6, 7, 10, 10,
          ],
          "circle-color": [
            "case",
            ["==", ["get", "kind"], "port"], "#ffd166",
            "#c084fc",
          ],
          "circle-stroke-color": "#0e1118",
          "circle-stroke-width": 1.8,
          "circle-opacity": 0.95,
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
          "text-color": "#f5e9d0",
          "text-halo-color": "rgba(14,17,24,0.9)",
          "text-halo-width": 1.4,
        },
      });

      // Selection halo for any layer
      map.addLayer({
        id: "selection-region",
        type: "line",
        source: "regions",
        paint: { "line-color": "#ffffff", "line-width": 3 },
        filter: ["==", ["get", "id"], -1],
      });
      map.addLayer({
        id: "selection-port",
        type: "circle",
        source: "ports",
        paint: {
          "circle-radius": 14,
          "circle-color": "rgba(255,255,255,0.1)",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
        filter: ["==", ["get", "id"], -1],
      });

      for (const lyr of ["regions-fill", "ports-circle", "countries-fill"]) {
        map.on("mouseenter", lyr, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", lyr, () => { map.getCanvas().style.cursor = ""; });
        map.on("click", lyr, (e) => {
          const f = e.features?.[0] as MapGeoJSONFeature | undefined;
          if (f?.properties?.id != null) selectTerritory(Number(f.properties.id));
        });
      }

      // Force a resize after one tick — pywebview sometimes mounts the
      // container with no width on first paint.
      setTimeout(() => map.resize(), 50);
    });

    // Also resize whenever the window changes
    const onResize = () => map.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- push data into sources whenever queries land ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;

    const filterByEmpire = (fc: GeoJSON.FeatureCollection | undefined) => {
      if (!fc) return EMPTY_FC;
      const features = fc.features.filter((f) => {
        const emp = (f.properties as any)?.empire;
        if (!emp) return true;
        return empires.has(emp);
      });
      return { type: "FeatureCollection" as const, features };
    };

    (map.getSource("countries") as maplibregl.GeoJSONSource | undefined)
      ?.setData(filterByEmpire(countriesQ.data));
    (map.getSource("regions") as maplibregl.GeoJSONSource | undefined)
      ?.setData(filterByEmpire(regionsQ.data));
    (map.getSource("ports") as maplibregl.GeoJSONSource | undefined)
      ?.setData(filterByEmpire(portsQ.data));
  }, [countriesQ.data, regionsQ.data, portsQ.data, empires]);

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
    map.setFilter("selection-region", ["==", ["get", "id"], selectedId ?? -1]);
    map.setFilter("selection-port", ["==", ["get", "id"], selectedId ?? -1]);

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
        <div className="absolute top-3 left-3 bg-panel/90 text-white/70 text-xs px-3 py-1.5 rounded-md border border-black/40">
          завантаження шарів…
        </div>
      )}
      <div className="absolute bottom-3 left-3 bg-panel/85 text-white/60 text-[10px] px-2 py-1 rounded border border-black/40">
        країни: {countriesQ.data?.features.length ?? 0} ·
        регіони: {regionsQ.data?.features.length ?? 0} ·
        точки: {portsQ.data?.features.length ?? 0}
      </div>
    </>
  );
};

export default MapView;
