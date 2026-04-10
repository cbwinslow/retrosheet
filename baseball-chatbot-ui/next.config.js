/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    BASEBALL_API_URL: process.env.BASEBALL_API_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig
