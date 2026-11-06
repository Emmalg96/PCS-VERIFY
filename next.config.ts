import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Smaller production images when using the Dockerfile (copies `.next/standalone`). */
  output: "standalone",
};

export default nextConfig;
