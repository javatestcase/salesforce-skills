import { chromium } from "/tmp/modelcontextprotocol-ext-apps/node_modules/@playwright/test/index.mjs";
import fs from "node:fs";

const output = process.env.MCP_APPS_HOST_CAPTURE_DIR ?? "./evals/mcp_apps/host_captures";
fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleMessages = [];
page.on("console", message => consoleMessages.push(`${message.type()}: ${message.text()}`));
page.on("pageerror", error => consoleMessages.push(`pageerror: ${error.message}`));
await page.goto("http://localhost:8080", { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(8000);
const controls = await page.locator("select, textarea, input, button").evaluateAll(nodes => nodes.map(node => ({
  tag: node.tagName,
  text: node.textContent?.trim(),
  type: node.getAttribute("type"),
  name: node.getAttribute("name"),
  value: node.value,
  aria: node.getAttribute("aria-label"),
  placeholder: node.getAttribute("placeholder")
})));
const body = await page.locator("body").innerText();
await page.screenshot({ path: `${output}/basic-host-initial.png`, fullPage: true });
fs.writeFileSync(`${output}/basic-host-initial.json`, JSON.stringify({ body, controls, consoleMessages }, null, 2));
console.log(JSON.stringify({ body, controls, consoleMessages }, null, 2));
await browser.close();
