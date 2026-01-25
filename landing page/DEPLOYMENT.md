# SafeMail Landing Page - Deployment Guide

## Quick Deploy to Vercel (Recommended)

### Option 1: Deploy from GitHub

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push -u origin main
   ```

2. **Connect to Vercel**
   - Go to https://vercel.com/new
   - Select your GitHub repository
   - Click "Deploy"
   - Done! 🎉

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Deploy**
   ```bash
   vercel
   ```

3. **Follow prompts** and your site will be live

### Option 3: Use v0's Deploy Button

1. In v0, click the three dots in the top right
2. Click "Download ZIP"
3. Extract the files
4. Use the Vercel CLI or GitHub method above

---

## Post-Deployment Setup

### 1. Custom Domain

1. **In Vercel Dashboard:**
   - Go to your project settings
   - Navigate to "Domains"
   - Add your custom domain
   - Follow DNS setup instructions

2. **Update metadata in `app/layout.tsx`:**
   ```typescript
   openGraph: {
     url: 'https://yourdomain.com',
     // ...
   }
   ```

### 2. Analytics

Already included via Vercel Analytics. Data is visible in:
- Vercel Dashboard → Project → Analytics

To view:
- Real-time traffic
- Page views
- Device breakdown
- Geographic distribution

### 3. Environment Variables (Optional)

If you add environment variables later:

1. **In Vercel Dashboard:**
   - Settings → Environment Variables
   - Add your variables
   - Redeploy

2. **Example `.env.local` for local development:**
   ```
   NEXT_PUBLIC_SITE_URL=http://localhost:3000
   DATABASE_URL=your_database_url
   ```

### 4. Email Notifications (Optional Setup)

To send confirmation emails when someone joins waitlist:

1. **Install email service** (choose one):
   ```bash
   npm install nodemailer        # For SMTP
   npm install @sendgrid/mail    # For SendGrid
   npm install resend            # For Resend
   ```

2. **Update `/app/api/waitlist/route.ts`:**
   ```typescript
   // Add after saving to database
   await sendWelcomeEmail(sanitizedData.workEmail, sanitizedData.fullName)
   ```

### 5. Database Migration (Optional)

To upgrade from JSON to database:

1. **Choose a provider:**
   - **Supabase** (PostgreSQL + Auth) - Recommended
   - **Neon** (PostgreSQL)
   - **PlanetScale** (MySQL)
   - **MongoDB Atlas** (NoSQL)

2. **Install client:**
   ```bash
   npm install @supabase/supabase-js
   ```

3. **Create table:**
   ```sql
   CREATE TABLE waitlist (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     full_name TEXT NOT NULL,
     work_email TEXT NOT NULL UNIQUE,
     company_name TEXT NOT NULL,
     role TEXT NOT NULL,
     monthly_volume TEXT NOT NULL,
     created_at TIMESTAMP DEFAULT NOW()
   );
   ```

4. **Update API route** to use database instead of JSON

### 6. Monitoring & Errors

1. **In Vercel Dashboard:**
   - Analytics → Errors
   - Monitor failed requests
   - Check server logs

2. **Add Sentry for error tracking** (optional):
   ```bash
   npm install @sentry/nextjs
   ```

---

## Troubleshooting

### Form submissions not working

**Issue**: 404 error when submitting form

**Solution**:
1. Check that `/app/api/waitlist/route.ts` exists
2. Rebuild: `npm run build`
3. Redeploy to Vercel

### Styling looks wrong

**Issue**: Dark theme not applying

**Solution**:
1. Ensure `globals.css` is imported in `app/layout.tsx`
2. Check that `<html className="dark">` is set in layout
3. Clear browser cache: Ctrl+Shift+Delete

### Mobile menu not working

**Issue**: Hamburger menu doesn't toggle

**Solution**:
1. Check browser console for JavaScript errors
2. Ensure `navbar.tsx` is using `'use client'`
3. Verify hydration is not causing issues

### Waitlist file not creating

**Issue**: `/data/waitlist.json` doesn't exist after first submission

**Solution**:
1. On Vercel, file system is read-only
2. **Migrate to database immediately** (see Database Migration above)
3. Or use Vercel KV for temporary storage

---

## Performance Optimization

### Caching

Enable edge caching in Vercel:

1. **In `next.config.mjs`:**
   ```javascript
   export default {
     headers: async () => [
       {
         source: '/(.*)',
         headers: [
           {
             key: 'Cache-Control',
             value: 'public, max-age=3600, stale-while-revalidate=86400',
           },
         ],
       },
     ],
   }
   ```

2. **Redeploy** to apply changes

### Image Optimization

- Currently no images (gradients only) ✅
- Keep it this way for best performance
- If adding images, use Next.js `<Image>` component

### Code Splitting

- Already handled by Next.js App Router ✅
- Components are lazy-loaded automatically

---

## Security Checklist

- ✅ Email validation
- ✅ Input sanitization
- ✅ HTTPS enabled (automatic on Vercel)
- ✅ No API keys exposed
- ✅ CORS headers set correctly
- ⚠️ Rate limiting (consider adding)
- ⚠️ Spam detection (optional)

### Add Rate Limiting

```typescript
// In /app/api/waitlist/route.ts
import { Ratelimit } from '@upstash/ratelimit'
import { Redis } from '@upstash/redis'

const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(5, '1 h'),
})

// In POST handler:
const { success } = await ratelimit.limit(request.ip!)
if (!success) {
  return NextResponse.json({ error: 'Too many requests' }, { status: 429 })
}
```

---

## Backup & Maintenance

### Regular Backups

1. **For JSON storage** (development only):
   - Copy `/data/waitlist.json` to safe location
   - Daily via git commits

2. **For database storage:**
   - Enable automated backups in database provider dashboard
   - Most providers do this automatically

### Monitoring Checklist

- [ ] Check Vercel analytics weekly
- [ ] Monitor error logs daily
- [ ] Test form submission weekly
- [ ] Check domain SSL certificate validity
- [ ] Review waitlist growth trends
- [ ] Update content as needed

---

## Updating the Site

### Push Updates

1. **Make changes locally**
   ```bash
   git add .
   git commit -m "Update content"
   git push
   ```

2. **Vercel automatically deploys** (if connected to GitHub)

3. **View deployment status** in Vercel Dashboard

### Rollback

If something breaks:
1. Go to Vercel Dashboard → Deployments
2. Find the previous working deployment
3. Click "Rollback"

---

## Next.js Version Updates

Every few months, update Next.js for security and performance:

```bash
npm update next
npm run build
npm run dev  # Test locally
git push    # Auto-deploys to Vercel
```

---

## Support & Questions

- **Next.js Docs**: https://nextjs.org/docs
- **Vercel Docs**: https://vercel.com/docs
- **Tailwind CSS**: https://tailwindcss.com/docs
- **shadcn/ui**: https://ui.shadcn.com

---

**You're all set!** Your SafeMail landing page is now live and production-ready. 🚀
