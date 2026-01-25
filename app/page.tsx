import { Navbar } from '@/components/navbar'
import { Hero } from '@/components/hero'
import { ProblemSection } from '@/components/problem-section'
import { SolutionSection } from '@/components/solution-section'
import { HowItWorks } from '@/components/how-it-works'
import { LeadGenSection } from '@/components/lead-gen-section'
import { LeadQualitySection } from '@/components/lead-quality-section'
import { SafetySection } from '@/components/safety-section'
import { AISection } from '@/components/ai-section'
import { WaitlistSection } from '@/components/waitlist-section'
import { Footer } from '@/components/footer'
import { SocialProof } from '@/components/social-proof' // Added import for SocialProof

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <Navbar />

      {/* Hero Section */}
      <Hero />

      {/* Problem Section */}
      <ProblemSection />

      {/* Solution Section */}
      <SolutionSection />

      {/* How It Works */}
      <HowItWorks />

      {/* Lead Gen Section */}
      <LeadGenSection />

      {/* Lead Quality Section */}
      <LeadQualitySection />

      {/* Safety Section */}
      <SafetySection />

      {/* AI Section */}
      <AISection />

      {/* Waitlist Section */}
      <WaitlistSection />

      {/* Footer */}
      <Footer />
    </main>
  )
}
