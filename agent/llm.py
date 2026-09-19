"""
VEILGUARD — shared LLM client.

One place that talks to whatever LLM provider is configured, so the agent and
the RAG chat don't each need provider-specific code.

Supports:
  - OpenRouter (OpenAI-compatible API) — free models like Nemotron
  - Anthropic (Claude)

Both a plain chat call and a tool-use call are exposed. OpenRouter uses the
OpenAI tool-calling format; Anthropic uses its own. This module normalizes
both to a simple internal shape so callers stay provider-agnostic.
"""

import os
import json


class LLMUnavailable(Exception):
    pass


def _provider():
    from config import LLM_PROVIDER
    return LLM_PROVIDER


# ---------------------------------------------------------------- OpenRouter

def _openrouter_client():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise LLMUnavailable("OPENROUTER_API_KEY not set.")
    try:
        from openai import OpenAI
    except ImportError:
        raise LLMUnavailable("Run: pip install openai")
    from config import OPENROUTER_BASE_URL
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)


def _to_openai_tools(tool_schemas):
    """Convert our tool schemas to OpenAI's function-calling format."""
    return [{
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    } for t in tool_schemas]


# ----------------------------------------------------------------- Anthropic

def _anthropic_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMUnavailable("ANTHROPIC_API_KEY not set.")
    try:
        import anthropic
    except ImportError:
        raise LLMUnavailable("Run: pip install anthropic")
    return anthropic.Anthropic(api_key=key)


# --------------------------------------------------------------- public API

def simple_chat(prompt, system=None, max_tokens=800):
    """One-shot text completion. Returns the text, or raises LLMUnavailable."""
    prov = _provider()
    if prov == "openrouter":
        client = _openrouter_client()
        from config import LLM_MODEL
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        resp = client.chat.completions.create(
            model=LLM_MODEL, messages=msgs, max_tokens=max_tokens)
        return resp.choices[0].message.content or ""
    else:
        client = _anthropic_client()
        from config import ANTHROPIC_MODEL
        kw = {"model": ANTHROPIC_MODEL, "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": prompt}]}
        if system:
            kw["system"] = system
        msg = client.messages.create(**kw)
        return "".join(b.text for b in msg.content
                       if getattr(b, "type", "") == "text")


def available():
    """True if the configured provider has a usable key + SDK."""
    try:
        if _provider() == "openrouter":
            _openrouter_client()
        else:
            _anthropic_client()
        return True
    except LLMUnavailable:
        return False
