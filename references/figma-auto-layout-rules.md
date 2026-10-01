# Figma Auto Layout Rules

Non-negotiable contracts for transpiling a Design IR into Figma via the Plugin API (`use_figma` / `figma_console_mcp`). These are load-bearing: Figma silently ignores several properties when they are set in the wrong order, and a broken order produces a frame that *looks* right once and collapses the moment anything is resized.

Source of truth: [Figma Plugin API — Auto Layout](https://www.figma.com/plugin-docs/api/properties/nodes-autolayoutmixin/) and [Working with Variables](https://www.figma.com/plugin-docs/working-with-variables/).

## 1. Color normalization

The Figma API takes RGB channels in the **0.0–1.0** range, not 0–255.

```js
// IR stores rgb { r, g, b } already normalized — use it directly.
const { r, g, b } = token.rgb;
const paint = { type: 'SOLID', color: { r, g, b } };

// From a hex string, divide by 255 — never pass 0-255 straight through.
const hexToFigma = (hex) => {
  const n = parseInt(hex.replace('#', ''), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
};
```

Alpha is a separate `opacity` field on the paint, not a 4th channel:

```js
const paint = { type: 'SOLID', color: { r, g, b }, opacity: token.alpha ?? 1 };
```

## 2. Auto Layout order

Set `layoutMode` and every layout property **before** appending children. When a frame auto-layouts, Figma re-lays-out its children on the next tick; properties set after a child exists can be clobbered.

Correct order:

```js
const frame = figma.createFrame();
frame.name = 'hero';

// 1. Mode first.
frame.layoutMode = 'VERTICAL';            // 'HORIZONTAL' | 'VERTICAL' | 'NONE'

// 2. Sizing rules.
frame.primaryAxisSizingMode = 'AUTO';     // 'AUTO' = hug on main axis
frame.counterAxisSizingMode = 'AUTO';     // 'FIXED' = fill on cross axis

// 3. Padding + spacing (only valid once layoutMode is set).
frame.paddingTop = 64;
frame.paddingBottom = 64;
frame.paddingLeft = 32;
frame.paddingRight = 32;
frame.itemSpacing = 24;
frame.primaryAxisAlignItems = 'CENTER';   // MIN | CENTER | MAX | SPACE_BETWEEN
frame.counterAxisAlignItems = 'CENTER';

// 4. Children come last.
parent.appendChild(frame);
```

Property mapping from IR:

| IR | Figma |
|---|---|
| `direction: "column"` | `layoutMode = 'VERTICAL'` |
| `direction: "horizontal"` | `layoutMode = 'HORIZONTAL'` |
| `gap` | `itemSpacing` |
| `padding.top/right/bottom/left` | `paddingTop/Right/Bottom/Left` |
| `justify: "center"` | `primaryAxisAlignItems = 'CENTER'` |
| `justify: "space-between"` | `primaryAxisAlignItems = 'SPACE_BETWEEN'` |
| `align: "center"` | `counterAxisAlignItems = 'CENTER'` |
| `sizing.width: "hug"` | `primaryAxisSizingMode` (on a HORIZONTAL frame) `= 'AUTO'` |
| `sizing.width: "fill"` | child `layoutGrow = 1` + parent `counterAxisSizingMode` handling |
| `wrap: true` | `layoutWrap = 'WRAP'` |

`primaryAxisSizingMode` / `counterAxisSizingMode` are **axis-relative**, and the axes swap with `layoutMode`. On a HORIZONTAL frame the primary axis is width; on a VERTICAL frame it is height. Resolve the IR's `sizing.width` / `sizing.height` against the frame's actual direction before assigning — never map width→primary blindly.

## 3. Constraint sequence

`layoutAlign` and `layoutGrow` only have meaning relative to a parent, so they are **ignored unless set after `appendChild`**:

```js
parent.appendChild(child);

// Then, and only then:
child.layoutAlign = 'STRETCH';   // 'STRETCH' | 'INHERIT'  → cross-axis fill
child.layoutGrow = 1;            // main-axis fill (1 = grow, 0 = hug)
child.layoutPositioning = 'AUTO'; // 'AUTO' participates in layout; 'ABSOLUTE' escapes it
```

Rules:

- `STRETCH` fills the **cross** axis; `layoutGrow = 1` fills the **main** axis. To make a child fill both (e.g. a card in a wrapping grid), apply both.
- Setting these before `appendChild` fails silently — no error, just a component that does not stretch.
- `layoutGrow` is meaningful only when the parent is auto-layout. On a non-auto-layout parent it does nothing.

## 4. Async page context

Working across pages requires awaiting the page switch. Assigning `figma.currentPage` synchronously races with plugin reloads and throws on locked pages.

```js
const page = figma.root.children.find(p => p.name === 'Screens');
await figma.setCurrentPageAsync(page);   // always await
const frame = figma.createFrame();       // now created on the right page
```

For read-only node lookup the sync `figma.getNodeByIdAsync(id)` is preferred over the deprecated `figma.getNodeById`:

```js
const node = await figma.getNodeByIdAsync(nodeId);
if (!node) throw new Error(`node ${nodeId} not found`);
```

Stitch every async call into the same `await` chain — a floating promise that mutates a node after the plugin returns leaves the file half-written.

## 5. Variable binding

Bind paints to variables wherever the IR names a token, so a later theme change propagates instead of being frozen into a static solid.

```js
// One-time setup per file.
const collection = figma.variables.createVariableCollection('kage-tokens');
const modeId = collection.modes[0].modeId;

const makeColorVar = (name, rgb) => {
  const v = figma.variables.createVariable(name, collection, 'COLOR');
  v.setValueForMode(modeId, rgb);   // rgb = { r, g, b } normalized
  return v;
};

const primary = makeColorVar('color/primary', { r: 0.357, g: 0.549, b: 1.0 });

// Bind the fill (not a static SOLID).
node.fills = [figma.variables.setBoundVariableForPaint(
  { type: 'SOLID', color: { r: 0, g: 0, b: 0 } },
  'color',
  primary
)];
```

Notes:

- Resolve the variable by name with `figma.variables.getLocalVariables('COLOR')` and match on `variable.name` — there is no global name lookup.
- Spacing tokens become `FLOAT` variables; bind via `node.setBoundVariable('itemSpacing' | 'paddingLeft' | ..., floatVar)`.
- Fonts used by any text node must be loaded before the node is created: `await figma.loadFontAsync({ family, style })`. A text node with an unloaded font throws on any write to `characters`.

## 6. Text nodes

```js
await figma.loadFontAsync({ family: 'Inter', style: 'Semi Bold' });
const t = figma.createText();
t.fontName = { family: 'Inter', style: 'Semi Bold' };
t.characters = irNode.text;
t.fontSize = 24;
t.lineHeight = { value: 32, unit: 'PIXELS' };  // match IR lineHeight in px, not percent
t.letterSpacing = { value: -0.2, unit: 'PIXELS' };
t.textAutoResize = 'HEIGHT';                    // grow downward; never 'NONE' unless width is fixed
```

`textAutoResize = 'NONE'` requires `resize()` on both axes and reintroduces the fixed-size fragility this whole pipeline exists to avoid. Use `'HEIGHT'` for flowing text, `'WIDTH_AND_HEIGHT'` for single-line labels.

## 7. Components

The IR `components` map becomes Figma Component Sets.

1. Build one `ComponentNode` per variant with `figma.createComponentFromNode(frame)`.
2. `figma.combineAsVariants(nodes, parent)` to form the set.
3. Name each variant node with the IR variant keys as `key=value` pairs, comma-separated: `size=lg, tone=primary`.
4. Instances reference the set: `const inst = componentSet.defaultVariant.createInstance()`.

Variant property names must match the IR keys exactly or `combineAsVariants` will not group them.

## 8. Completion invariant

Before reporting the frame as done, every one of these must hold:

- [ ] Every IR color token is bound to a variable (no raw SOLID paints).
- [ ] Every container has `layoutMode` set and its children appended after that.
- [ ] Every stretch/grow constraint is applied after `appendChild`.
- [ ] No `textAutoResize = 'NONE'` unless the IR explicitly marked the node `sizing.width: "fixed"`.
- [ ] Every created node ID is collected and returned in the hand-off.
- [ ] Resizing the root frame ±30% produces no overlap and no unintended truncation.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Frame does not stretch after resize | `layoutGrow`/`layoutAlign` set before `appendChild` | Move the assignment after the append |
| Padding has no effect | `paddingTop` set while `layoutMode = 'NONE'` | Set `layoutMode` first |
| Colors are near-black | 8-bit values passed as 0–255 | Divide by 255, or use IR `rgb` |
| Text write throws | Font not loaded | `await figma.loadFontAsync(...)` before `characters =` |
| Node created on wrong page | `figma.currentPage =` used synchronously | `await figma.setCurrentPageAsync(page)` |
| Variants refuse to combine | Variant node names do not match IR keys | Name nodes `key=value, key2=value2` |
