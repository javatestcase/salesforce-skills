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

CALENDAR_EVENTS_SOURCE_SUBTITLE = (
    "[N] meetings · [N] deal-linked · [N] external · first at [time], last ends [time]"
)
CALENDAR_EVENTS_ACTIVE_SUBTITLE = (
    "[N] meetings · [N] deal-linked · first at [time], last ends [time]"
)
CALENDAR_EVENTS_SOURCE_SUBTITLE_DESCRIPTION = (
    "Caption subhead: meeting count, deal-linked count, external count, first start / last end."
)
CALENDAR_EVENTS_ACTIVE_SUBTITLE_DESCRIPTION = (
    "Caption subhead: meeting count, deal-linked count, first start / last end."
)
CALENDAR_EVENTS_SOURCE_SUBTITLE_EXAMPLE = (
    "6 meetings · 4 deal-linked · 2 external · first at 9:00, last ends 4:30"
)
CALENDAR_EVENTS_ACTIVE_SUBTITLE_EXAMPLE = (
    "6 meetings · 4 deal-linked · first at 9:00, last ends 4:30"
)


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


def dynamic_renderer_block(path):
    """Return the sole dynamic-renderer ``(raw_text, value)`` pair, or None."""
    renderers = [
        (raw, value)
        for raw, value in json_fences(path)
        if isinstance(value, dict) and isinstance(value.get("renderer"), dict)
    ]
    if not renderers:
        return None
    if len(renderers) != 1:
        raise WidgetTemplateError(f"{path}: expected one renderer JSON block, found {len(renderers)}")
    return renderers[0]


def dynamic_renderer(path):
    """Return the sole dynamic renderer definition in a skill, or None when absent."""
    block = dynamic_renderer_block(path)
    return None if block is None else block[1]


def variable_contract(path):
    """Return the sole variable-contract JSON object in a skill, or None when absent."""
    contracts = [
        value
        for _, value in json_fences(path)
        if isinstance(value, dict)
        and isinstance(value.get("$comment"), str)
        and "Variable contract" in value["$comment"]
    ]
    if not contracts:
        return None
    if len(contracts) != 1:
        raise WidgetTemplateError(f"{path}: expected one variable-contract JSON block, found {len(contracts)}")
    return contracts[0]


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


def expected_calendar_events_contract(source_contract):
    """Return the one approved active-only calendar contract variation."""
    expected = json.loads(json.dumps(source_contract))
    comment = expected.get("$comment")
    if not isinstance(comment, str) or CALENDAR_EVENTS_SOURCE_SUBTITLE not in comment:
        raise WidgetTemplateError("calendar-events: upstream variable contract changed unexpectedly")
    expected["$comment"] = comment.replace(
        CALENDAR_EVENTS_SOURCE_SUBTITLE, CALENDAR_EVENTS_ACTIVE_SUBTITLE
    )

    subtitle = expected.get("props", {}).get("subtitle")
    if not isinstance(subtitle, dict):
        raise WidgetTemplateError("calendar-events: upstream subtitle contract is missing")
    if subtitle.get("description") != CALENDAR_EVENTS_SOURCE_SUBTITLE_DESCRIPTION:
        raise WidgetTemplateError("calendar-events: upstream subtitle description changed unexpectedly")
    if subtitle.get("example") != CALENDAR_EVENTS_SOURCE_SUBTITLE_EXAMPLE:
        raise WidgetTemplateError("calendar-events: upstream subtitle example changed unexpectedly")
    subtitle["description"] = CALENDAR_EVENTS_ACTIVE_SUBTITLE_DESCRIPTION
    subtitle["example"] = CALENDAR_EVENTS_ACTIVE_SUBTITLE_EXAMPLE
    return expected


def assert_calendar_events_local_contract(source, active):
    """Allow only the approved no-attendee-count calendar contract correction."""
    source_renderer = dynamic_renderer_block(source)
    active_renderer = dynamic_renderer_block(active)
    if source_renderer is None or active_renderer is None:
        raise WidgetTemplateError("calendar-events: dynamic renderer is missing")
    if source_renderer[0] != active_renderer[0]:
        raise WidgetTemplateError("calendar-events: active renderer JSON differs from upstream")

    source_contract = variable_contract(source)
    active_contract = variable_contract(active)
    if source_contract is None or active_contract is None:
        raise WidgetTemplateError("calendar-events: variable contract is missing")
    if active_contract != expected_calendar_events_contract(source_contract):
        raise WidgetTemplateError(
            "calendar-events: active variable contract differs beyond the approved subtitle correction"
        )
    if "external" in active.read_text().lower():
        raise WidgetTemplateError("calendar-events: active skill still claims an external attendee metric")


def assert_active_widget_parity(skill):
    """Return the active renderer after enforcing exact or approved widget-block parity."""
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
        if skill == "calendar-events":
            assert_calendar_events_local_contract(source, active)
        else:
            raise WidgetTemplateError(f"{skill}: active widget JSON/variable-contract blocks differ from upstream")
    return active_renderer
