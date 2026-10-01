# Adversarial Verification Checklist

Quality gate specifications, metric definitions, and automated verification procedures for `kage-bunshin-ui-ux`.

---

## 1. Quality Metric Targets

Every generated artifact (Figma frame, Google Stitch screen, or Code output) must pass these quantitative thresholds before final hand-off.

| Metric | Target Threshold | Formula / Measuring Instrument | Failure Action |
|---|---|---|---|
| **SSIM (Structural Similarity)** | **$\ge 0.95$** | Multi-channel SSIM via `scikit-image` (`visual_diff.py`) | Re-adjust bounding box dimensions, padding, or typography scales. |
| **MAE (Mean Absolute Error)** | **$\le 5.0$** (8-bit) | $\frac{1}{WH} \sum \|I_{orig} - I_{rend}\|$ via OpenCV/NumPy | Correct fill colors, gradients, stroke colors, or opacity. |
| **Layout Shift / Overlap** | **$0.0\%$ tolerance** | Bounding box collision detection among sibling layout nodes | Switch container `layoutMode` or adjust `layoutGrow` / `layoutAlign`. |
| **Text Truncation** | **$0$ unintended ellipses** | DOM `scrollWidth > clientWidth` check via Playwright | Adjust text wrapping (`layoutMode: AUTO`, `flex-wrap`, or min-width). |
| **WCAG 2.1 Contrast** | **AA Pass** ($\ge 4.5:1$ body, $\ge 3:1$ lg) | Relative Luminance Contrast Ratio | Adjust foreground/background semantic tokens. |
| **Token Binding** | **$100\%$** on supported targets | Figma `setBoundVariable` / CSS variable references | Bind unbound hex/pixel literals to semantic tokens. |
| **Interactive States** | **Pass** on all buttons/inputs | Playwright pseudo-class state assertions (`hover`, `focus`, `active`) | Add CSS hover/focus rules or Figma component variant states. |

---

## 2. Metric Calculation Details

### Structural Similarity Index (SSIM)
Measures structural, luminance, and contrast similarity across localized Gaussian windows:
$$\text{SSIM}(x, y) = \frac{(2\mu_x\mu_y + C_1)(2\sigma_{xy} + C_2)}{(\mu_x^2 + \mu_y^2 + C_1)(\sigma_x^2 + \sigma_y^2 + C_2)}$$
- Tested over luminance channels and weighted RGB.
- A score below $0.95$ indicates misaligned elements, missing icons, incorrect line heights, or shifted grids.

### Mean Absolute Error (MAE)
Computes average per-pixel absolute difference in 8-bit color space ($[0, 255]$):
$$\text{MAE} = \frac{1}{3 \cdot W \cdot H} \sum_{c \in \{R,G,B\}} \sum_{x=1}^W \sum_{y=1}^H |I_{\text{orig}}(x,y,c) - I_{\text{rend}}(x,y,c)|$$
- An MAE $> 5.0$ indicates widespread color mismatch, missing dark-mode palette inversion, or incorrect alpha blending.

---

## 3. Step-by-Step Verification Protocol

```
   ┌───────────────────────────────────────────────┐
   │ 1. Capture Rendered Output                    │
   │    • Code: Headless Chromium screenshot       │
   │    • Figma: Export Frame at 1x/2x PNG         │
   │    • Stitch: MCP Render Artifact Capture      │
   └──────────────────────┬────────────────────────┘
                          │
                          ▼
   ┌───────────────────────────────────────────────┐
   │ 2. Execute `scripts/visual_diff.py`           │
   │    • Compares original vs rendered preview    │
   │    • Generates `diff_heatmap.png`             │
   └──────────────────────┬────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
     [SSIM >= 0.95 &             [SSIM < 0.95 OR
      MAE <= 5.0]                 MAE > 5.0]
            │                           │
            ▼                           ▼
   ┌─────────────────┐         ┌───────────────────────────────┐
   │ 3. Run Inter-   │         │ 4. Iterative Patching         │
   │    action Check │         │    • Read heatmap clusters    │
   │    (`verify_    │         │    • Patch 1 token or margin  │
   │    interactions │         │    • Max 5 iterations ceiling │
   │    .mjs`)       │         └──────────────┬────────────────┘
   └────────┬────────┘                        │
            ▼                                 │ (Re-render & Re-verify)
   ┌─────────────────┐                        │
   │ 5. Pass Hand-off│ ◄──────────────────────┘
   └─────────────────┘
```

---

## 4. Interactive State Checklist (Playwright)

For code targets (`HTML/Tailwind`, `React`), execute `node scripts/verify_interactions.mjs --target <url_or_file>`:

- [ ] **Buttons (`<button>`, `[role="button"]`, `.btn`)**:
  - `hover`: Cursor changes to `pointer`; background or border shifts by measurable delta ($\Delta E > 2.0$).
  - `focus-visible`: Clear focus ring present (outline or box-shadow with contrast $\ge 3:1$).
  - `active`: Slight scale/transform or pressed background shade.
  - `disabled`: Cursor is `not-allowed`; opacity $\le 0.6$; pointer events disabled.
- [ ] **Inputs (`<input>`, `<textarea>`, `<select>`)**:
  - `focus`: Active border color shifts to `primary` token; outer glow/ring applied.
  - `placeholder`: Muted contrast token ($\ge 3:1$ against input surface).
- [ ] **Links (`<a>`)**:
  - `hover`: Underline appears or text color brightens/darkens.
- [ ] **Cards / Clickable Surfaces**:
  - `hover`: Elevation shadow increases or subtle border highlight occurs.

---

## 5. Convergence & Failure Escalation

1. **Max 5 Iterations Ceiling**: If SSIM remains $< 0.95$ or MAE $> 5.0$ after 5 atomic refinement loops:
   - Halt automatic re-rendering.
   - Output the `diff_heatmap.png` artifact to the user.
   - List the top 3 pixel error regions identified by contour analysis.
   - Provide explicit manual remediation advice.
2. **Never Reset From Scratch**: Apply only localized deltas (adjusting one margin, changing one font weight, fixing one border radius). Total re-generation risks introducing regressions to already converged areas.
