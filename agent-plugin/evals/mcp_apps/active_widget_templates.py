"""Extract and compare dynamic-widget templates from active skills."""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parents[1]
REPO_ROOT = PLUGIN_ROOT.parent
SOURCE_SKILLS = REPO_ROOT / "salesforce-for-sales" / "skills"
ACTIVE_SKILLS = PLUGIN_ROOT / "skills"
JSON_FENCE_RE = re.compile(r"```json\n(.*?)\n```", re.S)


class WidgetTemplateError(RuntimeError):
    """Raised when a dynamic widget template is missing or does not match upstream."""


def json_fences(path):
    """Return parsed JSON fences as ``(raw_text, value)`` pairs."""
    values = []
    for raw in JSON_FENCE_RE.findall(path.read_text()):
        try:
            values.append((raw, json.loads(raw)))
        except json.JSONDecodeError:
            continue
    return values


def dynamic_renderer(path):
    """Return the sole dynamic renderer definition in a skill, or None when absent."""
    renderers = [value for _, value in json_fences(path)
                 if isinstance(value, dict) and isinstance(value.get("renderer"), dict)]
    if not renderers:
        return None
    if len(renderers) != 1:
        raise WidgetTemplateError(f"{path}: expected one renderer JSON block, found {len(renderers)}")
    return renderers[0]


def widget_blocks(path):
    """Return raw JSON widget-template and variable-contract blocks in source order."""
    blocks = []
    for raw, value in json_fences(path):
        is_renderer = isinstance(value, dict) and isinstance(value.get("renderer"), dict)
        comment = value.get("$comment", "") if isinstance(value, dict) else ""
        is_contract = isinstance(comment, str) and "Variable contract" in comment
        if is_renderer or is_contract:
            blocks.append(raw)
    return blocks


def skill_paths(skill):
    return SOURCE_SKILLS / skill / "SKILL.md", ACTIVE_SKILLS / skill / "SKILL.md"


def assert_active_widget_parity(skill):
    """Return the active renderer after proving its widget blocks match upstream exactly."""
    source, active = skill_paths(skill)
    if not source.is_file():
        raise WidgetTemplateError(f"{skill}: upstream skill file missing: {source}")
    if not active.is_file():
        raise WidgetTemplateError(f"{skill}: active skill file missing: {active}")

    source_renderer = dynamic_renderer(source)
    active_renderer = dynamic_renderer(active)
    if source_renderer is None:
        if active_renderer is not None:
            raise WidgetTemplateError(f"{skill}: active skill adds a dynamic widget absent upstream")
        return None
    if active_renderer is None:
        raise WidgetTemplateError(f"{skill}: active skill is missing the upstream dynamic widget")

    source_blocks = widget_blocks(source)
    active_blocks = widget_blocks(active)
    if source_blocks != active_blocks:
        raise WidgetTemplateError(f"{skill}: active widget JSON/variable-contract blocks differ from upstream")
    return active_renderer
