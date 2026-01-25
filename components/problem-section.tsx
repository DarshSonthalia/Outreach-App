'use client'

import { AlertCircle, Inbox, Clock } from 'lucide-react'

export function ProblemSection() {
  const problems = [
    {
      icon: AlertCircle,
      title: 'Burned Domains',
      description: 'One mistake and your domain reputation is ruined. No more inbox placement. No more sales.',
    },
    {
      icon: Inbox,
      title: 'Spam Folders',
      description: 'Without proper warmup, even great emails land in spam. Your campaigns become invisible.',
    },
    {
      icon: Clock,
      title: 'Manual Follow‑ups',
      description: 'Tracking who replied, when to follow up, and managing replies takes hours. Every day.',
    },
  ]

  return (
    <section className="py-20 px-6 border-b border-border">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">Cold outreach is risky and broken</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Most platforms let you move fast. But speed without safety destroys your ability to sell.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {problems.map((problem, index) => {
            const Icon = problem.icon
            return (
              <div
                key={index}
                className="p-8 rounded-xl border border-border bg-card/40 backdrop-blur-sm hover:border-accent/50 transition-all duration-300 hover:bg-card/60"
              >
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-red-500/20 to-orange-500/20 flex items-center justify-center mb-4">
                  <Icon className="w-6 h-6 text-red-400" />
                </div>
                <h3 className="text-xl font-semibold mb-3">{problem.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{problem.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
