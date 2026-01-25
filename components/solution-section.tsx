'use client'

import { Zap, Shield, StopCircle, Repeat } from 'lucide-react'

export function SolutionSection() {
  const features = [
    {
      icon: Zap,
      title: 'Domain Warmup Automation',
      description: 'Gradual sends with strategic engagement patterns. Your domain reputation grows automatically.',
    },
    {
      icon: Shield,
      title: 'Hard Send Limits',
      description: 'We enforce hard caps based on your domain age and history. No overrides. Ever.',
    },
    {
      icon: StopCircle,
      title: 'Auto‑Stop on Replies',
      description: 'Detect real replies and pause follow‑ups instantly. No spam sequences to prospects who engaged.',
    },
    {
      icon: Repeat,
      title: 'Smart Follow‑ups',
      description: 'AI suggests timing and strategy for follow‑ups. Personalized, not pushy.',
    },
  ]

  return (
    <section className="py-20 px-6 border-b border-border">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">Outreach built the safe way</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Every feature is designed to protect your domain while maximizing delivery and replies.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <div
                key={index}
                className="group p-8 rounded-xl border border-border bg-card/40 backdrop-blur-sm hover:border-accent/50 transition-all duration-300 hover:bg-card/60 hover:shadow-lg"
              >
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 flex items-center justify-center mb-4 group-hover:shadow-lg group-hover:shadow-violet-500/20 transition-all">
                  <Icon className="w-6 h-6 text-violet-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
