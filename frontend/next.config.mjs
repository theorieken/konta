/** @type {import('next').NextConfig} */
const nextConfig = {
  // Small runtime image – see Dockerfile.
  output: 'standalone',
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  // The API lives behind the same nginx, so no rewrites are needed in
  // production. In `npm run dev` this proxies to a locally running backend.
  async rewrites() {
    if (process.env.NODE_ENV === 'production') return [];
    const backend = process.env.DEV_BACKEND_URL || 'http://localhost:8000';
    return [
      { source: '/api/:path*', destination: `${backend}/api/:path*` },
      { source: '/ws/:path*', destination: `${backend}/ws/:path*` },
    ];
  },
};

export default nextConfig;
