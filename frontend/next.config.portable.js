/** Next.js config for portable static export (bundled inside e-Patrol.exe) */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  trailingSlash: true,
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_API_URL: 'http://127.0.0.1:8765',
  },
}

module.exports = nextConfig
