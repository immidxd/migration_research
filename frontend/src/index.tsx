import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider, theme as antdTheme } from "antd";

import App from "./App";
import { useFilters } from "./store";
import "./styles/index.css";
import "maplibre-gl/dist/maplibre-gl.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } },
});


const Themed: React.FC = () => {
  const mode = useFilters((s) => s.theme);
  return (
    <ConfigProvider
      theme={{
        algorithm:
          mode === "dark" ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: mode === "dark" ? "#c9a96e" : "#9c5e1c",
          colorBgBase: mode === "dark" ? "#1a1f2e" : "#faf6ec",
          colorTextBase: mode === "dark" ? "#e6e9ef" : "#2a2724",
          borderRadius: 6,
        },
      }}
    >
      <App />
    </ConfigProvider>
  );
};

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Themed />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
