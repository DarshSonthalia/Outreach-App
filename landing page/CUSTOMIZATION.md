# SafeMail Landing Page - Customization Guide

This guide shows you how to customize the landing page for your needs.

---

## 🏢 Rebrand to Your Company

### Step 1: Replace Company Name

Search and replace `SafeMail` with your company name across these files:

**File: `/components/navbar.tsx`**
```tsx
// Before:
<span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
  SafeMail
</span>

// After:
<span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
  YourCompanyName
</span>
```

**File: `/components/footer.tsx`**
```tsx
// Before:
<span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
  SafeMail
</span>

// After:
<span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
  YourCompanyName
</span>
```

**File: `/app/layout.tsx`**
```typescript
export const metadata: Metadata = {
  title: 'SafeMail - AI-Powered Cold Email...',
  // Change to:
  title: 'YourCompanyName - Your Value Proposition...',
  
  openGraph: {
    title: 'SafeMail - Cold Email That Actually Protects Your Domain',
    // Change to:
    title: 'YourCompanyName - Your Value Proposition',
  },
  
  twitter: {
    title: 'SafeMail - Cold Email That Actually Protects Your Domain',
    // Change to:
    title: 'YourCompanyName - Your Value Proposition',
  },
}
```

### Step 2: Update Logo

Replace text logo with actual logo:

**File: `/components/navbar.tsx`**
```tsx
// Option A: Use an image logo
import Image from 'next/image'

<Image src="/logo.svg" alt="Logo" width={32} height={32} />

// Option B: Keep gradient text but change styling
<span className="font-bold text-lg">Your Logo Text</span>
```

---

## 📝 Update Content

### Hero Section

**File: `/components/hero.tsx`**
```tsx
<h1 className="text-5xl md:text-7xl font-bold mb-6 text-balance leading-tight">
  Your Headline Here
</h1>

<p className="text-lg md:text-xl text-muted-foreground mb-8 text-balance leading-relaxed max-w-3xl mx-auto">
  Your subheadline and value proposition here.
</p>
```

### Problem Section

**File: `/components/problem-section.tsx`**
```tsx
const problems = [
  {
    icon: AlertCircle,
    title: 'Your Problem 1',
    description: 'Describe the pain point your product solves...',
  },
  {
    icon: Inbox,
    title: 'Your Problem 2',
    description: 'Another problem your customers face...',
  },
  {
    icon: Clock,
    title: 'Your Problem 3',
    description: 'Third key problem your product addresses...',
  },
]
```

### Solution Section

**File: `/components/solution-section.tsx`**
```tsx
const features = [
  {
    icon: Zap,
    title: 'Your Feature 1',
    description: 'How this feature benefits customers...',
  },
  {
    icon: Shield,
    title: 'Your Feature 2',
    description: 'Benefit of this feature...',
  },
  // Add/remove features as needed
]
```

### How It Works Section

**File: `/components/how-it-works.tsx`**
```tsx
const steps = [
  {
    number: '1',
    icon: Mail,
    title: 'Your Step 1',
    description: 'What users do in step 1...',
  },
  {
    number: '2',
    icon: Users,
    title: 'Your Step 2',
    description: 'What happens in step 2...',
  },
  // Modify as needed for your product flow
]
```

### Safety Section

**File: `/components/safety-section.tsx`**
```tsx
const safetyFeatures = [
  'Your first key benefit or feature',
  'Your second key benefit or feature',
  'Your third key benefit or feature',
  'Add more or remove as needed',
]
```

---

## 🎨 Change Colors & Theme

### Update Color Scheme

**File: `/app/globals.css`**

Modify the `.dark` section to match your brand:

```css
.dark {
  --background: #0a0a0f;      /* Main background */
  --foreground: #f5f5f7;      /* Main text */
  --card: #1a1a2e;            /* Card background */
  --card-foreground: #f5f5f7; /* Card text */
  --accent: #a78bfa;          /* Primary accent (violet) */
  --accent-foreground: #0a0a0f;
  --muted: #4a4a6a;           /* Disabled/secondary text */
  --muted-foreground: #a8a8c0;
  --border: #2d2d4d;          /* Border color */
  --input: #1a1a2e;           /* Input background */
  --ring: #7c3aed;            /* Focus ring color */
}
```

### Common Brand Colors

**Blue-based SaaS:**
```css
--accent: #0066ff;     /* Bright blue */
--ring: #0052cc;       /* Darker blue */
```

**Green-based (Environmental/Health):**
```css
--accent: #10b981;     /* Emerald green */
--ring: #059669;
```

**Red-based (Energy/Speed):**
```css
--accent: #ef4444;     /* Bright red */
--ring: #dc2626;
```

**Orange-based (Warmth/Growth):**
```css
--accent: #f97316;     /* Vibrant orange */
--ring: #ea580c;
```

### Update Gradient Accents

**File: `/components/navbar.tsx`, `/components/footer.tsx`**
```tsx
// Before (Violet → Indigo):
<span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">

// After (Your colors):
<span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
```

### Update Button Colors

Throughout components, change button gradients:

```tsx
// Before:
className="bg-gradient-to-r from-violet-500 to-indigo-500 hover:from-violet-600 hover:to-indigo-600"

// After:
className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600"
```

---

## 🔤 Change Fonts

### Update to Different Font

**File: `/app/layout.tsx`**
```tsx
import { Poppins, Sora } from 'next/font/google'

// Poppins
const poppins = Poppins({ 
  subsets: ["latin"],
  weight: ['400', '600', '700']
})

// In your layout:
<body className={`${poppins.className} font-sans antialiased`}>
```

**File: `/app/globals.css`**
```css
@theme inline {
  --font-sans: 'Poppins', sans-serif;
  --font-mono: 'Geist Mono', monospace;
}
```

### Popular Font Combinations

**Modern/Tech:** Inter + JetBrains Mono
**Elegant:** Playfair Display + Lato  
**Friendly:** Sora + Inter
**Professional:** Poppins + Roboto Mono

---

## 👥 Update Waitlist Form

### Add New Fields

**File: `/components/waitlist-form.tsx`**

Add to `FormData` interface:
```tsx
interface FormData {
  fullName: string
  workEmail: string
  companyName: string
  role: string
  monthlyVolume: string
  phoneNumber?: string  // New field
  budget?: string       // New field
}
```

Add form input:
```tsx
<div>
  <label htmlFor="phoneNumber" className="block text-sm font-medium mb-2">
    Phone Number
  </label>
  <Input
    id="phoneNumber"
    name="phoneNumber"
    type="tel"
    placeholder="+1 (555) 123-4567"
    value={formData.phoneNumber || ''}
    onChange={handleChange}
    className="bg-card border-border text-foreground placeholder:text-muted-foreground"
  />
</div>
```

### Change Form Labels

```tsx
// Before:
<label htmlFor="monthlyVolume" className="block text-sm font-medium mb-2">
  Monthly Email Volume
</label>

// After:
<label htmlFor="monthlyVolume" className="block text-sm font-medium mb-2">
  Your Custom Label
</label>
```

### Update Dropdown Options

```tsx
<select id="role" name="role" value={formData.role} onChange={handleChange}>
  <option value="Founder">Founder</option>
  <option value="Sales">Sales</option>
  <option value="Marketing">Marketing</option>
  <option value="Other">Other</option>
  {/* Add your options here */}
</select>
```

---

## 🔗 Add Navbar Links

**File: `/components/navbar.tsx`**

Add more navigation items:
```tsx
<button
  onClick={() => scrollToSection('features')}
  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
>
  Features
</button>
<button
  onClick={() => scrollToSection('pricing')}
  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
>
  Pricing
</button>
```

Add corresponding scroll sections in the page:
```tsx
<section id="features" className="scroll-mt-20">
  {/* Your content */}
</section>
```

---

## 🔐 Update Security/Social Proof

### Change Social Proof Companies

**File: `/components/social-proof.tsx`**
```tsx
{[
  'Your Partner 1',
  'Your Partner 2',
  'Your Partner 3',
  'Your Partner 4',
  'Your Partner 5',
].map((company) => (
  // ...
))}
```

### Add Real Social Links

**File: `/components/footer.tsx`**
```tsx
<a href="https://twitter.com/yourhandle" className="text-muted-foreground hover:text-accent transition-colors">
  <Twitter className="w-5 h-5" />
</a>
<a href="https://linkedin.com/company/yourcompany" className="text-muted-foreground hover:text-accent transition-colors">
  <Linkedin className="w-5 h-5" />
</a>
```

---

## 📊 Add Sections

### Add a Features Grid Section

Create `/components/features-grid.tsx`:
```tsx
'use client'

import { CheckCircle } from 'lucide-react'

export function FeaturesGrid() {
  const features = [
    { title: 'Feature 1', description: 'Description...' },
    { title: 'Feature 2', description: 'Description...' },
    // Add more features
  ]

  return (
    <section className="py-20 px-6 border-b border-border">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-4xl font-bold mb-12 text-center">All Features</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <div key={i} className="p-6 border border-border rounded-lg">
              <CheckCircle className="w-6 h-6 mb-3 text-accent" />
              <h3 className="font-semibold mb-2">{feature.title}</h3>
              <p className="text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

Add to `/app/page.tsx`:
```tsx
import { FeaturesGrid } from '@/components/features-grid'

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <Hero />
      {/* ... other sections ... */}
      <FeaturesGrid />
      {/* ... */}
      <Footer />
    </main>
  )
}
```

---

## 🎬 Add CTA Sections

### Add Mid-Page CTA

Create a call-to-action between sections:

```tsx
<section className="py-16 px-6 bg-gradient-to-r from-violet-500/10 to-indigo-500/10">
  <div className="max-w-4xl mx-auto text-center">
    <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
    <p className="text-muted-foreground mb-6">Join hundreds of founders already using our platform.</p>
    <Button 
      onClick={() => scrollToSection('waitlist')}
      className="bg-gradient-to-r from-violet-500 to-indigo-500"
    >
      Join Waitlist
    </Button>
  </div>
</section>
```

---

## ✅ Customization Checklist

- [ ] Update brand name everywhere
- [ ] Change company logo
- [ ] Update page title and meta description
- [ ] Change all headlines and subheadlines
- [ ] Update problem statements
- [ ] Add your features and benefits
- [ ] Update "How It Works" steps
- [ ] Change color scheme to match brand
- [ ] Update fonts if desired
- [ ] Add social media links
- [ ] Update footer links
- [ ] Customize form fields
- [ ] Test on mobile
- [ ] Deploy to production
- [ ] Set up analytics
- [ ] Monitor waitlist submissions

---

## 🚀 Next Steps After Customization

1. **Test everything locally**: `npm run dev`
2. **Build and check for errors**: `npm run build`
3. **Deploy to Vercel**: `git push`
4. **Test on production domain**
5. **Monitor waitlist submissions**
6. **Iterate based on feedback**

That's it! Your customized landing page is ready. 🎉
