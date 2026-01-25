'use client'

import { Mail, Users, Zap, MessageSquare } from 'lucide-react'

export function HowItWorks() {
  const steps = [
    {
      number: '1',
      icon: Mail,
      title: 'Connect Gmail',
      description: 'Link your Gmail account securely. We never store passwords, only manage sending.',
    },
    {
      number: '2',
      icon: Users,
      title: 'Add Leads',
      description: 'Upload your prospect list. Our system validates emails and flags high-risk recipients.',
    },
    {
      number: '3',
      icon: Zap,
      title: 'Launch Safely',
      description: 'Campaigns start slow, respecting warmup rules. Our AI monitors for spam signals in real-time.',
    },
    {
      number: '4',
      icon: MessageSquare,
      title: 'Manage Replies',
      description: 'View all replies in one inbox. Auto-detect engagement and pause sequences for respondents.',
    },
  ]

  return (
    <section id="how-it-works" className="py-20 px-6 border-b border-border scroll-mt-20">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">How It Works</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Four simple steps to scale cold email without burning your domain.
          </p>
        </div>

        <div className="space-y-8">
          {steps.map((step, index) => {
            const Icon = step.icon
            return (
              <div key={index} className="flex gap-6 md:gap-8">
                {/* Number Circle */}
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center font-bold text-white text-lg">
                    {step.number}
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 pt-1">
                  <div className="flex items-start gap-4 p-6 rounded-xl border border-border bg-card/40 backdrop-blur-sm hover:border-accent/50 transition-all">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                      <p className="text-muted-foreground leading-relaxed">{step.description}</p>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
