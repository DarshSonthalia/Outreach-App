'use client'

import { motion } from 'framer-motion'
import { Link2, Sliders, CheckCircle2 } from 'lucide-react'

export function LeadQualitySection() {
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

  const cards = [
    {
      icon: Link2,
      title: 'Source Links Included',
      description: 'Every lead shows where it came from.',
    },
    {
      icon: Sliders,
      title: 'Filters Built In',
      description: 'Avoid role inboxes like info@ and support@.',
    },
    {
      icon: CheckCircle2,
      title: 'Human Review First',
      description: 'Nothing is added until you approve.',
    },
  ]

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <motion.div
        className="grid md:grid-cols-3 gap-6"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-100px' }}
      >
        {cards.map((card, idx) => {
          const Icon = card.icon
          return (
            <motion.div
              key={idx}
              className="group rounded-xl border border-border/50 bg-card/30 backdrop-blur-sm p-6 hover:bg-card/50 transition-all duration-300 hover:border-accent/30"
              variants={itemVariants}
            >
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 flex items-center justify-center mb-4 group-hover:from-violet-500/30 group-hover:to-indigo-500/30 transition-all">
                <Icon size={24} className="text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {card.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {card.description}
              </p>
            </motion.div>
          )
        })}
      </motion.div>
    </section>
  )
}
