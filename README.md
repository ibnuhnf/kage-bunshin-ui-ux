# kage-bunshin-ui-ux

> Shadow Clone for UI/UX — analyze a design once, produce faithful editable copies everywhere.

An open-standard **Agent Skill** that takes a UI screenshot or a webpage URL and produces any of three targets:

| Target | Output |
|---|---|
| **Figma** | Editable frame with Auto Layout, Variable-bound paints, and a Component Set |
| **Google Stitch** | `.stitch/DESIGN.md` design system plus an MCP-generated screen |
| **Code** | Responsive React + Tailwind, or a single self-contained HTML file |

Every target is then pushed through an **adversarial visual verification loop** — render, compare (SSIM / MAE), correct atomically, repeat — until it converges.

## Why it exists

Most screenshot-to-code tools do direct pixel mapping: they read coordinates and emit `position: absolute` everywhere. The result looks right in a screenshot and falls apart the moment anyone edits it. This skill reconstructs a **semantic layout tree** first and transpiles from that, so the clone stays responsive and re-editable.

## Pipeline

```
screenshot / URL
      │
      ▼
[1] Multi-modal analysis  ──►  spatial hierarchy, color roles, type scale
      │
      ▼
[2] Design IR             ──►  intermediate_representation.json (agnostic)
      │
      ├──────────────┬──────────────┐
      ▼              ▼              ▼
   Figma         Stitch          Code
 (figma-use)   (.stitch/DESIGN.md) (React/Tailwind | HTML)
      │              │              │
      └──────────────┴──────────────┘
                     │
                     ▼
[3] Adversarial verification  ──►  SSIM >= 0.95, MAE <= 5.0
                     │
                     ▼
[4] Hand-off  ──►  node IDs, screen URL, file paths, metrics
```

## Install

### As an Agent Skill

Copy the repository into your skills directory, or reference it from your agent's skill manifest:

```
~/.claude/skills/kage-bunshin-ui-ux/
~/.agents/skills/kage-bunshin-ui-ux/
```

The entry point is `SKILL.md`.

### Script dependencies

```bash
pip install pillow numpy scikit-learn opencv-python scikit-image
npm install   # for scripts/verify_interactions.mjs (Playwright)
npx playwright install chromium
```

## Usage

Point your agent at a screenshot or URL and name the target:

```
Clone ./designs/dashboard.png into Figma with Auto Layout.
Replicate https://example.com/pricing as React + Tailwind.
Extract the design system from ./hero.png into a Stitch DESIGN.md.
```

### Scripts directly

```bash
# Extract a palette, WCAG contrast ratios, and radii from a screenshot
python scripts/extract_tokens.py --input hero.png --output tokens.json

# Compare an original against a rendered clone
python scripts/visual_diff.py --original hero.png --rendered render.png --heatmap diff.png

# Verify interactive states on a rendered page
node scripts/verify_interactions.mjs --url http://localhost:3000
```

## Quality gates

| Metric | Target | Meaning |
|---|---|---|
| SSIM | >= 0.95 | Structural similarity |
| MAE | <= 5.0 | Mean absolute error, 8-bit |
| Layout shift | 0 | No overlap, no unintended truncation |
| Token binding | 100% | Every bindable property bound to a variable |
| Responsiveness | pass | No overlap when content size changes |

## Repository layout

```
kage-bunshin-ui-ux/
├── SKILL.md                              # Agent skill manifest and playbook
├── README.md
├── CONTRIBUTING.md
├── .agents/plugins/plugin.json           # Marketplace manifest
├── references/
│   ├── figma-auto-layout-rules.md
│   ├── design-md-template.md
│   ├── vlm-prompt-contracts.md
│   └── verification-checklist.md
├── scripts/
│   ├── extract_tokens.py
│   ├── visual_diff.py
│   └── verify_interactions.mjs
└── templates/
    ├── intermediate_representation.json
    └── tokens.schema.json
```

## Research basis

- **FIGMA2CODE** (ICLR 2026) — the failure modes of direct coordinate mapping from multimodal design sources.
- **LaTCoder** (KDD 2025) — Layout-as-Thought decomposition and a combined MAE/CLIP verify score.
- **IW-Bench** (ACL 2025) — multimodal image-to-web benchmarks and the value of multi-pass reflection.

See [`referensi.md`](../referensi.md) for the full reference list of related repositories and papers.

## License

MIT
