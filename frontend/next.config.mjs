/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true, poweredByHeader: false,
  async rewrites() {
    const backend = process.env.BACKEND_ORIGIN || (process.env.NODE_ENV === "production" ? "https://smartfind-api-production.up.railway.app" : "");
    if (!backend) return [];
    return [
      {source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*`},
      {source: "/media/public/:path*", destination: `${backend}/media/public/:path*`}
    ];
  }
};
export default nextConfig;
