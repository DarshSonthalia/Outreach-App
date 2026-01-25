'use client'

export function SocialProof() {
  return (
    <section className="py-16 px-6 border-b border-border">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <p className="text-sm text-muted-foreground font-medium mb-2">BUILT FOR FOUNDERS & SALES TEAMS</p>
          <h2 className="text-2xl font-bold">Trusted by the most demanding outreach teams</h2>
        </div>

        {/* Logo Grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 items-center justify-items-center">
          {[
            'Stripe',
            'Notion',
            'Linear',
            'Vercel',
            'Raycast',
          ].map((company) => (
            <div
              key={company}
              className="px-6 py-4 rounded-lg border border-border/50 bg-card/30 hover:border-accent/50 transition-colors"
            >
              <p className="text-sm font-semibold text-muted-foreground">{company}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
