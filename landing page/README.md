# SafeMail - AI-Powered Email Outreach Platform

A production-ready SaaS landing page for SafeMail, a safety-first email outreach platform for founders and sales teams.

## 🚀 Overview

This is a high-conversion B2B SaaS landing page built with Next.js 14, TypeScript, and Tailwind CSS. It features:

- **Dark mode SaaS design** with glassmorphism cards and indigo/violet accent gradients
- **Smooth animations** with scroll transitions and hover effects
- **Full responsiveness** for all device sizes
- **Production-ready** waitlist system with form validation
- **SEO optimized** with proper metadata, OpenGraph, and structured data
- **Performance focused** with gradients, no heavy images

## 📁 Project Structure

```
├── app/
│   ├── page.tsx                 # Main landing page
│   ├── layout.tsx               # Root layout with metadata
│   ├── globals.css              # Global styles & theme
│   └── api/
│       └── waitlist/
│           └── route.ts         # Waitlist API endpoint
├── components/
│   ├── navbar.tsx               # Fixed navigation with mobile menu
│   ├── hero.tsx                 # Hero section with CTA
│   ├── social-proof.tsx         # Social proof / trust badges
│   ├── problem-section.tsx      # Problem statement (3 cards)
│   ├── solution-section.tsx     # Solution features (4 cards)
│   ├── how-it-works.tsx         # Step-by-step timeline
│   ├── safety-section.tsx       # Safety/security differentiator
│   ├── ai-section.tsx           # AI features overview
│   ├── waitlist-section.tsx     # Waitlist CTA container
│   ├── waitlist-form.tsx        # Waitlist form with validation
│   ├── footer.tsx               # Footer with links & socials
│   └── ui/                      # shadcn/ui components
├── data/
│   └── waitlist.json            # Waitlist entries (auto-created)
└── README.md
```

## 🎨 Design System

### Color Palette

- **Background**: `#0a0a0f` (near-black)
- **Cards**: `#1a1a2e` (dark gray with blur)
- **Text**: `#f5f5f7` (high-contrast white)
- **Muted Text**: `#a8a8c0` (subtle gray)
- **Accent**: `#a78bfa` (indigo/violet)
- **Ring**: `#7c3aed` (focus state)

### Typography

- **Font**: Geist (sans-serif)
- **Headings**: Bold, large scale (5xl-7xl for hero)
- **Body**: Readable, 16-18px base size
- **Line Height**: 1.5-1.6 for comfortable reading

## 🔧 Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **UI Components**: shadcn/ui
- **Icons**: Lucide React
- **Data Storage**: JSON file (development) or upgrade to database
- **Animation**: CSS + Tailwind animations
- **HTTP Client**: Fetch API

## 🚀 Getting Started

### Installation

1. **Clone or download this project**

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Run development server**
   ```bash
   npm run dev
   ```

4. **Open browser**
   Navigate to `http://localhost:3000`

### Deploy to Vercel

The easiest way to deploy is to use [Vercel](https://vercel.com):

1. **Push to GitHub** (if not already)
2. **Connect to Vercel** at https://vercel.com/new
3. **Select this repository**
4. **Deploy** (no env vars needed for basic setup)

## 📝 Features

### Waitlist System

The waitlist form collects:
- Full Name (required)
- Work Email (required, validated)
- Company Name (required)
- Role (dropdown: Founder, Sales, Marketing, Other)
- Monthly Email Volume (range select)

**Validation:**
- All fields required
- Email format validation
- Duplicate email prevention
- Sanitization against XSS

**Storage:**
- Development: JSON file at `/data/waitlist.json`
- Production: Recommend upgrading to database (Supabase, Neon, etc.)

### API Endpoints

#### POST /api/waitlist
Submit a new waitlist entry.

**Request:**
```json
{
  "fullName": "Alex Johnson",
  "workEmail": "alex@company.com",
  "companyName": "Acme Inc",
  "role": "Founder",
  "monthlyVolume": "1k-5k"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "You have been added to the waitlist",
  "id": "1234567890-abc123"
}
```

#### GET /api/waitlist
Retrieve waitlist statistics.

**Response:**
```json
{
  "count": 42,
  "message": "42 people on the waitlist"
}
```

## 🔐 Security

- Email validation (regex check)
- Duplicate prevention
- Input sanitization (trimmed strings)
- No sensitive data exposure
- CORS-ready for frontend requests
- Type-safe with TypeScript

## 📱 Responsive Design

- **Mobile First** approach
- **Breakpoints**: md (768px), lg (1024px)
- **Navbar**: Hamburger menu on mobile
- **Forms**: Full-width on mobile, optimized spacing
- **Typography**: Responsive sizes (5xl → 7xl hero)

## 🎯 SEO

- Page title: "SafeMail - AI-Powered Cold Email That Protects Your Domain"
- Meta description optimized for CTR
- OpenGraph tags for social sharing
- Twitter Card support
- Semantic HTML with proper heading hierarchy
- Mobile viewport configuration

## 📈 Performance

- **No heavy images** (gradients only)
- **CSS animations** instead of JavaScript
- **Smooth scroll** behavior
- **Optimized bundle** size
- **Fast load times** with minimal dependencies

## 🎨 Customization

### Change Brand Name
Find and replace `SafeMail` with your company name across:
- `navbar.tsx`
- `footer.tsx`
- `app/layout.tsx` (metadata)

### Update Colors
Edit color tokens in `/app/globals.css` under the `.dark` section:
```css
.dark {
  --background: #0a0a0f;
  --foreground: #f5f5f7;
  --accent: #a78bfa;
  /* ... */
}
```

### Modify Content
All copy is in individual component files. Update text directly in each section component.

### Add Database Integration

Replace the JSON file storage with a proper database:

1. **Supabase** (recommended):
   ```bash
   npm install @supabase/supabase-js
   ```

2. **Neon PostgreSQL**:
   ```bash
   npm install @neondatabase/serverless
   ```

3. Update `/app/api/waitlist/route.ts` to use the database client

## 🚀 Next Steps

1. **Customize copy** - Update all text to match your product
2. **Add analytics** - Vercel Analytics is already installed
3. **Setup database** - Move from JSON to production database
4. **Add email notifications** - Send welcome emails on signup
5. **Create admin dashboard** - View and export waitlist
6. **Setup domain** - Use your custom domain instead of vercel.app

## 📧 Waitlist Export

To export waitlist entries:
1. Read `/data/waitlist.json`
2. Parse the JSON array
3. Export to CSV or email service

Or access via the GET endpoint and pipe to a file:
```bash
curl https://your-domain.com/api/waitlist > waitlist.json
```

## 🔑 Environment Variables

Currently, no environment variables are required for basic deployment. However, you may want to add:

- `NEXT_PUBLIC_SITE_URL` - For canonical URLs in metadata
- `DATABASE_URL` - When upgrading to a database
- `EMAIL_API_KEY` - For sending confirmation emails

## 📄 License

This template is provided as-is for your use. Customize and deploy freely.

## 💡 Tips

- Use the design inspiration images as reference for SaaS best practices
- The Navbar is sticky and updates based on scroll position
- Smooth scroll navigation works by clicking navbar links
- Form validation prevents invalid submissions
- Success state shows after form submission
- Mobile menu closes on link click for better UX

---

**Ready to launch?** Deploy to Vercel with one click. Your SafeMail landing page is production-ready! 🚀
