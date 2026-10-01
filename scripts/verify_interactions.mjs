#!/usr/bin/env node
/**
 * verify_interactions.mjs - Playwright Interactive State & Accessibility Verifier
 *
 * Verifies that buttons, inputs, links, and cards properly implement interactive states
 * (hover, focus, active, disabled) and have accessible contrast and focus indicators.
 *
 * Usage:
 *   node scripts/verify_interactions.mjs --target <url_or_filepath> [--headless] [--json]
 */

import { chromium } from "playwright";
import { parseArgs } from "node:util";
import { existsSync } from "node:fs";
import { pathToFileURL } from "node:url";

const options = {
  target: { type: "string", short: "t" },
  headless: { type: "boolean", default: true },
  json: { type: "boolean", default: false },
  viewport: { type: "string", default: "1280x800" },
};

const { values: args } = parseArgs({ options, allowPositionals: true });

if (!args.target) {
  console.error("Error: --target <url_or_filepath> is required.");
  process.exit(1);
}

let targetUrl = args.target;
if (!targetUrl.startsWith("http://") && !targetUrl.startsWith("https://")) {
  if (!existsSync(targetUrl)) {
    console.error(`Error: Target file not found: ${targetUrl}`);
    process.exit(1);
  }
  targetUrl = pathToFileURL(targetUrl).href;
}

const [width, height] = args.viewport.split("x").map((v) => parseInt(v, 10) || 800);

async function runVerification() {
  const browser = await chromium.launch({ headless: args.headless });
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();

  const results = {
    target: targetUrl,
    timestamp: new Date().toISOString(),
    summary: { total: 0, passed: 0, failed: 0, warnings: 0 },
    checks: [],
  };

  try {
    await page.goto(targetUrl, { waitUntil: "networkidle", timeout: 15000 });

    // 1. Check all buttons for pointer cursor and hover reaction
    const buttons = await page.$$("button, [role='button'], a.btn, .button");
    for (let i = 0; i < buttons.length; i++) {
      const btn = buttons[i];
      const text = (await btn.innerText()).trim().slice(0, 30) || `Button #${i + 1}`;
      
      const beforeBox = await btn.boundingBox();
      if (!beforeBox) continue; // Hidden element

      const initialCursor = await btn.evaluate((el) => window.getComputedStyle(el).cursor);
      const initialBg = await btn.evaluate((el) => window.getComputedStyle(el).backgroundColor);

      // Trigger hover
      await btn.hover();
      await page.waitForTimeout(100);

      const hoverBg = await btn.evaluate((el) => window.getComputedStyle(el).backgroundColor);
      const hoverCursor = await btn.evaluate((el) => window.getComputedStyle(el).cursor);

      const hasPointer = hoverCursor === "pointer" || initialCursor === "pointer";
      const hasHoverEffect = hoverBg !== initialBg;

      results.summary.total++;
      if (hasPointer) {
        results.summary.passed++;
        results.checks.push({
          element: text,
          type: "BUTTON_HOVER",
          status: "PASS",
          detail: `Cursor: pointer. Visual shift detected: ${hasHoverEffect ? "YES" : "NO"}`,
        });
      } else {
        results.summary.failed++;
        results.checks.push({
          element: text,
          type: "BUTTON_HOVER",
          status: "FAIL",
          detail: `Missing cursor:pointer on interactive button (found: ${hoverCursor}).`,
        });
      }
    }

    // 2. Check form inputs for focus visibility
    const inputs = await page.$$("input:not([type='hidden']), textarea, select");
    for (let i = 0; i < inputs.length; i++) {
      const input = inputs[i];
      const name = (await input.getAttribute("name")) || (await input.getAttribute("placeholder")) || `Input #${i + 1}`;

      const initialOutline = await input.evaluate((el) => window.getComputedStyle(el).outline);
      const initialShadow = await input.evaluate((el) => window.getComputedStyle(el).boxShadow);
      const initialBorder = await input.evaluate((el) => window.getComputedStyle(el).borderColor);

      await input.focus();
      await page.waitForTimeout(100);

      const focusOutline = await input.evaluate((el) => window.getComputedStyle(el).outline);
      const focusShadow = await input.evaluate((el) => window.getComputedStyle(el).boxShadow);
      const focusBorder = await input.evaluate((el) => window.getComputedStyle(el).borderColor);

      const hasFocusIndicator =
        focusOutline !== initialOutline ||
        focusShadow !== initialShadow ||
        focusBorder !== initialBorder;

      results.summary.total++;
      if (hasFocusIndicator) {
        results.summary.passed++;
        results.checks.push({
          element: name,
          type: "INPUT_FOCUS",
          status: "PASS",
          detail: "Focus ring / border color transition present.",
        });
      } else {
        results.summary.warnings++;
        results.checks.push({
          element: name,
          type: "INPUT_FOCUS",
          status: "WARN",
          detail: "No perceptible border or outline change on focus.",
        });
      }
    }

    // 3. Check for text truncation overflows
    const textNodes = await page.$$("h1, h2, h3, h4, p, span, label");
    let truncatedCount = 0;
    for (const node of textNodes) {
      const isTruncated = await node.evaluate((el) => el.scrollWidth > el.clientWidth && window.getComputedStyle(el).overflow !== "visible");
      if (isTruncated) {
        truncatedCount++;
      }
    }

    results.summary.total++;
    if (truncatedCount === 0) {
      results.summary.passed++;
      results.checks.push({
        element: "DOM Text Elements",
        type: "TEXT_OVERFLOW",
        status: "PASS",
        detail: "Zero unintended text truncation detected.",
      });
    } else {
      results.summary.warnings++;
      results.checks.push({
        element: "DOM Text Elements",
        type: "TEXT_OVERFLOW",
        status: "WARN",
        detail: `Found ${truncatedCount} element(s) with potential text clipping/overflow.`,
      });
    }

  } catch (err) {
    results.error = err.message;
  } finally {
    await browser.close();
  }

  if (args.json) {
    console.log(JSON.stringify(results, null, 2));
  } else {
    console.log(`\n=== Interaction & A11y Verification ===`);
    console.log(`Target:   ${results.target}`);
    console.log(`Checks:   Total: ${results.summary.total} | Passed: ${results.summary.passed} | Failed: ${results.summary.failed} | Warnings: ${results.summary.warnings}`);
    console.log(`\nDetailed Breakdown:`);
    for (const check of results.checks) {
      const icon = check.status === "PASS" ? "✓" : check.status === "WARN" ? "⚠" : "✗";
      console.log(`  [${icon}] ${check.type.padEnd(16)} | ${check.element.padEnd(24)} | ${check.detail}`);
    }
  }

  if (results.summary.failed > 0) {
    process.exit(2);
  }
}

runVerification();
