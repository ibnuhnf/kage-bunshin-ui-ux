---
name: kage-bunshin-ui-ux
description: Replicate a UI screenshot or webpage URL into three targets — an editable Figma frame (Auto Layout + Variables), a Google Stitch DESIGN.md plus MCP screen, or responsive React/Tailwind or single-file HTML — then converge it with an adversarial visual-diff loop (SSIM >= 0.95, MAE <= 5%). Use when the user asks to clone, replicate, rebuild, or convert a UI screenshot/URL into Figma, Stitch, or code.
allowed-tools:
  - use_figma
  - figma_console_mcp:*
  - mcp_stitch:*
  - get_screenshot
  - run_command
triggers:
  - clone this
  - replicate
  - rebuild this page as
  - make a DESIGN.md from
  - convert this screenshot
  - convert this URL
  - kage bunshin
  - shadow clone
  - clone UI
  - clone design
---

# Kage Bunshin UI/UX

High-fidelity UI cloning across three ecosystems from one source of truth. Named after the Shadow Clone technique: analyze the original once, then produce faithful copies that stay editable.

## When to use

- "Clone this screenshot into Figma", "rebuild this page as React/Tailwind", "make a DESIGN.md from this URL".
- Any request to convert a visual (screenshot, URL, Figma frame) into a design artifact or code.
- Not for greenfield design (no source to replicate) and not for editing an existing design in place.

## The one rule

**Never map pixels directly.** Absolute coordinates destroy responsiveness and re-editability. Every target is reconstructed from a semantic layout tree — containers, flow direction, tokens — never from raw positions. See `references/figma-auto-layout-rules.md`.

## Pipeline

### Phase 1 — Multi-Modal Analysis & Design IR Synthesis

1. Preprocess: accept screenshot or URL. Downscale to max 2000px preserving aspect ratio. For URLs, capture a reference-viewport screenshot first.
2. Spatial decomposition with a Vision LLM: detect containers, parent-child hierarchy, and flow orientation (row vs column).
3. Extract semantic tokens: color roles by function (`primary`, `surface`, `background`, `textPrimary`, ...), typography scale (`heading-lg`, `body-md`, `caption`), spacing and radii.
4. Compile everything into `intermediate_representation.json` conforming to `templates/intermediate_representation.json` and `templates/tokens.schema.json`.

Prompt contracts for step 2-3: `references/vlm-prompt-contracts.md`.

### Phase 2 — Target Transpilation

Emit **one** target per run unless the user asks for several.

**Target A — Figma** (via `use_figma` / `figma_console_mcp`)
1. Create `VariableCollection`s for color and spacing first.
2. Build `FRAME` nodes and set `layoutMode` (`VERTICAL` / `HORIZONTAL`).
3. Normalize RGB to `0.0-1.0`, append children **before** setting `layoutAlign` / `layoutGrow`, bind paints to variables instead of raw solids.
4. Return every created node ID.

**Target B — Google Stitch**
1. Compile the IR into `.stitch/DESIGN.md` using `references/design-md-template.md`.
2. Enhance the request into a professional UI/UX prompt.
3. Call `mcp_stitch:create_screen` (`stitch::generate-design`).
4. Return the screen URL.

**Target C — Markdown contract**
1. Compile the completed IR into an AI-readable implementation contract:
   `python scripts/ir_to_markdown.py --input <ir.json> --output <design.md>`.
2. Treat the Markdown file as the exact hand-off specification for tokens, layout, content, components, states, and verification gates.

**Target D — Code**
1. Semantic HTML (`<header>`, `<main>`, `<article>`, `<button>`) — no absolute positioning.
2. Responsive Tailwind utilities (`flex`, `grid`, `gap-4`, `rounded-xl`) or a single self-contained HTML file.
3. Return file paths.

### Phase 3 — Adversarial Visual Verification Loop

1. Render the output: Playwright/Chromium for code, Figma preview export for frames, Stitch render for screens.
2. Compare against the original: `python scripts/visual_diff.py --original <input> --rendered <output>`.
3. If SSIM < 0.95 or MAE > 5.0, apply **atomic** corrections (one token, one margin, one spacing value) and re-render. Never reset the whole page.
4. Cap at 5 iterations; report residual deviation honestly if it does not converge.

Gates and metric definitions: `references/verification-checklist.md`.

### Phase 4 — Final Hand-off

Report: Figma node IDs, Stitch screen URL, code file paths, and the final SSIM/MAE numbers with the iteration count.

## Quality gates

| Gate | Target |
|---|---|
| SSIM | >= 0.95 |
| MAE | <= 5.0 (8-bit) |
| Layout shift | zero overlap, zero unintended truncation |
| Token binding | every visual property bound to a variable where the target supports it |
| Responsiveness | no overlap when text or container size changes |

## References

- `references/figma-auto-layout-rules.md` — non-negotiable Figma Plugin API contracts.
- `references/design-md-template.md` — Google Stitch `DESIGN.md` structure.
- `references/vlm-prompt-contracts.md` — CoT prompts for spatial and token extraction.
- `references/verification-checklist.md` — adversarial quality gates.
- `templates/intermediate_representation.json` — IR example.
- `templates/tokens.schema.json` — design token schema.
- `scripts/extract_tokens.py` — color palette, WCAG contrast, radii extraction.
- `scripts/visual_diff.py` — MAE / SSIM plus diff heatmap.
- `scripts/verify_interactions.mjs` — Playwright hover/focus/active verification.
- `scripts/ir_to_markdown.py` — deterministic IR to AI-readable Markdown contract.

## Failure modes to avoid

- Emitting `position: absolute` everywhere because the screenshot is a static image.
- Setting `layoutAlign` before `appendChild` (silently ignored by the Figma API).
- Using 8-bit RGB values directly in Figma (`0-255` instead of `0.0-1.0`).
- Reporting a clone as complete without running the visual diff.
- Looping forever: 5 iterations is the ceiling, then report.
