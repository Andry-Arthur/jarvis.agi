/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const httpOrigin = process.env.JARVIS_HTTP_ORIGIN ?? "http://localhost:8000";
    const wsOriginRaw = process.env.JARVIS_WS_ORIGIN ?? httpOrigin;
    const wsOrigin = wsOriginRaw.replace(/^wss:/, "https:").replace(/^ws:/, "http:");

    return [
      {
        source: "/api/:path*",
        destination: `${httpOrigin.replace(/\/$/, "")}/api/:path*`,
      },
      {
        source: "/ws",
        destination: `${wsOrigin.replace(/\/$/, "")}/ws`,
      },
    ];
  },
};

export default nextConfig;

