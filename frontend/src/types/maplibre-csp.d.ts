// CSP-safe maplibre-gl build doesn't ship its own .d.ts file. The CSP
// build has the same public API as the default build, so we just re-export
// the regular maplibre-gl types.
declare module "maplibre-gl/dist/maplibre-gl-csp" {
  import maplibregl from "maplibre-gl";
  export * from "maplibre-gl";
  export default maplibregl;
}
