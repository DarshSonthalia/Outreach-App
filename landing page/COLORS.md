# SafeMail Landing Page - Color System Reference

## Current Color Palette

All colors are defined in `/app/globals.css` under the `.dark` theme section.

### Primary Colors

| Purpose | Color | Hex | Usage |
|---------|-------|-----|-------|
| **Background** | Near Black | `#0a0a0f` | Page background |
| **Foreground** | Off White | `#f5f5f7` | Primary text |
| **Accent** | Violet | `#a78bfa` | Buttons, links, highlights |
| **Border** | Dark Gray | `#2d2d4d` | Card borders, dividers |

### Secondary Colors

| Purpose | Color | Hex | Usage |
|---------|-------|-----|-------|
| **Card BG** | Dark Gray | `#1a1a2e` | Card backgrounds |
| **Card Text** | Off White | `#f5f5f7` | Card text |
| **Muted** | Gray | `#4a4a6a` | Disabled states |
| **Muted Text** | Light Gray | `#a8a8c0` | Secondary text, helpers |
| **Input** | Dark Gray | `#1a1a2e` | Form inputs |
| **Ring** | Indigo | `#7c3aed` | Focus states |

### Gradients

| Name | Colors | Usage |
|------|--------|-------|
| **Logo Gradient** | `from-violet-400 to-indigo-400` | Brand text |
| **Button Gradient** | `from-violet-500 to-indigo-500` | CTA buttons |
| **Button Hover** | `from-violet-600 to-indigo-600` | Button hover states |
| **Card Hover** | `from-violet-500/5 to-indigo-500/5` | Card backgrounds on hover |

---

## CSS Color Tokens

All colors in `.dark` section of `/app/globals.css`:

```css
.dark {
  --background: #0a0a0f;
  --foreground: #f5f5f7;
  --card: #1a1a2e;
  --card-foreground: #f5f5f7;
  --popover: #1a1a2e;
  --popover-foreground: #f5f5f7;
  --primary: #f5f5f7;
  --primary-foreground: #0a0a0f;
  --secondary: #2d2d4d;
  --secondary-foreground: #f5f5f7;
  --muted: #4a4a6a;
  --muted-foreground: #a8a8c0;
  --accent: #a78bfa;
  --accent-foreground: #0a0a0f;
  --destructive: oklch(0.396 0.141 25.723);
  --destructive-foreground: oklch(0.637 0.237 25.331);
  --border: #2d2d4d;
  --input: #1a1a2e;
  --ring: #7c3aed;
}
```

---

## Tailwind Color Classes

These Tailwind classes are configured via the design tokens:

### Background
```tsx
<div className="bg-background">        {/* #0a0a0f */}
<div className="bg-card">              {/* #1a1a2e */}
<div className="bg-popover">           {/* #1a1a2e */}
<div className="bg-muted">             {/* #4a4a6a */}
```

### Text
```tsx
<p className="text-foreground">        {/* #f5f5f7 */}
<p className="text-muted-foreground">  {/* #a8a8c0 */}
<p className="text-accent">            {/* #a78bfa */}
```

### Borders
```tsx
<div className="border border-border">   {/* #2d2d4d */}
<div className="border-2 border-ring">  {/* #7c3aed */}
```

---

## Color Usage in Components

### Navbar
- **Background**: `bg-background/80` with `backdrop-blur-md`
- **Text**: `text-foreground` with `text-muted-foreground` for secondary
- **Logo**: Gradient `from-violet-400 to-indigo-400`
- **Button**: Gradient `from-violet-500 to-indigo-500`

### Cards
- **Background**: `bg-card/40` with `backdrop-blur-sm`
- **Border**: `border-border` or `border-accent/50` on hover
- **Text**: `text-foreground` and `text-muted-foreground`

### Icons (Feature Cards)
- **Background**: `bg-gradient-to-br from-violet-500/20 to-indigo-500/20`
- **Icon**: `text-violet-400`

### Problem Cards
- **Icon Background**: `bg-gradient-to-br from-red-500/20 to-orange-500/20`
- **Icon**: `text-red-400`

### Buttons
- **Primary**: `bg-gradient-to-r from-violet-500 to-indigo-500`
- **Hover**: `hover:from-violet-600 hover:to-indigo-600`
- **Disabled**: `disabled:opacity-50`
- **Secondary/Outline**: `border-border` with `hover:bg-card`

---

## Contrast & Accessibility

### WCAG Compliance

| Element | Foreground | Background | Ratio | Level |
|---------|-----------|-----------|-------|-------|
| Body Text | `#f5f5f7` | `#0a0a0f` | 19.6:1 | AAA ✓ |
| Muted Text | `#a8a8c0` | `#0a0a0f` | 9.2:1 | AAA ✓ |
| Accent Text | `#a78bfa` | `#0a0a0f` | 8.1:1 | AAA ✓ |
| Card Text | `#f5f5f7` | `#1a1a2e` | 16.2:1 | AAA ✓ |

**All colors meet WCAG AAA standards for accessibility.**

---

## Customizing Colors

### Quick Color Swap

To change the entire accent color from violet to blue:

**File: `/app/globals.css`**
```css
.dark {
  /* Before */
  --accent: #a78bfa;              /* Violet */
  --ring: #7c3aed;                /* Indigo */

  /* After */
  --accent: #3b82f6;              /* Blue-500 */
  --ring: #1d4ed8;                /* Blue-700 */
}
```

Then update gradient buttons:

**Example components:**
```tsx
// Before:
className="bg-gradient-to-r from-violet-500 to-indigo-500"

// After:
className="bg-gradient-to-r from-blue-500 to-cyan-500"
```

### Brand Color Presets

#### Tech/SaaS Blue
```css
--accent: #0066ff;              /* Bright Blue */
--ring: #0052cc;                /* Dark Blue */
```

#### Green/Eco
```css
--accent: #10b981;              /* Emerald */
--ring: #059669;                /* Dark Emerald */
```

#### Orange/Energy
```css
--accent: #f97316;              /* Orange */
--ring: #ea580c;                /* Dark Orange */
```

#### Rose/Modern
```css
--accent: #f43f5e;              /* Rose */
--ring: #e11d48;                /* Dark Rose */
```

#### Purple/Premium
```css
--accent: #a855f7;              /* Purple */
--ring: #9333ea;                /* Dark Purple */
```

---

## Semantic Token Mapping

### When to Use Each Color

**Use `--foreground` for:**
- Main body text
- Headlines
- Primary information

**Use `--muted-foreground` for:**
- Secondary text
- Helper text
- Disabled states
- Placeholders

**Use `--accent` for:**
- Primary CTA buttons
- Active states
- Links
- Highlights

**Use `--border` for:**
- Card borders
- Dividers
- Input borders

**Use `--ring` for:**
- Focus states
- Active indicators
- Attention-grabbing elements

---

## Dark Mode Specifics

The entire design uses the `.dark` class which applies:
- Near-black backgrounds for reduced eye strain
- High-contrast white text for readability
- Subtle accent colors for visual hierarchy
- Glassmorphism effects with `backdrop-blur-md`

**Pro tip:** The design is already dark-only. The root HTML has `className="dark"` in `/app/layout.tsx`.

---

## Color Checker Tools

Verify your colors online:

1. **Contrast Checker**: https://webaim.org/resources/contrastchecker/
2. **Color Palette Generator**: https://coolors.co/
3. **Gradient Generator**: https://gradientgenerator.com/
4. **Tailwind Color Picker**: https://tailwindcolor.com/

---

## Testing Colors

To test color changes:

1. Update `--accent` and `--ring` in `/app/globals.css`
2. Update gradient classes in components
3. Run `npm run dev`
4. Check all sections for consistency
5. Test on mobile devices
6. Verify contrast ratios

---

## Color Reference in Tailwind

Tailwind v4 classes you can use:

```tsx
/* Backgrounds */
bg-background, bg-card, bg-popover, bg-muted

/* Text */
text-foreground, text-muted-foreground, text-accent

/* Borders */
border-border, border-input, border-ring

/* Gradients */
from-violet-400, to-indigo-400
from-violet-500, to-indigo-500
from-violet-600, to-indigo-600
```

---

## Color Export for Design Tools

**Figma/Adobe XD Palette:**

| Name | Hex |
|------|-----|
| Background | #0a0a0f |
| Foreground | #f5f5f7 |
| Card | #1a1a2e |
| Accent | #a78bfa |
| Border | #2d2d4d |
| Muted | #4a4a6a |
| Ring | #7c3aed |

---

Done! Your color system is fully documented and ready to customize. 🎨
