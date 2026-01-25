'use client'

import { Brain, PenTool, MessageCircle, User } from 'lucide-react'

export function AISection() {
  const aiFeatures = [
    {
      icon: PenTool,
      title: 'AI Email Drafting',
      description: 'Generate personalized cold emails in seconds. Our model learns your best-performing angles.',
      badge: 'Personalized',
    },
    {
      icon: MessageCircle,
      title: 'AI Follow‑up Sequences',
      description: 'Smart follow-up timing and strategy. AI suggests what to send next based on prospect behavior.',
      badge: 'Timed',
    },
    {
      icon: Brain,
      title: 'Reply Suggestions',
      description: 'AI helps you draft compelling responses. But you always write the actual reply yourself.',
      badge: 'Draft Only',
    },
    {
      icon: User,
      title: 'Human in the Loop',
      description: 'You stay in control. AI assists, suggests, and learns. But you make every final decision.',
      badge: 'Always',
    },
  ]

  return (
    <section className="py-20 px-6 border-b border-border">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-accent/30 bg-accent/5 mb-6">
            <Brain className="w-4 h-4 text-accent" />
            <span className="text-sm font-medium text-accent">Powered by AI</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-bold mb-4">AI that helps, not hurts</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            AI drafting and suggestions that save you hours. But we never auto-send replies or make permanent decisions without you.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {aiFeatures.map((feature, index) => {
            const Icon = feature.icon
            return (
              <div
                key={index}
                className="group p-8 rounded-xl border border-border bg-card/40 backdrop-blur-sm hover:border-accent/50 transition-all duration-300 hover:bg-card/60"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 flex items-center justify-center group-hover:shadow-lg group-hover:shadow-violet-500/20 transition-all">
                    <Icon className="w-6 h-6 text-violet-400" />
                  </div>
                  <span className="text-xs font-semibold text-accent bg-accent/10 px-3 py-1 rounded-full">
                    {feature.badge}
                  </span>
                </div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </div>
            )
          })}
        </div>

        {/* Key Message */}
        <div className="mt-12 p-8 rounded-xl border border-accent/20 bg-gradient-to-r from-violet-500/5 to-indigo-500/5 backdrop-blur-sm">
          <p className="text-center text-lg">
            <span className="font-semibold text-foreground">We never auto-send replies.</span>
            <span className="text-muted-foreground"> Your inbox, your control, your relationships.</span>
          </p>
        </div>
      </div>
    </section>
  )
}
