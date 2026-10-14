#!/usr/bin/env python3
"""
Minimal Bedrock client for the eval harness (no dependencies).

Calls the Bedrock Converse API through the AWS CLI, so it needs only `aws` on PATH and a
working profile — no boto3. Used by judge.py (grading) and generate.py (offline executor).

Defaults (override with env vars or function args):
    EVAL_AWS_PROFILE  agentforce-demo
    EVAL_AWS_REGION   us-east-1
    EVAL_MODEL        us.anthropic.claude-sonnet-4-5-20250929-v1:0

Safety: any profile whose name contains "prod" is refused before a request is made.
Evals send skill output and org evidence to the model, so they must never run on
production credentials.
"""

import json
import os
import subprocess
import tempfile

DEFAULT_PROFILE = os.environ.get("EVAL_AWS_PROFILE", "agentforce-demo")
DEFAULT_REGION = os.environ.get("EVAL_AWS_REGION", "us-east-1")
DEFAULT_MODEL = os.environ.get("EVAL_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")

BLOCKED_PROFILE_MARKERS = ("prod",)


class LLMError(RuntimeError):
    """Raised for configuration, credential, or model-call failures."""


def check_profile(profile):
    """Refuse production-looking profiles. Raises LLMError."""
    if not profile:
        raise LLMError("no AWS profile configured (set EVAL_AWS_PROFILE or pass --profile)")
    if any(marker in profile.lower() for marker in BLOCKED_PROFILE_MARKERS):
        raise LLMError(
            f"refusing AWS profile {profile!r}: production profiles are blocked for evals"
        )


def converse(system, user, *, model=None, profile=None, region=None,
             max_tokens=1500, temperature=0.0, timeout=300):
    """Send one system + user turn to Bedrock Converse. Returns (text, usage_dict)."""
    profile = profile or DEFAULT_PROFILE
    region = region or DEFAULT_REGION
    model = model or DEFAULT_MODEL
    check_profile(profile)

    with tempfile.TemporaryDirectory() as td:
        system_path = os.path.join(td, "system.json")
        messages_path = os.path.join(td, "messages.json")
        with open(system_path, "w", encoding="utf-8") as f:
            json.dump([{"text": system}], f)
        with open(messages_path, "w", encoding="utf-8") as f:
            json.dump([{"role": "user", "content": [{"text": user}]}], f)

        cmd = [
            "aws", "bedrock-runtime", "converse",
            "--profile", profile,
            "--region", region,
            "--model-id", model,
            "--system", f"file://{system_path}",
            "--messages", f"file://{messages_path}",
            "--inference-config", json.dumps({"maxTokens": max_tokens, "temperature": temperature}),
            "--cli-read-timeout", str(timeout),
            "--output", "json",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
        except FileNotFoundError:
            raise LLMError("aws CLI not found on PATH")
        except subprocess.TimeoutExpired:
            raise LLMError(f"Bedrock call timed out after {timeout}s")

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        hint = ""
        if any(s in err for s in ("ExpiredToken", "InvalidClientTokenId", "security token")):
            hint = f" (refresh credentials for profile {profile!r})"
        elif "AccessDenied" in err:
            hint = f" (profile {profile!r} lacks bedrock:InvokeModel for {model})"
        raise LLMError(f"Bedrock converse failed (exit {proc.returncode}): {err[:500]}{hint}")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise LLMError(f"unparseable Bedrock response: {e}")

    blocks = data.get("output", {}).get("message", {}).get("content", [])
    text = "".join(b.get("text", "") for b in blocks)
    return text, data.get("usage", {})
