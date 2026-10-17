import fs from "node:fs";

const tokenPattern = /\{\{([A-Za-z0-9_]+)\}\}/g;

function activeRenderer() {
  const source = fs.readFileSync("./skills/account-context/SKILL.md", "utf8");
  const renderers = [];
  for (const match of source.matchAll(/```json\n([\s\S]*?)\n```/g)) {
    try {
      const value = JSON.parse(match[1]);
      if (value && typeof value === "object" && value.renderer && typeof value.renderer === "object") {
        renderers.push(value);
      }
    } catch {
      // Non-JSON code fences are not widget templates.
    }
  }
  if (renderers.length !== 1) {
    throw new Error(`expected one active account-context renderer JSON block, found ${renderers.length}`);
  }
  return renderers[0];
}

function hydrate(value, values) {
  if (typeof value === "string") {
    const exact = value.match(/^\{\{([A-Za-z0-9_]+)\}\}$/);
    if (exact) {
      if (!(exact[1] in values)) throw new Error(`missing fixture value for ${exact[1]}`);
      return values[exact[1]];
    }
    return value.replace(tokenPattern, (_match, name) => {
      if (!(name in values)) throw new Error(`missing fixture value for ${name}`);
      return String(values[name]);
    });
  }
  if (Array.isArray(value)) return value.map(item => hydrate(item, values));
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, hydrate(item, values)]));
  }
  return value;
}

export function activeAccountContextWidget() {
  const fixture = JSON.parse(fs.readFileSync("./evals/mcp_apps/fixtures/account-context.json", "utf8"));
  return hydrate(activeRenderer(), fixture.values);
}
