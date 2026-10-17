import { chromium } from "/tmp/modelcontextprotocol-ext-apps/node_modules/@playwright/test/index.mjs";
import fs from "node:fs";
import { activeAccountContextWidget } from "./reference_host_active_widget.mjs";

const output = process.env.MCP_APPS_HOST_CAPTURE_DIR ?? "./evals/mcp_apps/host_captures";
const widget = activeAccountContextWidget();
fs.mkdirSync(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
const consoleMessages = [];
page.on("console", message => consoleMessages.push(`${message.type()}: ${message.text()}`));
page.on("pageerror", error => consoleMessages.push(`pageerror: ${error.message}`));

await page.goto("http://localhost:8080", { waitUntil: "networkidle", timeout: 30000 });
await page.locator("textarea").fill(JSON.stringify({ resourceType: "dynamic", widgetDefinition: widget }));
await page.locator("button[type=submit]").click();
await page.waitForTimeout(10000);

const frames = [];
for (const frame of page.frames()) {
  try {
    frames.push({ url: frame.url(), text: (await frame.locator("body").innerText()).slice(0, 20000) });
  } catch (error) {
    frames.push({ url: frame.url(), error: String(error) });
  }
}
const renderedText = frames.map(frame => frame.text ?? "").join("\n");
const required = ["Ravelin Rail Logistics", "RECOMMENDED MOVE", "Open Opportunities", "Key Contacts", "Account Details", "Draft the note", "View in Salesforce", "Draft Email"];
const checks = required.map(text => ({ text, ok: renderedText.includes(text) }));
const hostText = await page.locator("body").innerText();
await page.screenshot({ path: `${output}/account-context-host.png`, fullPage: true });
const result = { checks, ok: checks.every(check => check.ok), hostText, frames, consoleMessages };
fs.writeFileSync(`${output}/account-context-host.json`, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (!result.ok) process.exitCode = 1;
