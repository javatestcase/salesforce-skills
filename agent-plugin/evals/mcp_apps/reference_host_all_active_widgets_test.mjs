import { chromium } from "/tmp/modelcontextprotocol-ext-apps/node_modules/@playwright/test/index.mjs";
import { execFileSync } from "node:child_process";
import fs from "node:fs";

const output = process.env.MCP_APPS_HOST_CAPTURE_DIR ?? "./evals/mcp_apps/host_captures";
const generated = JSON.parse(execFileSync("python3", ["evals/mcp_apps/active_widget_browser_inputs.py"], { encoding: "utf8" }));
fs.mkdirSync(output, { recursive: true });

async function mountedAppFrame(page, expectedText) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const frame = page.frames().find(candidate => candidate !== page.mainFrame() && candidate.url() === "about:blank");
    if (frame) {
      try {
        const text = await frame.locator("body").innerText({ timeout: 1000 });
        if (text.trim() && expectedText.every(candidate => text.includes(candidate))) return { frame, text };
      } catch {
        // The sandbox iframe can exist before its inner renderer body is ready.
      }
    }
    await page.waitForTimeout(500);
  }
  return null;
}

async function renderedPixelStats(page, png) {
  const dataUri = `data:image/png;base64,${png.toString("base64")}`;
  return page.evaluate(async source => {
    const image = new Image();
    image.src = source;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = image.width;
    canvas.height = image.height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const inset = Math.min(20, Math.floor(Math.min(image.width, image.height) / 4));
    let interiorNonWhitePixels = 0;
    for (let y = inset; y < image.height - inset; y += 1) {
      for (let x = inset; x < image.width - inset; x += 1) {
        const offset = (y * image.width + x) * 4;
        if (pixels[offset + 3] > 0 && (pixels[offset] < 245 || pixels[offset + 1] < 245 || pixels[offset + 2] < 245)) {
          interiorNonWhitePixels += 1;
        }
      }
    }
    return { width: image.width, height: image.height, interiorNonWhitePixels };
  }, dataUri);
}

const browser = await chromium.launch({ headless: true });
const results = [];
for (const { skill, widget, expectedText } of generated.widgets) {
  console.log(`Rendering active widget: ${skill}`);
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  const consoleMessages = [];
  page.on("console", message => consoleMessages.push(`${message.type()}: ${message.text()}`));
  page.on("pageerror", error => consoleMessages.push(`pageerror: ${error.message}`));
  try {
    await page.goto("http://localhost:8080", { waitUntil: "networkidle", timeout: 30000 });
    await page.locator("textarea").fill(JSON.stringify({ resourceType: "dynamic", widgetDefinition: widget }));
    await page.locator("button[type=submit]").click();
    const mounted = await mountedAppFrame(page, expectedText);
    const renderedText = mounted?.text ?? "";
    const outerIframes = page.locator("iframe");
    const outerIframeCount = await outerIframes.count();
    const pixelStats = outerIframeCount ? await renderedPixelStats(page, await outerIframes.first().screenshot()) : null;
    const iframeBoxes = await outerIframes.evaluateAll(frames => frames.map(frame => {
      const rect = frame.getBoundingClientRect();
      return { width: rect.width, height: rect.height };
    }));
    const visiblySizedApp = iframeBoxes.some(box => box.width >= 300 && box.height >= 100);
    const visiblyPaintedApp = Boolean(pixelStats && pixelStats.interiorNonWhitePixels >= 500);
    const checks = [
      { name: "MCP App iframe mounted", ok: Boolean(mounted) },
      { name: "MCP App iframe is visibly sized", ok: visiblySizedApp },
      { name: "MCP App iframe paints visible content", ok: visiblyPaintedApp },
      ...expectedText.map(text => ({ name: `visible text: ${text}`, ok: renderedText.includes(text) })),
    ];
    const result = {
      skill,
      expectedText,
      pixelStats,
      iframeBoxes,
      checks,
      iframeText: renderedText,
      consoleMessages,
    };
    result.ok = checks.every(check => check.ok);
    results.push(result);
    await page.screenshot({ path: `${output}/active-widget-${skill}.png`, fullPage: true });
  } catch (error) {
    results.push({ skill, expectedText, checks: [{ name: "browser execution", ok: false }], error: String(error), consoleMessages, ok: false });
  } finally {
    await page.close();
  }
}
await browser.close();

const summary = {
  tested: results.length,
  skipped: generated.skipped,
  passed: results.filter(result => result.ok).map(result => result.skill),
  failed: results.filter(result => !result.ok).map(result => result.skill),
  results,
};
summary.ok = summary.failed.length === 0;
fs.writeFileSync(`${output}/all-active-widgets.json`, JSON.stringify(summary, null, 2));
console.log(JSON.stringify({ tested: summary.tested, passed: summary.passed, failed: summary.failed, ok: summary.ok }, null, 2));
if (!summary.ok) process.exitCode = 1;
