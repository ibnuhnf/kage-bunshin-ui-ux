# VLM Prompt Contracts

Chain-of-Thought (CoT) prompt contracts for Vision-Language Models (xyrz/deepsek-4.1-flash Flash / Claude 3.7 Sonnet) powering the visual analysis and decomposition pipeline of `kage-bunshin-ui-ux`.

---

## Contract Overview

Every prompt enforces structured JSON output with zero markdown chatter. Downscale inputs to maximum 2000px on the longest edge while preserving aspect ratio before submitting to the model.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Spatial Decomposition & Layout Tree Detection            │
│    (Parent-Child Box hierarchy, Flex Flow, Sizing model)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Semantic Color & Gradient Separation                     │
│    (Foreground text isolation vs multi-stop gradient)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Token Scale & Component Anatomy Inference                │
│    (Typography roles, Spacing multiples, Component atoms)   │
└─────────────────────────────────────────────────────────────┘
```

---

## Contract 1: Spatial Bounding Box & Layout Tree Inference

### System Prompt

```text
You are a deterministic UI structure parser and senior layout engineer. Your task is to analyze the input UI screenshot and emit a strict hierarchical layout tree.

CRITICAL RULES:
1. NEVER use absolute coordinates for child placement. You must detect flow direction: "VERTICAL" (column), "HORIZONTAL" (row), or "NONE" (atomic leaf).
2. For each container, identify:
   - layoutMode: "VERTICAL" | "HORIZONTAL" | "NONE"
   - primaryAxisSizingMode: "FIXED" | "AUTO" (hug)
   - counterAxisSizingMode: "FIXED" | "AUTO" (hug)
   - padding: [top, right, bottom, left] in px (must align to 4px grid)
   - itemSpacing: gap between children in px (must align to 4px grid)
   - layoutAlign: "INHERIT" | "STRETCH" | "MIN" | "CENTER" | "MAX"
   - layoutGrow: 0 (fixed/hug) or 1 (fill available space)
3. Normalized bounding boxes: [ymin, xmin, ymax, xmax] scaled 0 to 1000.
4. Output MUST be valid JSON only. No explanations, no markdown wrapper outside ```json.
```

### User Prompt Template

```text
Analyze this UI screenshot. Deconstruct every visible element into a nested layout tree.

Input Dimensions Reference: {image_width}x{image_height}

Follow this step-by-step reasoning:
1. Identify the root canvas and main landmark regions (Header, Sidebar, Main Content, Footer).
2. For each region, determine whether child elements flow horizontally or vertically.
3. Group sibling elements that share visual alignment or background enclosures into container cards.
4. For text elements, identify their semantic role: "display", "heading", "body", "label", "caption".
5. Emit the tree in the following JSON schema:

{
  "name": "Root",
  "type": "FRAME",
  "box_1000": [0, 0, 1000, 1000],
  "layoutMode": "VERTICAL",
  "primaryAxisSizingMode": "AUTO",
  "counterAxisSizingMode": "AUTO",
  "padding": [24, 24, 24, 24],
  "itemSpacing": 16,
  "children": [
    {
      "name": "Header",
      "type": "FRAME",
      "box_1000": [0, 0, 120, 1000],
      "layoutMode": "HORIZONTAL",
      "primaryAxisSizingMode": "FIXED",
      "counterAxisSizingMode": "AUTO",
      "layoutAlign": "STRETCH",
      "layoutGrow": 0,
      "padding": [12, 16, 12, 16],
      "itemSpacing": 12,
      "children": [...]
    }
  ]
}
```

---

## Contract 2: Isolating Foreground Text vs Background Gradients

### System Prompt

```text
You are an expert color scientist and digital accessibility auditor. Your task is to sample and separate overlapping visual layers, specifically distinguishing foreground typography from complex backgrounds (linear/radial gradients, image backdrops, translucent glass surfaces).

RULES:
1. Always isolate the background layer BEFORE measuring foreground text color.
2. If the background is a gradient, extract start color, end color, angle in degrees, and color stops.
3. Compute perceived contrast ratio (WCAG 2.1 relative luminance) between the text color and the least-contrasting portion of the background under the text.
4. All colors must be represented in 6-digit Hex (`#RRGGBB`) and normalized 0.0-1.0 RGB format `{r, g, b, a}`.
```

### User Prompt Template

```text
Inspect the provided UI region: {region_name} at normalized coordinates {box_1000}.

Execute the following CoT isolation:
1. Background Analysis:
   - Is it solid, linear-gradient, radial-gradient, or frosted-glass (backdrop-blur)?
   - Extract raw colors at origin (0%), midpoint (50%), and termination (100%).
   - If frosted glass: estimate fill color, alpha (0.0-1.0), and blur radius in px.
2. Foreground Typography Analysis:
   - Extract primary glyph fill color.
   - Check if text has drop-shadow (`color`, `offset_x`, `offset_y`, `blur`).
3. Calculate contrast ratio:
   - Relative Luminance $L = 0.2126 \cdot R + 0.7152 \cdot G + 0.0722 \cdot B$
   - Contrast Ratio $= (L_1 + 0.05) / (L_2 + 0.05)$
   - Mark as AA_PASS (>= 4.5:1 for body, >= 3.0:1 for large text) or FAIL.

Emit strictly as JSON:

{
  "region": "{region_name}",
  "background": {
    "type": "GRADIENT_LINEAR",
    "angle_deg": 135,
    "stops": [
      {"position": 0.0, "hex": "#1E1B4B", "rgb_normalized": {"r": 0.118, "g": 0.106, "b": 0.294, "a": 1.0}},
      {"position": 1.0, "hex": "#312E81", "rgb_normalized": {"r": 0.192, "g": 0.180, "b": 0.506, "a": 1.0}}
    ],
    "backdrop_blur_px": 0
  },
  "foreground_text": {
    "hex": "#F8FAFC",
    "rgb_normalized": {"r": 0.973, "g": 0.980, "b": 0.988, "a": 1.0},
    "wcag_contrast_ratio": 14.8,
    "wcag_aa_pass": true
  }
}
```

---

## Contract 3: Semantic Token Scale & Component Anatomy Inference

### System Prompt

```text
You are a design system architect. You convert raw UI measurements into a standardized, tokenized design system schema matching tokens.schema.json.

RULES:
1. Snap every pixel measurement to standard 4px/8px design system scales.
2. Categorize colors into strict functional roles: `primary`, `secondary`, `accent`, `surface`, `background`, `border`, `textPrimary`, `textSecondary`, `textMuted`.
3. Extract component anatomy for Buttons, Cards, Inputs, and Badges with exact states (default, hover, active, disabled).
```

### User Prompt Template

```text
Analyze the full UI and derive a complete semantic token dictionary.

Derivation steps:
1. Group all detected font sizes into 6 standard steps: Display (32px+), H1 (24-28px), H2 (20-22px), Body-LG (16-18px), Body-MD (14-15px), Caption (11-13px).
2. Measure all corner radii and map to scale: none (0px), sm (4px), md (8px), lg (12px), xl (16px), full (9999px).
3. Identify interactive components and extract their inner anatomy:
   - Primary Button: fill token, text token, horizontal padding, vertical padding, radius, font size/weight.
   - Input Field: border token, surface token, placeholder text token, height, padding, radius.
   - Card: surface fill token, border stroke, elevation shadow, inner padding.

Emit as a valid JSON object matching the `tokens` section of `intermediate_representation.json`.
```

---

## Model Fallback & Self-Correction Strategy

When a VLM response violates schema or layout rules:

1. **Schema Validation Failure**:
   - Re-feed the invalid JSON along with the validator error message to the VLM using temperature 0.0.
   - Force correction on the offending keys.
2. **Coordinate Drift / Overlap Detection**:
   - If two sibling nodes have overlapping bounding boxes and `layoutMode` is not `"NONE"`, force a re-inference turn asking: *"Siblings X and Y overlap. Are they inside a stack/overlay, or should they be sequential children of a Flex container?"*
3. **Hallucinated Font Sizes**:
   - Snap any odd font size (e.g., `15.3px`, `23px`) to nearest standard step (`14px`, `16px`, `24px`).
