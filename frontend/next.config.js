/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  "output": "export",
  env: {
    HOST: process.env.HOST
  },
  typescript: {
    ignoreBuildErrors: true
  },
  eslint: {
    ignoreDuringBuilds: true
  },
  jest: {
    enabled: false
  }
};

// Set assetPrefix only in production/export mode
if (process.env.NODE_ENV === 'production') {
  nextConfig.assetPrefix = '/static';
}

module.exports = nextConfig;
