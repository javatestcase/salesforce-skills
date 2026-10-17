import { chromium } from "/tmp/modelcontextprotocol-ext-apps/node_modules/@playwright/test/index.mjs";
import fs from "node:fs";
import { activeAccountContextWidget } from "./reference_host_active_widget.mjs";

const output = process.env.MCP_APPS_HOST_CAPTURE_DIR ?? "./evals/mcp_apps/host_captures";
const expectedUrl = "https://orgfarm-39d35ccaaa-dev-ed.develop.my.salesforce.com/lightning/r/Opportunity/006bm00000Wn1XLAAZ/view";
const widget = activeAccountContextWidget();
fs.mkdirSync(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
const blockedNavigations = [];
await context.route("https://orgfarm-39d35ccaaa-dev-ed.develop.my.salesforce.com/**", async route => {
  blockedNavigations.push(route.request().url());
  await route.abort();
});
const page = await context.newPage();
const consoleMessages = [];
page.on("console", message => consoleMessages.push(`${message.type()}: ${message.text()}`));
page.on("pageerror", error => consoleMessages.push(`pageerror: ${error.message}`));

await page.goto("http://localhost:8080", { waitUntil: "networkidle", timeout: 30000 });
await page.locator("textarea").fill(JSON.stringify({ resourceType: "dynamic", widgetDefinition: widget }));
await page.locator("button[type=submit]").click();
await page.waitForTimeout(8000);
const appFrame = page.frames().find(frame => frame.url() === "about:blank" && frame !== page.mainFrame());
if (!appFrame) throw new Error("MCP App inner iframe was not mounted");
await appFrame.getByText("Draft the note", { exact: true }).click();
await page.waitForTimeout(1000);
await appFrame.getByText("View in Salesforce", { exact: true }).click();
await page.waitForTimeout(1000);

const hostText = await page.locator("body").innerText();
const messages = consoleMessages.filter(message => message.includes("Message from MCP App"));
const links = consoleMessages.filter(message => message.includes("Open link request"));
const result = {
  checks: [
    { name: "sendMessage reached host bridge", ok: messages.length > 0 },
    { name: "openLink reached host bridge", ok: links.length > 0 },
    { name: "Lightning navigation was intercepted", ok: blockedNavigations.includes(expectedUrl) },
  ],
  hostText,
  consoleMessages,
  blockedNavigations,
};
result.ok = result.checks.every(check => check.ok);
await page.screenshot({ path: `${output}/account-context-actions.png`, fullPage: true });
fs.writeFileSync(`${output}/account-context-actions.json`, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (!result.ok) process.exitCode = 1;
