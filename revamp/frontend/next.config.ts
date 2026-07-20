import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // This app is a nested package inside a larger repo; pin the workspace root
  // so Turbopack doesn't infer the parent lockfile.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
