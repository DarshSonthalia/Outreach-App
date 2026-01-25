# ⚡ Quick Start Guide - 5 Minutes to Launch

Get your SafeMail landing page live in 5 minutes.

---

## 🎯 Step 1: Download & Setup (2 mins)

```bash
# Clone this repository (or download ZIP)
git clone <your-repo-url>
cd safemail-landing

# Install dependencies
npm install

# Start development server
npm run dev

# Visit http://localhost:3000
```

---

## 🎨 Step 2: Customize (2 mins)

### Update Your Company Name
Open these files and replace `SafeMail`:
- `/components/navbar.tsx` (line 18)
- `/components/footer.tsx` (line 12)
- `/app/layout.tsx` (line 11, 13, 16, 22)

**Find & Replace shortcut:**
1. Press `Ctrl+Shift+H` (Cmd+Shift+H on Mac)
2. Find: `SafeMail`
3. Replace: `Your Company Name`
4. Replace All

### Update Headlines
Open `/components/hero.tsx` and edit:
- Line 24: Main headline
- Line 28: Subheadline

Open `/components/problem-section.tsx` and edit problem titles/descriptions.

---

## 🚀 Step 3: Deploy (1 min)

### Option A: GitHub + Vercel (Recommended)

```bash
# Push to GitHub
git add .
git commit -m "Initial commit"
git push origin main
```

Then go to **https://vercel.com/new** and:
1. Select your repository
2. Click "Deploy"
3. Your site is LIVE! 🎉

### Option B: Vercel CLI

```bash
npm install -g vercel
vercel
```

Follow the prompts and deploy.

---

## ✅ Step 4: Test Waitlist (30 secs)

1. Scroll to the bottom of your site
2. Fill out the waitlist form
3. Click "Request Access"
4. See success message ✓

**Note:** On Vercel, submissions are stored temporarily. Upgrade to a database for production (see DEPLOYMENT.md).

---

## 🔗 Step 5: Connect Domain (Optional)

In Vercel Dashboard:
1. Go to your project
2. Settings → Domains
3. Add your domain (e.g., app.yourcompany.com)
4. Follow DNS setup

---

## 📊 Done! What's Next?

- Monitor analytics at https://vercel.com/dashboard
- Share your link: `https://your-domain.vercel.app`
- Track waitlist: Check `/data/waitlist.json` locally (or use GET `/api/waitlist`)
- Customize further using CUSTOMIZATION.md

---

## 🚦 Common Quick Changes

### Change Accent Color
Edit `/app/globals.css` line 48:
```css
--accent: #a78bfa;  /* Change this hex value */
```

Then update button gradients in components:
```tsx
// Before
className="bg-gradient-to-r from-violet-500 to-indigo-500"

// After
className="bg-gradient-to-r from-blue-500 to-cyan-500"
```

### Add New Navbar Link
Edit `/components/navbar.tsx` around line 30:
```tsx
<button
  onClick={() => scrollToSection('your-section')}
  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
>
  Your Link
</button>
```

### Change Form Fields
Edit `/components/waitlist-form.tsx`:
- Add new field to `FormData` interface (line 10)
- Add input element (line 100+)
- Add to form submission

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Dev server won't start | Run `npm install` first |
| Styles not loading | Make sure `globals.css` is imported in `layout.tsx` |
| Form not submitting | Check `/app/api/waitlist/route.ts` exists |
| Colors look wrong | Clear browser cache (Ctrl+Shift+Delete) |
| Mobile menu broken | Refresh page (Cmd+R) |

---

## 📚 Full Guides (When You're Ready)

- **DEPLOYMENT.md** - Full deployment guide with options
- **CUSTOMIZATION.md** - Complete customization walkthrough
- **BUILD_SUMMARY.md** - What's included & architecture
- **COLORS.md** - Color system reference
- **README.md** - Full project documentation

---

## 🎯 Quick Customization Checklist

- [ ] Update company name (5 files)
- [ ] Change headlines in Hero section
- [ ] Update problem/solution copy
- [ ] Change accent color in globals.css
- [ ] Test form submission
- [ ] Deploy to Vercel
- [ ] Share with team
- [ ] Collect feedback

---

## 🚀 You're Live!

That's it! Your production-ready SaaS landing page is now online.

**Next:** Use CUSTOMIZATION.md for more detailed changes.

---

**Questions?**
- Check README.md for features
- See DEPLOYMENT.md for advanced setup
- Review CUSTOMIZATION.md for detailed changes

**Happy shipping!** 🎉
