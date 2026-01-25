'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'

interface MockLead {
  name: string
  role: string
  email: string
  source: string
  confidence: 'High' | 'Medium'
}

const mockResults: MockLead[] = [
  {
    name: 'Sarah Chen',
    role: 'Sales Manager',
    email: 'sarah.chen@acme.com',
    source: 'Website',
    confidence: 'High',
  },
  {
    name: 'Marcus Rodriguez',
    role: 'VP Marketing',
    email: 'm.rodriguez@acme.com',
    source: 'About Page',
    confidence: 'High',
  },
  {
    name: 'Elena Vasquez',
    role: 'Head of Growth',
    email: 'e.vasquez@acme.com',
    source: 'Public Web',
    confidence: 'Medium',
  },
  {
    name: 'James Park',
    role: 'Business Development',
    email: 'james.park@acme.com',
    source: 'Website',
    confidence: 'High',
  },
]

export function LeadGenPreviewCard() {
  const [showResults, setShowResults] = useState(false)
  const [inputValue, setInputValue] = useState('Acme Inc\nexample.com\nTechFlow Solutions')

  const handlePreview = () => {
    setShowResults(true)
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4 },
    },
  }

  return (
    <div className="relative">
      {/* Card Container */}
      <div className="rounded-xl border border-border/50 bg-card/50 backdrop-blur-sm p-6 shadow-lg hover:shadow-xl transition-shadow duration-300">
        {/* Input Section */}
        <div className="space-y-3 mb-6">
          <label className="text-sm font-medium text-foreground">
            Company names or domains
          </label>
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Acme Inc&#10;example.com&#10;TechFlow Solutions"
            className="w-full h-24 px-4 py-3 rounded-lg bg-background/50 border border-border text-foreground placeholder:text-muted-foreground text-sm resize-none focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all"
          />
        </div>

        {/* Preview Button */}
        <Button
          onClick={handlePreview}
          className="w-full bg-gradient-to-r from-violet-500 to-indigo-500 hover:from-violet-600 hover:to-indigo-600 text-white border-0 font-medium shadow-lg hover:shadow-xl transition-all"
        >
          Preview Leads
        </Button>

        {/* Results Section */}
        <AnimatePresence>
          {showResults && (
            <motion.div
              className="mt-6 space-y-3"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {/* Results Header */}
              <div className="text-sm font-medium text-muted-foreground px-1">
                Sample Results (3 of 12 found)
              </div>

              {/* Desktop Table View */}
              <div className="hidden sm:block overflow-hidden rounded-lg border border-border/50">
                <div className="divide-y divide-border/50">
                  {/* Table Header */}
                  <div className="grid grid-cols-5 gap-4 bg-background/50 p-3">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Name
                    </div>
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Role
                    </div>
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Email
                    </div>
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Source
                    </div>
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Confidence
                    </div>
                  </div>

                  {/* Table Rows */}
                  {mockResults.map((lead, idx) => (
                    <motion.div
                      key={idx}
                      className="grid grid-cols-5 gap-4 p-3 hover:bg-background/30 transition-colors"
                      variants={itemVariants}
                    >
                      <div className="text-sm text-foreground truncate font-medium">
                        {lead.name}
                      </div>
                      <div className="text-sm text-muted-foreground truncate">
                        {lead.role}
                      </div>
                      <div className="text-sm text-violet-400 truncate font-mono text-xs">
                        {lead.email}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {lead.source}
                      </div>
                      <div className="flex">
                        <span
                          className={`text-xs font-medium px-2 py-1 rounded-full ${
                            lead.confidence === 'High'
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-amber-500/20 text-amber-400'
                          }`}
                        >
                          {lead.confidence}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Mobile Stacked View */}
              <div className="sm:hidden space-y-2">
                {mockResults.map((lead, idx) => (
                  <motion.div
                    key={idx}
                    className="p-3 rounded-lg bg-background/50 border border-border/50 space-y-2"
                    variants={itemVariants}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <div className="text-sm font-medium text-foreground">
                          {lead.name}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {lead.role}
                        </div>
                      </div>
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded-full flex-shrink-0 ${
                          lead.confidence === 'High'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-amber-500/20 text-amber-400'
                        }`}
                      >
                        {lead.confidence}
                      </span>
                    </div>
                    <div className="text-xs text-violet-400 font-mono break-all">
                      {lead.email}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Source: {lead.source}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Disclaimer */}
              <motion.p
                className="text-xs text-muted-foreground italic pt-3"
                variants={itemVariants}
              >
                Preview only — real results depend on publicly available data.
              </motion.p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Ambient Glow */}
      <div className="absolute -inset-0.5 bg-gradient-to-r from-violet-500/20 to-indigo-500/20 rounded-xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity -z-10" />
    </div>
  )
}
