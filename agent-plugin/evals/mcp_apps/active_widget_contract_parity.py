#!/usr/bin/env python3
"""Fail when an active dynamic-widget renderer changes or a contract differs beyond an approved local exception.

This is deliberately offline. It protects the active skill tree from losing or altering upstream
renderer JSON while allowing approved non-widget query fixes and the calendar-events subtitle
correction that removes an unsupported attendee metric.
"""

import json
import sys

from active_widget_templates import (
    ACTIVE_SKILLS,
    SOURCE_SKILLS,
    WidgetTemplateError,
    assert_active_widget_parity,
    dynamic_renderer,
)


def skill_names(root):
    return sorted(path.name for path in root.iterdir() if (path / "SKILL.md").is_file())


def main():
    source_names = skill_names(SOURCE_SKILLS)
    active_names = skill_names(ACTIVE_SKILLS)
    if source_names != active_names:
        missing = sorted(set(source_names) - set(active_names))
        extra = sorted(set(active_names) - set(source_names))
        raise WidgetTemplateError(f"skill inventory differs: missing={missing}, extra={extra}")

    checked, without_widgets = [], []
    for skill in source_names:
        source = SOURCE_SKILLS / skill / "SKILL.md"
        if dynamic_renderer(source) is None:
            without_widgets.append(skill)
            continue
        assert_active_widget_parity(skill)
        checked.append(skill)

    print(json.dumps({
        "ok": True,
        "widget_templates_checked": len(checked),
        "widget_skills": checked,
        "without_dynamic_widget": without_widgets,
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WidgetTemplateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
