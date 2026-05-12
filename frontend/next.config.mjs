/** @type {import('next').NextConfig} */
function getApiOrigin() {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1"
  try {
    const url = new URL(baseUrl)
    return url.origin
  } catch {
    return "http://localhost:8000"
  }
}

const apiOrigin = getApiOrigin()

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
        destination: `${apiOrigin}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
