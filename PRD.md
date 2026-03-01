# PRD: StockPulse v2.0 — Frontend Redesign

## Problem

The current StockPulse dashboard works well functionally but looks generic and "AI-generated." All cards are uniform boxes, the color scheme is flat, there's no personality or delight, and the layout doesn't guide the user's eye. For StockPulse to stand out and feel premium, the frontend needs a complete visual and interaction overhaul — while keeping the exact same backend API and data structure.

## Goals

1. Transform the dashboard from "functional prototype" to "polished product" that feels hand-crafted
2. Create a memorable visual identity with personality and micro-interactions
3. Guide users through data with clear information hierarchy and progressive disclosure
4. Make the app feel responsive, alive, and playful without being unprofessional
5. Keep both pages (Dashboard + Scanner) and all existing features working identically

## Constraints

- **No backend changes** — same API endpoints, same data models, same Python code
- **CDN-only** — keep using Tailwind CSS CDN + Chart.js CDN (no build tooling)
- **Single HTML files** — `index.html` and `scanner.html` remain self-contained
- **Dark mode only** — dark theme is the brand identity
- **Performance** — no heavy libraries beyond Tailwind + Chart.js

---

## Design System

### Color Palette

Replace the flat dark navy with a richer, layered palette using subtle gradients and glass effects:

```
Background:     #0a0f1e (deep space blue, slightly warmer than current)
Surface-1:      #111827 (primary card background)
Surface-2:      #1a2235 (elevated cards, modals)
Surface-3:      #232d42 (hover states, active elements)
Glass:          rgba(255,255,255,0.03) with backdrop-blur (glassmorphism panels)
Border:         rgba(255,255,255,0.06) (subtle, not harsh lines)
Border-hover:   rgba(255,255,255,0.12)

Text-primary:   #f1f5f9 (off-white, not pure white — reduces eye strain)
Text-secondary: #94a3b8
Text-muted:     #64748b

Accent-green:   #34d399 (brighter, more vibrant than current #10b981)
Accent-red:     #f87171 (softer red, less alarming)
Accent-blue:    #60a5fa (lighter, more inviting blue)
Accent-amber:   #fbbf24

Signal-BUY:     linear-gradient(135deg, #34d399, #059669)
Signal-SELL:    linear-gradient(135deg, #f87171, #dc2626)
Signal-HOLD:    linear-gradient(135deg, #94a3b8, #64748b)

Confidence gradient (used for confidence meters):
  90-100:  #34d399 (strong green)
  75-89:   #60a5fa (blue)
  60-74:   #fbbf24 (amber)
  0-59:    #94a3b8 (gray)
```

### Typography

```
Headings:       'Inter', system-ui, sans-serif — weight 700, letter-spacing -0.02em
Body:           'Inter', system-ui, sans-serif — weight 400
Monospace/Data: 'JetBrains Mono', monospace — for prices, percentages, numbers

Load via CDN:
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### Spacing & Grid

Use an 8px base grid:
```
xs: 4px   (tight inline gaps)
sm: 8px   (between related items)
md: 16px  (card padding, between components)
lg: 24px  (section separation)
xl: 32px  (major section gaps)
2xl: 48px (page-level spacing)
```

### Elevation & Depth

Create depth with layered shadows and glass:
```css
/* Card resting state */
.card {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.02) inset;
    border-radius: 16px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Card hover */
.card:hover {
    border-color: rgba(255,255,255,0.12);
    box-shadow: 0 8px 25px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.05) inset;
    transform: translateY(-2px);
}

/* Glass panel (for overlays, header, signal panel) */
.glass {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.06);
}

/* Modal overlay */
.modal-bg {
    background: rgba(0,0,0,0.6);
    backdrop-filter: blur(8px);
}
```

### Micro-Interactions & Animations

```css
/* Smooth page entry — cards stagger in */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Pulse animation for live data indicators */
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* Number count-up animation for metrics */
@keyframes countUp {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Confidence ring fill (circular progress) */
@keyframes ringFill {
    from { stroke-dashoffset: 100; }
    to { stroke-dashoffset: var(--ring-offset); }
}

/* Toast slide + fade */
@keyframes toastIn {
    from { transform: translateX(120%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
@keyframes toastOut {
    to { transform: translateX(120%); opacity: 0; }
}
```

---

## Page 1: Dashboard (`index.html`)

### Header

Replace the flat header with a glass-morphism navbar:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ◉ StockPulse          Dashboard  Scanner          ● LIVE    ↻ Refresh    │
│                                                    Updated 2m ago         │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Logo**: "StockPulse" with a subtle gradient text (blue → purple) and a small animated pulse dot ◉ before it
- **Nav tabs**: Pill-style with smooth sliding indicator (the active tab has a subtle glow background that slides when switching)
- **Live indicator**: Small green dot with pulse animation + "LIVE" text when market is open; gray dot + "CLOSED" when market closed
- **Last updated**: Relative time ("Updated 2m ago") instead of absolute timestamp — updates reactively
- **Refresh button**: Icon-only circle button, rotates on click with smooth easing

### Hero Stats Row

Replace the 4 plain boxes with a more engaging stats bar:

```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  📊 5        │ │  ▲ 2 Active  │ │  ● Market    │ │  Bullish     │
│  Tracked     │ │  Signals     │ │    Open       │ │  ██████░░ 3:2│
│              │ │  ↑1 from     │ │  Closes 4:00p │ │              │
│              │ │  yesterday   │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

- **Numbers animate in** with a count-up effect on page load
- **Sentiment card**: Shows a mini horizontal bar (green vs red segments) representing BUY vs SELL ratio visually, not just text
- **Market card**: Shows "Closes in Xh Ym" countdown during market hours, "Opens in Xh Ym" outside hours (using New York market hours: 9:30 AM - 4:00 PM ET)

### Stock Cards Grid

The cards are the heart of the app. Make them distinctive and information-rich without being cluttered:

```
┌─────────────────────────────────────────┐
│  GOOGL              BUY ●●●●○  82/100  │
│  Alphabet Inc.      ▓▓▓▓▓▓▓▓░░         │
│                                         │
│  $178.42         ▲ +1.24%               │
│                                         │
│  ╭─────────────────────────────╮        │
│  │        ╱╲    ╱╲             │        │
│  │  ╱╲╱╲╱╱  ╲╱╱  ╲╱╲         │        │
│  │ ╱                  ╲        │        │
│  ╰─────────────────────────────╯        │
│                                         │
│  RSI 42.1    MACD +0.34    Vol 1.2x     │
│                                   [✕]   │
└─────────────────────────────────────────┘
```

**Key changes from current:**

1. **Confidence meter**: Replace the plain "82/100" badge with a visual dot meter (●●●●○) or a thin horizontal progress bar with gradient fill. The bar color follows the confidence gradient (green/blue/amber/gray).

2. **Signal badge**: Use gradient-filled pills instead of bordered text. BUY gets a green gradient pill, SELL gets red, HOLD gets gray. Add a subtle glow shadow matching the signal color.

3. **Sparkline upgrade**: Make the sparkline taller (increase from 40px to 56px height), add a gradient fill below the line (green-to-transparent or red-to-transparent based on trend), and show the current price as a small dot at the end of the line.

4. **Indicator row**: Use monospace font for numbers. Color-code each value inline. RSI: green if <30, red if >70. MACD: green if positive, red if negative.

5. **Remove button**: Replace text "Remove" with a small "✕" icon in the bottom-right corner, only visible on hover (opacity transition).

6. **Stagger animation**: Cards animate in one by one with 50ms delay between each (using `animation-delay` calculated per card index).

7. **Card hover**: On hover, the card border subtly glows in the signal color (green glow for BUY cards, red for SELL, blue-gray for HOLD).

### Active Signals Panel

Transform from a plain list into a "command center" sidebar:

```
┌─────────────────────────┐
│  ⚡ Active Signals      │
│                         │
│  ┌─────────────────────┐│
│  │ ● GOOGL        BUY  ││
│  │   82/100  RSI oversold│
│  │   ▓▓▓▓▓▓▓▓░░        ││
│  └─────────────────────┘│
│                         │
│  ┌─────────────────────┐│
│  │ ● NVDA         BUY  ││
│  │   76/100  Golden cross│
│  │   ▓▓▓▓▓▓▓░░░        ││
│  └─────────────────────┘│
│                         │
│  No sell signals today   │
│                         │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│  💡 Tip: Click a signal │
│  to see full analysis   │
└─────────────────────────┘
```

- **Section header**: "Active Signals" with a ⚡ icon
- **Signal items**: Each has a left-border accent color (green/red), a confidence bar, and the top reason in small text
- **Empty state**: If no sell signals, say "No sell signals today" with a subtle checkmark or calm message instead of just blank space
- **Tip**: Show a contextual tip at the bottom for first-time visitors (store in localStorage, hide after first click)

### Add Stock Modal

Make it feel more polished:

```
┌─────────────────────────────────────────┐
│                                         │
│  Add to Watchlist                       │
│                                         │
│  ┌─────────────────────────────────────┐│
│  │ 🔍  Search stocks...               ││
│  └─────────────────────────────────────┘│
│                                         │
│  ┌─ AAPL ─────────────────────────────┐│
│  │  Apple Inc.              NASDAQ     ││
│  ├─────────────────────────────────────┤│
│  │  AMZN                               ││
│  │  Amazon.com Inc.         NASDAQ     ││
│  ├─────────────────────────────────────┤│
│  │  AMD                                ││
│  │  Advanced Micro Devices  NASDAQ     ││
│  └─────────────────────────────────────┘│
│                                         │
│  ┌─────────────────────────────────────┐│
│  │  ✓ AAPL — Apple Inc.      [Clear]  ││
│  └─────────────────────────────────────┘│
│                                         │
│     [ Add to Watchlist ]    [ Cancel ]  │
│                                         │
└─────────────────────────────────────────┘
```

- Modal slides up from bottom with a spring animation
- Search results have hover highlight with smooth transition
- Selected stock shows a check icon and the card has a blue border glow
- "Add to Watchlist" button has full width, gradient blue background
- On successful add, briefly show a green checkmark animation before closing

### Detail Modal

This is the biggest redesign opportunity. The current modal dumps everything in a vertical scroll. Redesign with **tabbed sections** for progressive disclosure:

```
┌─────────────────────────────────────────────────────────────────────┐
│  GOOGL — Alphabet Inc.                                        [✕]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  $178.42          ▲ +$2.18 (+1.24%)          BUY  ●●●●○  82/100   │
│                                                                     │
│  [ Overview ]  [ Technical ]  [ Backtest ]                         │
│  ━━━━━━━━━━━                                                       │
│                                                                     │
│  ┌─ Overview Tab ──────────────────────────────────────────────────┐│
│  │                                                                  │
│  │  CHART (with period buttons: 1M 3M 6M 1Y)                      │
│  │  ┌──────────────────────────────────────────────────────────┐   │
│  │  │                                                          │   │
│  │  │              Price chart with SMAs + Volume              │   │
│  │  │                                                          │   │
│  │  └──────────────────────────────────────────────────────────┘   │
│  │                                                                  │
│  │  ┌─ Key Levels ────┐  ┌─ Company Info ────┐  ┌─ Advisor ──────┐│
│  │  │ Support  $165.20│  │ Sector: Tech      │  │ Summary text   ││
│  │  │ Resist.  $185.40│  │ MCap: $2.2T       │  │ of analysis... ││
│  │  │ Stop     $170.10│  │ P/E: 25.4         │  │                ││
│  │  └─────────────────┘  └───────────────────┘  └────────────────┘│
│  │                                                                  │
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─ Technical Tab (hidden until clicked) ──────────────────────────┐│
│  │  Indicator cards (RSI, MACD, Stoch, ATR, SMAs, Volume, BB)      │
│  │  Bullish signals list                                            │
│  │  Bearish signals list                                            │
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─ Backtest Tab (hidden until clicked) ───────────────────────────┐│
│  │  Run Backtest button → shows metrics, equity curve, trade log   │
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Tab system:**
- 3 tabs: **Overview** | **Technical** | **Backtest**
- Active tab has a bottom border indicator (animated slide)
- Tab content fades in/out smoothly (opacity + translateY transition)
- Overview is the default tab — shows chart, key levels, company info, and advisor summary
- Technical tab shows all indicator cards, bullish/bearish signal lists
- Backtest tab shows the run button + results (same backtest UI as currently built, but inside a tab)

**Other improvements:**
- Price display uses monospace font with slight letter-spacing for readability
- Signal badge at the top has the gradient style + glow shadow
- Confidence shown as a circular SVG ring (small donut chart showing fill %) next to the confidence number
- Modal has smooth enter animation (scale from 0.95 → 1.0 with fade, 200ms)

### Footer

Simplify and add personality:

```
┌─────────────────────────────────────────────────────────────────────┐
│  StockPulse v1.1                    Data: Yahoo Finance            │
│  Educational purposes only.         Auto-refresh: 4:32             │
│  Not financial advice.                                              │
└─────────────────────────────────────────────────────────────────────┘
```

- Remove the wall-of-text disclaimer; replace with a single concise line + a "Learn more" link that opens a small popover with the full legal text
- Two-column layout: branding left, data info right
- Subtle top border with a gradient (dark to slightly lighter to dark)

### Toast Notifications

Upgrade with better styling:

- Glass background with colored left-border accent
- Icon on the left (checkmark for success, x for error, i for info)
- Slide in from top-right, slide out to right on dismiss
- Clickable to dismiss early
- Stack up to 3 toasts, older ones compress

---

## Page 2: Scanner (`scanner.html`)

### Same header and design system as dashboard.

### Progress Section (during scan)

Replace the plain progress bar with a more engaging visualization:

```
┌─────────────────────────────────────────────────────────────────────┐
│  📡 Scanning S&P 500...                              247 / 503     │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░  49%            │
│                                                                     │
│  🟢 BUY: 18    🔴 SELL: 12    ⚪ HOLD: 204    ⚠ Errors: 13       │
│  Estimated time remaining: ~4 minutes                               │
└─────────────────────────────────────────────────────────────────────┘
```

- Animated gradient on the progress bar (moving shimmer effect)
- Estimate remaining time based on elapsed time and progress percentage
- Stats update live every poll

### Stats Cards

Same style as dashboard hero stats, but scanner-specific:

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ 503      │ │ 24       │ │ 15       │ │ 464      │ │ Mar 1, 2026  │
│ Scanned  │ │ BUY      │ │ SELL     │ │ HOLD     │ │ Last Scan    │
│          │ │ ▓▓░░░ 5% │ │ ▓░░░░ 3% │ │ ▓▓▓▓▓ 92%│ │ 6:00 AM      │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘
```

- Each stat card shows a tiny proportion bar below the count
- Numbers animate up on load

### Filters Bar

Make filters more interactive:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Signal: [ All ▼ ]   Sector: [ All Sectors ▼ ]                     │
│                                                                     │
│  Confidence: ○─────────●──────○  65       Showing: 142 results     │
│              0                100                                   │
└─────────────────────────────────────────────────────────────────────┘
```

- Styled select dropdowns (custom appearance matching the dark theme)
- Confidence slider has a custom-styled thumb (circle) and track (gradient from gray to green)
- Filters apply with a subtle fade transition on the results table
- Add a "Reset filters" text button when any filter is active

### Results Table

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  Symbol   Name                  Sector          Price     Chg     Signal  Conf   │
├──────────────────────────────────────────────────────────────────────────────────┤
│  ● NVDA   NVIDIA Corp.          Technology     $142.50   ▲+2.3%  [BUY]   88     │
│  ● AAPL   Apple Inc.            Technology     $198.20   ▲+0.8%  [BUY]   82     │
│  ● XOM    Exxon Mobil           Energy         $105.30   ▼-1.2%  [SELL]  76     │
│  ...                                                                             │
├──────────────────────────────────────────────────────────────────────────────────┤
│  ◀ Previous          Page 1 of 3              Next ▶                             │
└──────────────────────────────────────────────────────────────────────────────────┘
```

- **Row hover**: Subtle highlight with the signal color (very faint green/red/gray background)
- **Confidence column**: Show as a small inline progress bar + number, not just a number
- **Signal badges**: Same gradient pill style as dashboard cards
- **"+ Watch" button**: Appears on row hover, not always visible (reduces visual clutter)
- **Sticky header**: Table header stays visible while scrolling
- **Empty state**: Friendly message: "No scan results yet. Run a scan to discover signals across the entire S&P 500."

---

## Interaction Details

### Loading States

Replace plain skeleton loaders with more polished versions:
- Cards: Show 3 skeleton cards with staggered shimmer animation (each card's shimmer starts 200ms after the previous)
- Numbers: Show a dash with a subtle pulse animation instead of static "-"
- Charts: Show a flat gray area with a faint grid pattern, not just empty space
- Tables: Show 5 skeleton rows with alternating widths for visual variety

### Transitions

- **Page elements**: Fade-slide-up on initial load (staggered 50ms per element)
- **Tab switching**: Content fades out (100ms), new content fades in (150ms) with 4px upward slide
- **Modal open**: Background blurs in (200ms), modal scales from 0.97 to 1.0 with fade (250ms, cubic-bezier easing)
- **Modal close**: Reverse of open, faster (150ms)
- **Card removal**: Card shrinks + fades out (200ms), remaining cards shift to fill gap smoothly (300ms)
- **Toast**: Slide in from right (300ms spring), auto-dismiss slides out right (200ms)
- **Hover effects**: All hovers use `transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1)`

### Empty States

- **No stocks**: "Your watchlist is empty. Add your first stock to get started." with a prominent "Add Stock" button
- **No signals**: "All quiet — no actionable signals right now. The market will speak when it's ready."
- **No scanner results**: "No scan results yet. Run a scan to discover signals across the entire S&P 500."
- **Backtest no data**: "Not enough historical data to run a meaningful backtest (need 250+ days)."

---

## Implementation Notes

### Files to Modify

1. **`app/dashboard/templates/index.html`** — Complete rewrite of HTML structure, CSS, and JavaScript
2. **`app/dashboard/templates/scanner.html`** — Complete rewrite matching the new design system

### External Dependencies (CDN only, no new libraries)

- Tailwind CSS (already used): `https://cdn.tailwindcss.com`
- Chart.js (already used): `https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js`
- Inter font: `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap`
- JetBrains Mono font: `https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap`

### What stays the same

- All API calls (`/api/stocks`, `/api/stocks/{symbol}`, `/api/search`, etc.)
- All data structures (stock objects, indicators, signals, backtest results, scanner results)
- All JavaScript function names and their core logic
- Auto-refresh behavior (5 minute countdown)
- localStorage preferences
- All backend code (Python, FastAPI, scheduler, WhatsApp)

### Chart.js Theming

Apply consistent theming to all Chart.js instances:
```javascript
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 11;
```

### Confidence Ring (SVG Component)

For the circular confidence indicator used on cards and detail modal:
```html
<svg width="36" height="36" viewBox="0 0 36 36">
  <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="3"/>
  <circle cx="18" cy="18" r="14" fill="none" stroke="currentColor" stroke-width="3"
    stroke-dasharray="88" stroke-dashoffset="CALCULATED" stroke-linecap="round"
    transform="rotate(-90 18 18)" style="transition: stroke-dashoffset 0.6s ease-out"/>
  <text x="18" y="18" text-anchor="middle" dominant-baseline="central"
    fill="currentColor" font-size="10" font-weight="600">82</text>
</svg>
```

The `stroke-dashoffset` is calculated as: `88 - (88 * confidence / 100)`.

---

## Verification

After implementation, verify:
1. All stock cards render correctly with new styling
2. Signal badges show proper gradient colors
3. Cards animate in with stagger on page load
4. Detail modal opens with tabs working (Overview, Technical, Backtest)
5. Backtest still runs and displays results in the Backtest tab
6. Scanner page shows progress bar during scan
7. Scanner results table is filterable and paginated
8. Add Stock modal with autocomplete works
9. Toast notifications appear and dismiss correctly
10. Auto-refresh countdown still works
11. Responsive layout works on mobile (test at 375px, 768px, 1024px, 1440px)
12. Chart.js charts render with new theming
13. No console errors
14. Run the app with `python run.py` and test all pages
