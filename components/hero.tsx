'use client'

import { Button } from '@/components/ui/button'
import { ArrowRight } from 'lucide-react'

export function Hero() {
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id)
    element?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <section className="relative min-h-screen flex items-center justify-center pt-20 px-6 overflow-hidden">
      {/* Animated background gradient */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>

      <div className="max-w-4xl mx-auto text-center">
        {/* Main Headline */}
        <h1 className="text-5xl md:text-7xl font-bold mb-6 text-balance leading-tight">
          Cold Email That Actually Protects Your Domain
        </h1>

        {/* Subheadline */}
        <p className="text-lg md:text-xl text-muted-foreground mb-8 text-balance leading-relaxed max-w-3xl mx-auto">
          AI-powered outreach with built‑in warmup, safety limits, smart follow‑ups, and real inbox replies — all in one platform.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <Button
            onClick={() => scrollToSection('waitlist')}
            size="lg"
            className="bg-gradient-to-r from-violet-500 to-indigo-500 hover:from-violet-600 hover:to-indigo-600 text-white border-0 shadow-lg hover:shadow-2xl transition-all px-8"
          >
            Join Waitlist
            <ArrowRight className="ml-2 w-4 h-4" />
          </Button>
          <Button
            onClick={() => scrollToSection('how-it-works')}
            variant="outline"
            size="lg"
            className="border-border hover:bg-card px-8"
          >
            See How It Works
          </Button>
        </div>

        {/* Trust Badge */}
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          <span>Private beta opening soon</span>
        </div>
      </div>
    </section>
  )
}
