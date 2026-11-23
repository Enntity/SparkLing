# SPDX-License-Identifier: AGPL-3.0-only
"""Shared endpoint settings for SparkLing's small functional checks."""

from __future__ import annotations

import os


SERVED_MODEL_NAME = os.environ.get("SERVED_MODEL_NAME", "ling-3.2-air-atlas")


def chat_url(port: str | None = None) -> str:
    """Return the OpenAI chat endpoint, with an independently configurable port."""
    default_port = port or os.environ.get("SPARKLING_PORT", "8897")
    base = os.environ.get("SPARKLING_URL", f"http://127.0.0.1:{default_port}").rstrip("/")
    suffix = "/v1/chat/completions"
    return base if base.endswith(suffix) else base + suffix
