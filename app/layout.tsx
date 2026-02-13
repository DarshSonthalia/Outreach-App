import React from "react"
import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'intently-ai - AI-Powered Cold Email That Protects Your Domain',
  description: 'Send cold emails safely with AI-powered warmup, smart follow-ups, and lead discovery from public web sources. Built-in reputation protection. Founders and sales teams trust intently-ai to scale outreach without burning domains.',
  generator: 'v0.app',
  openGraph: {
    title: 'intently-ai - Cold Email That Actually Protects Your Domain',
    description: 'AI-powered outreach with built-in warmup, safety limits, smart follow-ups, and real inbox replies — all in one platform.',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'intently-ai - Cold Email That Actually Protects Your Domain',
    description: 'AI-powered outreach platform with safety-first features for founders and sales teams.',
  },
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
  themeColor: '#0a0a0f',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark scroll-smooth" suppressHydrationWarning>
      <body className={`font-sans antialiased bg-background text-foreground`}>
        {children}
        <Analytics />
      </body>
    </html>
  )
}
