/** @type {import('next').NextConfig} */
const backendApiUrl = (process.env.BACKEND_API_URL || 'https://vlegal-rag-backend.onrender.com').replace(/\/+$/, '');

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/backend/chat',
        destination: `${backendApiUrl}/chat/`,
      },
      {
        source: '/api/backend/:path*',
        destination: `${backendApiUrl}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
