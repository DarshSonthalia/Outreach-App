'use client'

import { WaitlistForm } from './waitlist-form'

export function WaitlistSection() {
  return (
    <section id="waitlist" className="py-20 px-6 border-b border-border scroll-mt-20">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">Join the Private Beta</h2>
          <p className="text-lg text-muted-foreground">
            We're onboarding early users carefully to ensure we deliver the best experience and maintain perfect deliverability for our community.
          </p>
        </div>

        {/* Form Container */}
        <div className="p-8 rounded-2xl border border-border bg-gradient-to-br from-card/60 to-card/30 backdrop-blur-sm">
          <WaitlistForm />
        </div>

        {/* Trust Note */}
        <div className="mt-8 p-6 rounded-xl border border-border/50 bg-card/20">
          <p className="text-center text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">Privacy guaranteed.</span> We never sell your data. Your email is safe with us.
          </p>
        </div>
      </div>
    </section>
  )
}
