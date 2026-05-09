"""
Shared lazy-initialized watsonx client for chat generation (and optional tasks).

Uses the same env vars as ingestion extraction:
  WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, WATSONX_MODEL_ID
"""

from __future__ import annotations

import os
from typing import Optional

_client = None


def watsonx_configured() -> bool:
    return bool(os.getenv("WATSONX_API_KEY") and os.getenv("WATSONX_PROJECT_ID"))


def generate_text(
    prompt: str,
    *,
    max_new_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    """
    Single-turn text generation. Raises if not configured or IBM SDK errors.
    """
    global _client
    if not watsonx_configured():
        raise RuntimeError("watsonx not configured (missing WATSONX_API_KEY or WATSONX_PROJECT_ID)")

    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    if _client is None:
        credentials = Credentials(
            url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
            api_key=os.environ["WATSONX_API_KEY"],
        )
        _client = ModelInference(
            model_id=os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct"),
            credentials=credentials,
            project_id=os.environ["WATSONX_PROJECT_ID"],
            params={
                "decoding_method": "greedy",
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
            },
        )

    return _client.generate_text(prompt=prompt).strip()
