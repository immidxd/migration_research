import React, { useEffect, useMemo, useRef } from "react";
import maplibregl, { Map, MapGeoJSONFeature } from "maplibre-gl";

import { useTerritoryLayer } from "../api/territories";
import { useFilters } from "../store";

const BASE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [
    { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.45 } },
  ],
};

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

const MapView: React.FC = () => {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);

  const kinds = useFilters((s) => s.kinds);
  const empires = useFilters((s) => s.empires);
  const selectedId = useFilters((s) => s.selectedTerritoryId);
  const selectTerritory = useFilters((s) => s.selectTerritory);

  const activeKinds = useMemo(() => Array.from(kinds), [kinds]);
  const activeEmpires = useMemo(() => empires, [empires]);

  // Always fetch all four layers; filter visibility client-side via the
  // store toggles. Keeps the network quiet when the user clicks toggles.
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
    });
    mapRef.current = map;

    map.on("load", () => {
      for (const id of ["countries", "regions", "ports"] as const) {
        map.addSource(id, { type: "geojson", data: EMPTY_FC });
      }

      map.addLayer({
        id: "countries-fill",
        type: "fill",
        source: "countries",
        paint: {
          "fill-color": "#1a2942",
          "fill-opacity": 0.35,
        },
      });
      map.addLayer({
        id: "countries-line",
        type: "line",
        source: "countries",
        paint: { "line-color": "#3a4a6b", "line-width": 0.4 },
      });

      map.addLayer({
        id: "regions-fill",
        type: "fill",
        source: "regions",
        paint: {
          "fill-color": [
            "match",
            ["get", "empire"],
            "russian_empire", "#c97e3a",
            "austro_hungarian", "#5ea3a3",
            "#999999",
          ],
          "fill-opacity": 0.35,
        },
      });
      map.addLayer({
        id: "regions-outline",
        type: "line",
        source: "regions",
        paint: { "line-color": "#e6c89a", "line-width": 1.2 },
      });

      map.addLayer({
        id: "ports-circle",
        type: "circle",
        source: "ports",
        paint: {
          "circle-radius": [
            "case",
            ["==", ["get", "kind"], "port"], 5,
            4,
          ],
          "circle-color": [
            "case",
            ["==", ["get", "kind"], "port"], "#e6b800",
            "#9b5de5",
          ],
          "circle-stroke-color": "#0e1118",
          "circle-stroke-width": 1.5,
        },
      });

      // Selection halo
      map.addLayer({
        id: "selection-halo",
        type: "line",
        source: "regions",
        paint: { "line-color": "#ffffff", "line-width": 2.5 },
        filter: ["==", ["get", "id"], -1],
      });

      // Hover cursor + click to select
      for (const lyr of ["regions-fill", "ports-circle", "countries-fill"]) {
        map.on("mouseenter", lyr, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", lyr, () => { map.getCanvas().style.cursor = ""; });
        map.on("click", lyr, (e) => {
          const f = e.features?.[0] as MapGeoJSONFeature | undefined;
          if (f?.properties?.id != null) {
            selectTerritory(Number(f.properties.id));
          }
        });
      }
    });

    return () => { map.remove(); mapRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- push data into sources ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const filterByEmpire = (fc: GeoJSON.FeatureCollection | undefined) => {
      if (!fc) return EMPTY_FC;
      const features = fc.features.filter((f) => {
        const emp = (f.properties as any)?.empire;
        if (!emp) return true;  // countries (no empire on most) always pass
        return activeEmpires.has(emp);
      });
      return { type: "FeatureCollection" as const, features };
    };
    (map.getSource("countries") as maplibregl.GeoJSONSource | undefined)
      ?.setData(filterByEmpire(countriesQ.data));
    (map.getSource("regions") as maplibregl.GeoJSONSource | undefined)
      ?.setData(filterByEmpire(regionsQ.data));
    (map.getSource("ports") as maplibregl.GeoJSONSource | undefined)
      ?.setData(filterByEmpire(portsQ.data));
  }, [countriesQ.data, regionsQ.data, portsQ.data, activeEmpires]);

  // --- toggle layer visibility per kind set ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const showCountry = kinds.has("country");
    const showRegion = kinds.has("region");
    const showPort = kinds.has("port") || kinds.has("border_crossing");
    for (const [id, on] of [
      ["countries-fill", showCountry],
      ["countries-line", showCountry],
      ["regions-fill", showRegion],
      ["regions-outline", showRegion],
      ["ports-circle", showPort],
    ] as Array<[string, boolean]>) {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
      }
    }
  }, [kinds]);

  // --- selection halo + flyTo ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    if (map.getLayer("selection-halo")) {
      map.setFilter("selection-halo", ["==", ["get", "id"], selectedId ?? -1]);
    }
    if (selectedId != null) {
      const findIn = (fc?: GeoJSON.FeatureCollection) =>
        fc?.features.find((f) => f.id === selectedId || (f.properties as any)?.id === selectedId);
      const f = findIn(regionsQ.data) || findIn(portsQ.data) || findIn(countriesQ.data);
      if (f) {
        const geom = f.geometry as any;
        if (geom?.type === "Point") {
          map.flyTo({ center: geom.coordinates, zoom: 6, speed: 1.2 });
        }
      }
    }
  }, [selectedId, regionsQ.data, portsQ.data, countriesQ.data]);

  return <div ref={ref} className="absolute inset-0" />;
};

export default MapView;
