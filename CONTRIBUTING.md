# Contributing

Thanks for helping improve `kage-bunshin-ui-ux`.

## Ground rules

1. **No pixel mapping.** Any contribution that introduces absolute-coordinate reconstruction of a layout is rejected. Everything is rebuilt from the semantic IR.
2. **No placeholders.** Reference documents and scripts ship complete. `TODO`, `...`, and truncated bodies are not accepted.
3. **One concern per PR.** A PR changes one of: a reference doc, a script, a template, or the skill manifest.
4. **Every metric claim must be measurable.** If you add a quality gate, define how it is computed and what value counts as a pass.

## What to contribute

| Area | Examples |
|---|---|
| `references/` | Tighten a Figma API contract, add a Stitch template section, sharpen a VLM prompt contract |
| `scripts/` | Improve palette extraction, add a new diff metric, broaden interaction checks |
| `templates/` | Extend the IR schema, add a target-specific token mapping |
| `SKILL.md` | Clarify a phase, add a failure mode, correct the playbook |

## Development setup

```bash
git clone https://github.com/ibnuhnf/kage-bunshin-ui-ux.git
cd kage-bunshin-ui-ux
pip install pillow numpy scikit-learn opencv-python scikit-image pytest
npm install
npx playwright install chromium
```

## Before you open a PR

- [ ] Scripts run end to end on a real screenshot. Include the command you ran and its output.
- [ ] `python -m pytest tests/` passes.
- [ ] New reference content cites a source or a concrete API behavior — not an opinion.
- [ ] `SKILL.md` frontmatter still validates: `name`, `description`, `allowed-tools`.
- [ ] No secrets, no personal paths, no vendor lock-in added to a script.

## Style

- **Markdown:** ATX headings, fenced code blocks with a language tag, tables for enumerations of three or more.
- **Python:** standard library first, `argparse` CLIs, type hints on public functions, no print-debugging left behind.
- **JavaScript:** ESM, explicit `--flag` parsing, fail loudly on a missing input.
- **Naming:** files `kebab-case.md`, scripts `snake_case.py` and `camelCase.mjs`.

## Commit messages

Conventional Commits:

```
feat(scripts): add CIEDE2000 to visual_diff
fix(references): correct layoutAlign ordering rule
docs(skill): clarify the 5-iteration ceiling
```

## Reporting a bad clone

Open an issue with:

1. The source screenshot or URL.
2. The target used (Figma / Stitch / Code).
3. The reported SSIM and MAE.
4. The diff heatmap if you have it.

A clone that reports a passing metric while visibly diverging is a bug — say so explicitly.

## License

By contributing you agree your work is released under the MIT License.
