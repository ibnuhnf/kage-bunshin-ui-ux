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

Choose one installation method. The skill itself is used through an AI coding
agent; the Python and Node scripts are optional local verification tools.

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

> `verify_interactions.mjs` is optional. Install it only when you have a
> rendered HTML/React page to inspect. The other two scripts need the Python
> packages shown above.

## Usage

### 1. Give the agent a source

Use either a local screenshot or a public webpage URL. State the desired
target and any constraints such as viewport, framework, route, or required
interactions:

```
Clone ./designs/dashboard.png into Figma with Auto Layout.
Replicate https://example.com/pricing as React + Tailwind.
Extract the design system from ./hero.png into a Stitch DESIGN.md.
```

For better results, provide a clean screenshot at the intended viewport. If a
URL is used, mention pages that require authentication separately; the agent
cannot infer private content without access.

### 2. Choose a target

- **Figma:** request an editable frame, Auto Layout, components, and bound
  design variables. The result is handed back as Figma node/page information.
- **Google Stitch:** request a Stitch design system and screen. The result
  includes `.stitch/DESIGN.md` plus the generated screen reference.
- **Code:** request React + Tailwind for an existing app, or single-file HTML
  when you need a portable prototype. Include the expected route and start
  command when working in a repository.

One source can be sent to multiple targets. Keep the same viewport and
content when comparing them.

### 3. Review and verify

The agent first creates a semantic layout representation, then generates the
chosen target. Render the result at the source viewport and compare it with
the original. Fix layout, spacing, typography, color, and responsive issues
before accepting the hand-off.

The repository does not include external Figma or Stitch credentials. Those
integrations must be available in the agent environment that runs the skill.

### Scripts directly

```bash
# Extract a palette, WCAG contrast ratios, and radii from a screenshot
python scripts/extract_tokens.py --input hero.png --output tokens.json

# Compare an original against a rendered clone
python scripts/visual_diff.py --original hero.png --rendered render.png --heatmap diff.png

# Verify interactive states on a rendered page
node scripts/verify_interactions.mjs --target http://localhost:3000
```

`verify_interactions.mjs` accepts a URL or local HTML file. Useful options:

```bash
node scripts/verify_interactions.mjs --target dist/index.html --viewport 1440x900 --json
node scripts/verify_interactions.mjs --target http://localhost:3000 --headless false
```

The token extractor writes JSON. The visual diff writes the heatmap path
passed with `--heatmap` and prints the quality result. Example:

```bash
python scripts/extract_tokens.py --input designs/dashboard.png --output artifacts/dashboard.tokens.json
python scripts/visual_diff.py \
  --original designs/dashboard.png \
  --rendered artifacts/dashboard.render.png \
  --heatmap artifacts/dashboard.diff.png
```

Run commands from the repository root, or use absolute paths. Use PNG files
with matching intended viewport dimensions whenever possible.

### Complete local workflow

```bash
# 1. Extract reusable visual tokens
python scripts/extract_tokens.py --input designs/dashboard.png --output artifacts/tokens.json

# 2. Ask the agent to create the IR and chosen target from the screenshot
# 3. Start the generated page, then verify interactions
node scripts/verify_interactions.mjs --target http://localhost:3000 --json

# 4. Capture a render at the same viewport and compare it to the source
python scripts/visual_diff.py --original designs/dashboard.png --rendered artifacts/render.png --heatmap artifacts/diff.png
```

The repository provides analysis and verification utilities, not a universal
screenshot-to-Figma/Stitch command. Target generation is performed by the
agent using `SKILL.md`, the intermediate representation template, and the
reference contracts.

## Input and output checklist

Before starting, prepare:

- Source screenshot(s), or a reachable URL.
- Target: Figma, Stitch, React/Tailwind, or HTML.
- Viewport size and responsive breakpoints, if known.
- Required interactions: navigation, forms, menus, hover, focus, and states.
- Existing project path and start command for code output.

Expect:

- `tokens.json` from token extraction.
- An intermediate representation based on `templates/intermediate_representation.json`.
- Target-specific files, nodes, or screen references.
- Visual metrics and a diff heatmap after rendering.

## Troubleshooting

### `ModuleNotFoundError` or missing Python package

Install the dependencies in the current Python environment:

```bash
python -m pip install pillow numpy scikit-learn opencv-python scikit-image
```

### `scikit-image is not installed`

Install `scikit-image`, then rerun `visual_diff.py`. SSIM cannot be computed
without it.

### Playwright browser is missing

```bash
npx playwright install chromium
```

### Visual score is below the gate

Check viewport dimensions first. Then inspect the heatmap for the largest
errors, fix one class of issue at a time, rerender, and rerun the diff. Do not
compare a cropped source with a full-page render.

### No Figma or Stitch output

Confirm that the target integration is installed and authenticated in the
agent environment. Local token extraction alone does not create external
Figma or Stitch artifacts.

## Development and tests

Run the repository checks before publishing changes:

```bash
python -m pytest
python -m py_compile scripts/extract_tokens.py scripts/visual_diff.py
npm install
npm run verify:sample
```

`npm run verify:sample` runs the repeatable local interaction scenario in
`tests/fixtures/interaction-smoke.html` and checks hover, focus, and text
overflow. It is a smoke test for the verifier, not a claim that an arbitrary
clone matches a source screenshot.

The full screenshot-to-target E2E path still requires a real source screenshot,
generated target output, and authenticated Figma/Stitch integrations. Run that
path manually when those inputs are available.

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
├── tests/
│   ├── fixtures/interaction-smoke.html
│   ├── test_extract_tokens.py
│   └── test_visual_diff.py
└── templates/
    ├── intermediate_representation.json
    └── tokens.schema.json
```

## Research basis

- **FIGMA2CODE** (ICLR 2026) — the failure modes of direct coordinate mapping from multimodal design sources.
- **LaTCoder** (KDD 2025) — Layout-as-Thought decomposition and a combined MAE/CLIP verify score.
- **IW-Bench** (ACL 2025) — multimodal image-to-web benchmarks and the value of multi-pass reflection.

The implementation references are maintained in [`references/`](references/).

## License

MIT
