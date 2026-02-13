'use client'

import React from "react"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { AlertCircle, CheckCircle } from 'lucide-react'

type FormState = 'idle' | 'loading' | 'success' | 'error'

interface FormData {
  fullName: string
  workEmail: string
  companyName: string
  role: string
  monthlyVolume: string
  leadStrategy?: string
}

export function WaitlistForm() {
  const [state, setState] = useState<FormState>('idle')
  const [error, setError] = useState('')
  const [formData, setFormData] = useState<FormData>({
    fullName: '',
    workEmail: '',
    companyName: '',
    role: 'Founder',
    monthlyVolume: '1k-5k',
    leadStrategy: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setState('loading')

    try {
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to submit form')
      }

      setState('success')
      setFormData({
        fullName: '',
        workEmail: '',
        companyName: '',
        role: 'Founder',
        monthlyVolume: '1k-5k',
        leadStrategy: '',
      })
    } catch (err) {
      console.error('Waitlist submission error:', err)
      setError(err instanceof Error ? err.message : 'An error occurred')
      setState('error')
    }
  }

  if (state === 'success') {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-8 h-8 text-green-400" />
        </div>
        <h3 className="text-2xl font-bold mb-2">You're on the list! 🎉</h3>
        <p className="text-muted-foreground mb-6">
          We'll reach out soon with your private beta access. Check your email for updates.
        </p>
        <Button
          onClick={() => setState('idle')}
          variant="outline"
          className="border-border"
        >
          Submit Another
        </Button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Full Name */}
      <div>
        <label htmlFor="fullName" className="block text-sm font-medium mb-2">
          Full Name
        </label>
        <Input
          id="fullName"
          name="fullName"
          type="text"
          placeholder="e.g., Alex Johnson"
          value={formData.fullName}
          onChange={handleChange}
          required
          className="bg-card border-border text-foreground placeholder:text-muted-foreground"
        />
      </div>

      {/* Work Email */}
      <div>
        <label htmlFor="workEmail" className="block text-sm font-medium mb-2">
          Work Email
        </label>
        <Input
          id="workEmail"
          name="workEmail"
          type="email"
          placeholder="e.g., alex@company.com"
          value={formData.workEmail}
          onChange={handleChange}
          required
          className="bg-card border-border text-foreground placeholder:text-muted-foreground"
        />
      </div>

      {/* Company Name */}
      <div>
        <label htmlFor="companyName" className="block text-sm font-medium mb-2">
          Company Name
        </label>
        <Input
          id="companyName"
          name="companyName"
          type="text"
          placeholder="e.g., Acme Inc"
          value={formData.companyName}
          onChange={handleChange}
          required
          className="bg-card border-border text-foreground placeholder:text-muted-foreground"
        />
      </div>

      {/* Role */}
      <div>
        <label htmlFor="role" className="block text-sm font-medium mb-2">
          Role
        </label>
        <select
          id="role"
          name="role"
          value={formData.role}
          onChange={handleChange}
          required
          className="w-full px-4 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
        >
          <option value="Founder">Founder</option>
          <option value="Sales">Sales</option>
          <option value="Marketing">Marketing</option>
          <option value="Other">Other</option>
        </select>
      </div>

      {/* Monthly Volume */}
      <div>
        <label htmlFor="monthlyVolume" className="block text-sm font-medium mb-2">
          Monthly Email Volume
        </label>
        <select
          id="monthlyVolume"
          name="monthlyVolume"
          value={formData.monthlyVolume}
          onChange={handleChange}
          required
          className="w-full px-4 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
        >
          <option value="1k-5k">1K - 5K/month</option>
          <option value="5k-20k">5K - 20K/month</option>
          <option value="20k-50k">20K - 50K/month</option>
          <option value="50k+">50K+/month</option>
        </select>
      </div>

      {/* Lead Strategy (Optional) */}
      <div>
        <label htmlFor="leadStrategy" className="block text-sm font-medium mb-2">
          How do you plan to get leads? <span className="text-muted-foreground">(optional)</span>
        </label>
        <select
          id="leadStrategy"
          name="leadStrategy"
          value={formData.leadStrategy}
          onChange={handleChange}
          className="w-full px-4 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
        >
          <option value="">Select an option...</option>
          <option value="csv">Upload CSV</option>
          <option value="built-in">Use built-in lead gen</option>
          <option value="both">Both</option>
        </select>
      </div>

      {/* Error Message */}
      {state === 'error' && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Error</p>
            <p className="text-sm text-red-300">{error}</p>
          </div>
        </div>
      )}

      {/* Submit Button */}
      <Button
        type="submit"
        disabled={state === 'loading'}
        className="w-full bg-gradient-to-r from-violet-500 to-indigo-500 hover:from-violet-600 hover:to-indigo-600 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {state === 'loading' ? 'Requesting Access...' : 'Request Access'}
      </Button>

      <p className="text-xs text-muted-foreground text-center">
        We respect your privacy. Unsubscribe anytime.
      </p>
    </form>
  )
}
