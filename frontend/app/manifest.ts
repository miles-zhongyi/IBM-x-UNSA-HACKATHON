import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "HealthChat AI (demo)",
    short_name: "HealthChat",
    description: "Understand your visit notes with grounded answers (demo).",
    start_url: "/",
    display: "standalone",
    background_color: "#faf9f6",
    theme_color: "#1d4ed8",
    icons: [
      { src: "/icon-192.svg", sizes: "192x192", type: "image/svg+xml", purpose: "any" },
      { src: "/icon-512.svg", sizes: "512x512", type: "image/svg+xml", purpose: "any" },
    ],
  };
}
