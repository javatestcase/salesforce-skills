#!/usr/bin/env python3
"""Emit hydrated active widgets plus visible-text and action assertions for browser tests."""

import json
from pathlib import Path

from active_widget_templates import ACTIVE_SKILLS, WidgetTemplateError, assert_active_widget_parity
from batch_widget_contracts import hydrate

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"

VISIBLE_ATTRIBUTES = {
    "tile/text": ("text",),
    "tile/badge": ("label",),
    "tile/callout": ("title",),
    "tile/button": ("label",),
}


def browser_contract(widget):
    visible, messages, links, action_labels, unsupported = [], [], [], [], []

    def visit(value):
        if isinstance(value, dict):
            definition = value.get("definition")
            attributes = value.get("attributes", {})
            if isinstance(definition, str) and isinstance(attributes, dict):
                for name in VISIBLE_ATTRIBUTES.get(definition, ()):
                    candidate = attributes.get(name)
                    if isinstance(candidate, str) and candidate.strip() and candidate not in visible:
                        visible.append(candidate)
                if definition == "tile/button":
                    label = attributes.get("label")
                    click_actions = attributes.get("actions", {}).get("click", [])
                    for action in click_actions if isinstance(click_actions, list) else []:
                        if isinstance(action, dict) and str(action.get("definition", "")).startswith("action/"):
                            if isinstance(label, str) and label.strip():
                                action_labels.append(label)
                elif definition == "action/sendMessage":
                    content = attributes.get("content")
                    if isinstance(content, str) and content.strip():
                        messages.append(content)
                elif definition == "action/openLink":
                    url = attributes.get("url")
                    if isinstance(url, str) and url.strip():
                        links.append(url)
                elif definition.startswith("action/"):
                    unsupported.append(definition)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(widget)
    return {
        "expectedText": visible[:3],
        "expectedMessages": messages,
        "expectedLinks": links,
        "expectedActionLabels": action_labels,
        "unsupportedActions": unsupported,
    }


def leaf_strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for child in value for item in leaf_strings(child)]
    if isinstance(value, dict):
        return [item for child in value.values() for item in leaf_strings(child)]
    return []


def browser_inputs():
    scenario = json.loads((FIXTURES / "ravelin-scenario.json").read_text())
    cases = json.loads((FIXTURES / "ravelin-widget-cases.json").read_text())
    inputs, skipped, widget_skills = [], [], []
    for path in sorted(ACTIVE_SKILLS.iterdir()):
        if not (path / "SKILL.md").is_file():
            continue
        skill = path.name
        try:
            template = assert_active_widget_parity(skill)
        except WidgetTemplateError as exc:
            raise RuntimeError(str(exc)) from exc
        if template is None:
            skipped.append(skill)
            continue
        widget_skills.append(skill)
        case = cases.get(skill)
        if not case:
            raise RuntimeError(f"{skill}: no Ravelin widget case")
        widget = hydrate(template, case["values"])
        contract = browser_contract(widget)
        contract["expectedText"] = case["expectedText"]
        strings = "\n".join(leaf_strings(widget))
        missing_text = [value for value in contract["expectedText"] if value not in strings]
        if missing_text:
            raise RuntimeError(f"{skill}: expectations absent from hydrated widget: {missing_text}")
        if "fixture" in strings.lower() or "example.invalid" in strings:
            raise RuntimeError(f"{skill}: generated placeholder data leaked into Ravelin case")
        if not any("Ravelin" in value for value in contract["expectedText"]):
            raise RuntimeError(f"{skill}: expectations are not anchored to Ravelin")
        if contract["unsupportedActions"]:
            raise RuntimeError(f"{skill}: unsupported actions {contract['unsupportedActions']}")
        expected_action_count = len(contract["expectedMessages"]) + len(contract["expectedLinks"])
        if len(contract["expectedActionLabels"]) != expected_action_count:
            raise RuntimeError(
                f"{skill}: {expected_action_count} declared actions but "
                f"{len(contract['expectedActionLabels'])} rendered button labels"
            )
        inputs.append({"skill": skill, "widget": widget, **contract})
    missing_cases = sorted(set(widget_skills) - set(cases))
    extra_cases = sorted(set(cases) - set(widget_skills))
    if missing_cases or extra_cases:
        raise RuntimeError(f"Ravelin case inventory differs: missing={missing_cases}, extra={extra_cases}")
    return {"scenario": scenario["scenario"], "widgets": inputs, "skipped": skipped}


def main():
    print(json.dumps(browser_inputs()))


if __name__ == "__main__":
    main()
