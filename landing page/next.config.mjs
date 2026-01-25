import path from 'path'
import { config } from 'dotenv'

config({ path: path.join(process.cwd(), '..', '.env') })

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
