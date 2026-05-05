/** @type {import('next').NextConfig} */
const apiLabAgentOrigin = (process.env.AI_LAB_AGENT_URL || "http://localhost:8000").replace(/\/+$/, "")

const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiLabAgentOrigin}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
