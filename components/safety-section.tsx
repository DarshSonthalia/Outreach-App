'use client'

import { CheckCircle2, Shield } from 'lucide-react'

export function SafetySection() {
  const safetyFeatures = [
    'SPF/DMARC verification before every send',
    'Ramped daily send limits based on domain history',
    'Real‑time bounce and unsubscribe monitoring',
    'Automatic campaign pause on spam signals',
    'No unsafe overrides — ever',
    'Compliance with all major ISP sender requirements',
  ]

  return (
    <section id="safety" className="py-20 px-6 border-b border-border scroll-mt-20">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-accent/30 bg-accent/5 mb-6">
            <Shield className="w-4 h-4 text-accent" />
            <span className="text-sm font-medium text-accent">Security First</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">We protect your reputation by default</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Every feature is built with domain reputation protection as the foundation. No compromises.
          </p>
        </div>

        {/* Main Safety Card */}
        <div className="mb-12 p-8 md:p-12 rounded-2xl border border-accent/20 bg-gradient-to-br from-card/60 to-card/30 backdrop-blur-sm">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Left: Icon + Text */}
            <div>
              <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center mb-6">
                <Shield className="w-8 h-8 text-green-400" />
              </div>
              <h3 className="text-2xl font-bold mb-4">Built for domain longevity</h3>
              <p className="text-muted-foreground leading-relaxed mb-6">
                Your domain is your most valuable asset in sales. One burned domain can take months to recover. We build everything around ensuring your domain stays healthy and profitable for years.
              </p>
            </div>

            {/* Right: Feature List */}
            <div className="space-y-3">
              {safetyFeatures.map((feature, index) => (
                <div key={index} className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                  <span className="text-foreground">{feature}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Why It Matters */}
        <div className="p-8 rounded-xl border border-border bg-card/40 backdrop-blur-sm">
          <h3 className="text-xl font-semibold mb-4">Why This Matters</h3>
          <div className="space-y-4 text-muted-foreground leading-relaxed">
            <p>
              Without strict safety controls, founders and sales teams burn through domains. They send too fast, ignore bounce rates, and spam signals. Then they wonder why nobody responds anymore.
            </p>
            <p>
              intently-ai takes that burden off your shoulders. We make the hard decisions for you, enforcing safety limits that protect your ability to sell at scale.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
