import React, { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";

// Minimal MapLibre canvas using a free OSM raster style — placeholder until
// historical basemaps (Euratlas / Rumsey WMTS) and territory layers land.
const MapView: React.FC = () => {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center: [31.0, 49.0], // centred on Ukraine
      zoom: 4.5,
    });
    return () => map.remove();
  }, []);

  return <div ref={ref} className="absolute inset-0" />;
};

export default MapView;
