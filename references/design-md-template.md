# Google Stitch `DESIGN.md` Template

The specification for the design-system document that Target B writes to `.stitch/DESIGN.md`, then hands to Google Stitch (`mcp_stitch:create_screen` / `stitch::generate-design`). Stitch reads this as the generation contract, so every section below is a section an agent generating screens will actually consume — prose that Stitch cannot act on is worse than absent.

Fill every section from the Design IR. Where the IR cannot supply a value, state the assumption explicitly rather than leaving a blank.

---

## Template

````markdown
# Design System: <Project Name>

## Overview & Atmosphere

- **Mood**: <e.g. "calm, technical, high-contrast dark">
- **Target audience**: <who uses this>
- **Design language**: <e.g. "Bento Grid Minimalist", "Glassmorphic Modern Tech">
- **Visual metaphor**: <one sentence on the feeling the screen must evoke>
- **Density**: <airy | balanced | compact>

## Semantic Color Roles

Colors are referenced by role, never by hex, in all downstream prompts.

| Role | Hex | Usage |
|---|---|---|
| `primary` | `#5b8cff` | Brand accent — primary CTA, active states, focus rings |
| `secondary` | `#7c5cff` | Supporting accent — badges, secondary highlights |
| `accent` | `#37d6c0` | Emphasis only — sparing, never a surface |
| `background` | `#0b0d12` | Page canvas |
| `surface` | `#151922` | Cards, nav bar, containers |
| `surface-subtle` | `#1e2430` | Hover states, inset panels, code blocks |
| `border` | `#2a3140` | Separators, strokes, dividers |
| `text-primary` | `#f4f7fb` | Headings, primary body, labels |
| `text-secondary` | `#9aa4b2` | Captions, meta, helper text |
| `success` | `#3ecf8e` | Positive status |
| `warning` | `#f5b544` | Caution status |
| `danger` | `#f0564a` | Errors, destructive actions |

**Contrast rules** (WCAG 2.1):

- Body text must reach >= 4.5:1 against its background; large text >= 3:1.
- `text-secondary` on `background` is for large or non-essential text only unless it clears 4.5:1.
- Never place `text-primary` on `primary` — use `background` as the text color on filled brand surfaces.

## Typography Hierarchy

- **Display font**: <family> — weights <e.g. 600-800>
- **Body font**: <family> — weights <e.g. 400-500>
- **Mono font**: <family> (code, tokens, IDs)

| Step | Size | Line height | Weight | Letter spacing | Use |
|---|---|---|---|---|---|
| Display | 56px | 64px | 700 | -1.2px | Hero headline |
| H1 | 40px | 48px | 700 | -0.8px | Page title |
| H2 | 32px | 40px | 600 | -0.4px | Section heading |
| H3 | 24px | 32px | 600 | -0.2px | Card title |
| Body L | 18px | 28px | 400 | 0 | Lead paragraph |
| Body M | 16px | 24px | 400 | 0 | Default body |
| Body S | 14px | 20px | 400 | 0 | Secondary body |
| Caption | 12px | 16px | 500 | 0.4px | Labels, meta (often uppercase) |

Rules:

- One Display or H1 per screen.
- Never more than 3 size steps between adjacent headings.
- Line height is expressed in px values that round to the 4px grid.

## Spacing Scale

Baseline grid: **4px**. All spacing is a multiple of 4.

| Token | px | Typical use |
|---|---|---|
| `xs` | 4 | Icon gaps, tight label spacing |
| `sm` | 8 | Inline gaps, compact padding |
| `md` | 16 | Default padding, stack gaps |
| `lg` | 24 | Section inner padding, card gaps |
| `xl` | 32 | Container padding |
| `2xl` | 48 | Between blocks |
| `3xl` | 64 | Section vertical padding |
| `4xl` | 96 | Hero / page-level breathing room |

Radii: `none` 0 · `sm` 6 · `md` 10 · `lg` 16 · `full` 9999.

Elevation:

- `shadow-md`: `0 8px 24px -8px #00000033` — cards.
- `shadow-lg`: `0 24px 64px -16px #00000055` — modals, popovers.

## Component Anatomy

### Button

- **Structure**: horizontal auto-layout, centered, gap `sm`.
- **Sizes**: `sm` (min-height 36px, padding 8/16, Body M) · `lg` (min-height 48px, padding 16/24, Body L).
- **Tones**: `primary` (fill `primary`, text `background`) · `ghost` (transparent, text `text-primary`, border `border`).
- **Radius**: `md`.
- **States**: default · hover (`brightness 1.08`) · active (`scale 0.98`) · focus (2px `primary` ring, 2px offset) · disabled (opacity 0.5).

### Input

- **Structure**: vertical, label above field, gap `sm`.
- **Field**: fill `surface`, border `border`, radius `md`, padding `sm`/`md`, text Body M, placeholder `text-secondary`.
- **States**: default · hover (`surface-subtle`) · focus (border `primary` + ring) · error (border `danger`) · disabled (opacity 0.5).

### Card

- **Structure**: vertical, gap `md`, padding `lg`.
- **Surface**: fill `surface`, border `border`, radius `lg`, `shadow-md`.
- **Anatomy**: optional icon (24px) → title (H3) → body (Body M, `text-secondary`) → optional action row.

### Navigation Bar

- **Structure**: horizontal, `space-between`, align center, padding `md`/`xl`.
- **Surface**: fill `surface`, border-bottom `border`.
- **Regions**: brand (left) · links (center or right, gap `lg`, Body M `text-secondary`) · CTA (right).
- **Height**: 64px.

### Badge

- **Structure**: horizontal, centered, gap `xs`, padding `xs`/`sm`, radius `full`.
- **Type**: Caption, uppercase.
- **Tones**: `primary` (fill `primary` @ 15%, text `primary`) · `success` · `warning` · `danger` · `neutral` (fill `surface-subtle`, text `text-secondary`).

## Layout

- **Max content width**: 1200px, centered, side padding `xl`.
- **Grid**: 12-column, 24px gutter.
- **Breakpoints**: mobile `<640` · tablet `640-1024` · desktop `>1024`.
- **Section rhythm**: `3xl`–`4xl` vertical padding between major sections.

## Do's and Don'ts

**Do**

- Reference colors by role (`primary`, `surface`), never by hex, in every screen prompt.
- Keep to the spacing scale — every gap and padding a multiple of 4.
- Give each screen exactly one primary action.
- Use `surface` for cards and `background` for the canvas; keep the two distinct.

**Don't**

- Don't introduce a new color outside the Semantic Color Roles table.
- Don't use more than two font families per screen.
- Don't stack two primary CTAs in one view.
- Don't use `accent` as a surface fill — it is emphasis only.
- Don't hardcode pixel positions; express layout as flow (stack / row / grid).
- Don't mix radii — pick from `sm`/`md`/`lg`/`full` only.
````

---

## Usage notes

**Where it lives.** Target B writes the filled document to `.stitch/DESIGN.md` in the project root. Stitch's MCP reads that path; a `DESIGN.md` elsewhere is not picked up.

**Filling from the IR.** The mapping is direct:

| `DESIGN.md` section | IR source |
|---|---|
| Semantic Color Roles | `tokens.color.*` (hex + the `role` note) |
| Typography Hierarchy | `tokens.typography.fontFamilies` + `tokens.typography.scale` |
| Spacing Scale | `tokens.spacing.scale` + `tokens.radius` + `tokens.shadow` |
| Component Anatomy | `components.*.anatomy` |
| Layout | derived from the tree's root padding and the widest container |
| Do's and Don'ts | enforced from the IR — list what the IR deliberately did not do |

**Why roles, not hexes.** Stitch's generation is prompt-driven. A prompt that says "set the card background to `surface`" keeps the screen inside the token system; one that says `#151922` produces a screen that cannot be re-themed when the tokens change. The role table is the contract that keeps the two in sync.

**When the IR lacks a value.** State the assumption inline (`## Dependencies: Inter assumed available via Google Fonts`) rather than inventing a token. An invented token silently diverges from the Figma and code targets.

**Handoff.** After writing `DESIGN.md`, call `mcp_stitch:create_screen`. Include in the request: the project name, the screen's purpose, the role names it should use, and the layout shape from the IR. Return the resulting screen URL in the Phase-4 hand-off.
