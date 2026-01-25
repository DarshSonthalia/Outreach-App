'use client'

import { motion } from 'framer-motion'
import { LeadGenPreviewCard } from './lead-gen-preview-card'

export function LeadGenSection() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6 },
    },
  }

  const bullets = [
    'Company → website discovery',
    'Team/about/contact page scanning',
    'Email pattern suggestions + verification signals',
    'Review before outreach—stay in control',
  ]

  return (
    <section id="lead-gen" className="py-20 px-6 max-w-7xl mx-auto">
      <motion.div
        className="grid lg:grid-cols-2 gap-12 items-start"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-100px' }}
      >
        {/* Left: Content */}
        <motion.div className="space-y-6" variants={itemVariants}>
          <div>
            <motion.h2
              className="text-4xl md:text-5xl font-bold text-balance mb-4"
              variants={itemVariants}
            >
              Find Leads From Public Sources—Fast
            </motion.h2>
            <motion.p
              className="text-lg text-muted-foreground leading-relaxed"
              variants={itemVariants}
            >
              Input company names or domains and discover suggested contacts from public websites, team pages, and public web results.
            </motion.p>
          </div>

          {/* Bullets */}
          <motion.ul className="space-y-3" variants={containerVariants}>
            {bullets.map((bullet, idx) => (
              <motion.li
                key={idx}
                className="flex items-start gap-3"
                variants={itemVariants}
              >
                <div className="flex-shrink-0 w-5 h-5 rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 flex items-center justify-center mt-1">
                  <span className="w-2 h-2 bg-white rounded-full" />
                </div>
                <span className="text-foreground">{bullet}</span>
              </motion.li>
            ))}
          </motion.ul>


        </motion.div>

        {/* Right: Preview Card */}
        <motion.div variants={itemVariants}>
          <LeadGenPreviewCard />
        </motion.div>
      </motion.div>
    </section>
  )
}
