'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Menu, X } from 'lucide-react'

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false)
  const appUrl = '/app'

  const scrollToSection = (id: string) => {
    setIsOpen(false)
    const element = document.getElementById(id)
    element?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <nav className="fixed top-0 w-full z-50 backdrop-blur-md bg-background/80 border-b border-border">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <div className="font-bold text-xl tracking-tight">
          <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
            intently-ai
          </span>
        </div>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-8">
          <button
            onClick={() => scrollToSection('how-it-works')}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            How It Works
          </button>
          <button
            onClick={() => scrollToSection('lead-gen')}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Lead Gen
          </button>
          <button
            onClick={() => scrollToSection('safety')}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Safety
          </button>
          <button
            onClick={() => scrollToSection('pricing')}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Pricing
          </button>
          <button
            onClick={() => scrollToSection('waitlist')}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Join Waitlist
          </button>
        </div>

        {/* CTA Button */}
        <div className="hidden md:flex items-center gap-3">
          <Button
            onClick={() => scrollToSection('waitlist')}
            className="bg-gradient-to-r from-violet-500 to-indigo-500 hover:from-violet-600 hover:to-indigo-600 text-white border-0 shadow-lg hover:shadow-xl transition-all"
          >
            Join Waitlist
          </Button>
          <Button asChild variant="outline" className="border-border/60">
            <Link href={appUrl}>Sign Up</Link>
          </Button>
        </div>

        {/* Mobile Menu Button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="md:hidden p-2 text-foreground hover:bg-card rounded-lg transition-colors"
        >
          {isOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Navigation */}
      {isOpen && (
        <div className="md:hidden border-t border-border bg-background/95 backdrop-blur-md">
          <div className="px-6 py-4 space-y-4">
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="block w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors py-2"
            >
              How It Works
            </button>
            <button
              onClick={() => scrollToSection('lead-gen')}
              className="block w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors py-2"
            >
              Lead Gen
            </button>
            <button
              onClick={() => scrollToSection('safety')}
              className="block w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors py-2"
            >
              Safety
            </button>
            <button
              onClick={() => scrollToSection('pricing')}
              className="block w-full text-left text-sm text-muted-foreground hover:text-foreground transition-colors py-2"
            >
              Pricing
            </button>
            <Button
              asChild
              variant="outline"
              className="w-full border-border/60"
              onClick={() => setIsOpen(false)}
            >
              <Link href={appUrl}>Sign Up</Link>
            </Button>
            <Button
              onClick={() => scrollToSection('waitlist')}
              className="w-full bg-gradient-to-r from-violet-500 to-indigo-500 hover:from-violet-600 hover:to-indigo-600 text-white border-0"
            >
              Join Waitlist
            </Button>
          </div>
        </div>
      )}
    </nav>
  )
}
