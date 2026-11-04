# UI Design System — "Emerald Luxe" (SaaS, light + dark)

A single, consistent design system across every page. The product reads as a
polished, high-end SaaS application: an emerald brand with a gold luxury accent,
dark emerald mesh showcases, generous whitespace, soft layered shadows, and a
full light **and dark** theme.

> **Direction history (user-requested).** Started as "Sky-Blue editorial", moved
> to "Modern SaaS (indigo)", now "Emerald Luxe" with a gold accent + dark mode,
> per the user's request for a high-luxury SaaS look. The absolute product rules
> are unchanged: **no fabricated stats/activity/testimonials, no AI branding, no
> monetary features.** The landing conveys premium *feel* through design and
> honest content — it invents no numbers, logos, or reviews.

## Theming

- Tokens live in `static/css/_variables.css`. `:root` is the light theme;
  `html[data-theme="dark"]` overrides surface/text/border/shadow tokens. The
  brand ramp is shared by both themes.
- Theme is toggled by the header button, persisted in `localStorage`
  (`skillswap-theme`), and applied **before paint** by a tiny inline script in
  `base.html` (no flash). `<meta name="color-scheme" content="light dark">`.
- Retheme the whole app by editing the brand ramp — every component uses tokens.

## Palette

| Role | Token(s) | Usage |
|---|---|---|
| Brand | `--brand-50 … --brand-800` (emerald) | primary actions, links, active nav, accents |
| Partner | `--teal-500/600` | "learn" pills, info |
| Accent | `--accent-400/500/600` (gold) | hero accent text, gold feature tile, highlights |
| Signature gradients | `--gradient-brand` (emerald→teal), `--gradient-gold` | buttons, brand mark, CTA |
| Hero mesh | `--hero-ink` + `--hero-mesh` | dark emerald hero, showcase visual, free band |
| Surfaces | `--surface`, `--surface-2/3`, `--bg` | cards, page background (per theme) |
| Text | `--text`, `--text-muted`, `--text-subtle` | copy hierarchy (per theme) |
| Semantic | `--success/danger/warning/info` (+ `-bg`/`-bd`) | flash, status badges |

## Backgrounds (proxy-safe)

External image requests don't survive the dev path-rewriting proxy (same reason
CSS is inlined). So all "imagery" is **inline and dependency-free**:
- Page background: faint emerald radial glow + a dot-grid **SVG data URI**
  (`--bg-texture`), fixed attachment.
- Hero / showcase / free band: layered radial-gradient **mesh** (`--hero-mesh`)
  over `--hero-ink`, plus a subtle **SVG `feTurbulence` grain** overlay (`--noise`).

## Typography

System sans (`--font-sans`, Inter if present), bold tight headings, `.display`
for hero, `.eyebrow` kickers, `.lede` intros. Scale in `_typography.css`.

## Components

Elevated cards with hover lift; gradient `.btn-primary`, plus secondary / ghost /
danger / white / **outline-light** (for dark heroes) and sizes; sticky blurred
header with active links + theme toggle + notification pill; skill/status badges;
status-coloured flash; dashed empty states; avatars (image or gradient initials).
Landing/luxury pieces: **announcement bar**, **trust chips**, gradient **feature
tiles**, **showcase** split with a glass match-card mockup, **principle** cards,
dark **"$0 / forever" free band**, native **FAQ accordion** (`<details>`),
**CTA band**, multi-column **footer**. Widgets: **scroll-reveal**
(IntersectionObserver, safe-by-default — hidden only under `html.js`, with a
load-time fallback so content is never stranded) and **back-to-top**.

## CSS organization

```
static/css/
├── _variables.css   # tokens: brand ramp, gradients, mesh, textures, spacing,
│                     #         radius, shadow, type + dark-theme overrides
├── _base.css        # reset, body background, reveal animation (html.js gated)
├── _typography.css  # heading/display/eyebrow/meta scale
├── _layout.css      # announce bar, header, footer, hero, grids
├── _components.css  # cards, badges, avatars, flash, lists, chat, trust chips,
│                     #   principles, showcase, free band, FAQ, back-to-top …
├── _buttons.css     # button variants + sizes
└── _forms.css       # inputs, filter bar, form card, validation
```

Hand-written CSS only — no framework, no Node/npm build. The stylesheet is
**inlined** by `apps/common/templatetags/assets.py` (`{% inline_css %}`) so it
survives the dev path-rewriting proxy (see docs/DECISIONS.md D-B). JS is vanilla
and inline in `base.html` (theme toggle, reveal, back-to-top) and the chat poller.

## Product voice

Natural, human, specific — "Learn anything by teaching what you know.",
"Trade skills, not money.", "Free, and always will be." Never AI-powered.

## Page inventory (16)

| # | Page | Character |
|---|---|---|
| 1 | Landing | dark emerald mesh hero + trust chips + features + how-it-works showcase + principles + "$0 forever" band + FAQ + CTA |
| 2–4 | Register / Login / Password reset | centered auth cards |
| 5 | Member profile | avatar header, stat cards, reviews |
| 6 | Discovery | filter bar + match-card grid with teach/learn pills |
| 7 | Matching results | bidirectional skills as teach/learn pills |
| 8 | Skills management | two-list editor + add-skill card |
| 9 | Exchange requests | sent/received rows with status badges |
| 10 | Exchange workspace | details card, status badge, dual-confirm panel |
| 11 | Private chat | bubble thread, gradient "me" bubbles |
| 12 | Learning sessions | upcoming/past with badges, schedule card |
| 13 | Notifications | read/unread list, empty state |
| 14 | Reviews | review form card + aggregate on profile |
| 15 | Account settings | profile card, Google connect, deactivate |
| 16 | Admin/moderation | Django admin |

Every page belongs to the same system and works in both light and dark themes.
