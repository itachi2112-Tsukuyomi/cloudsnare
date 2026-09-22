"""
CLOUDSNARE Agent - orchestrator.

Brain-and-hands separation:
  - The LLM is the BRAIN: reads the conversation and tool menu, asks
    follow-up questions, decides which tool to call.
  - This orchestrator is the HANDS: validates the call, enforces the
    confirmation gate for state-changing actions, executes the real boto3
    tool, logs it, and feeds the result back to the model.

Works with either provider (see config.LLM_PROVIDER):
  - openrouter (OpenAI-compatible tool calling) - e.g. free Nemotron
  - anthropic  (Claude tool use)

Safety layers enforced here regardless of provider:
  1. Only tools in the registry can run.
  2. WRITE tools require explicit human confirmation before executing.
  3. Every executed action is appended to an audit log.
"""

import os
import json
from datetime import datetime, timezone

from agent.tools import TOOLS
from agent.schemas import TOOL_SCHEMAS, SYSTEM_PROMPT


def _audit(log_path, entry):
    entry = {"time": datetime.now(timezone.utc).isoformat(), **entry}
    try:
        data = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.append(entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class Agent:
    def __init__(self, region, model, log_path, confirm_fn=None, provider=None):
        self.region = region
        self.model = model
        self.log_path = log_path
        self.confirm_fn = confirm_fn
        if provider is None:
            from config import LLM_PROVIDER
            provider = LLM_PROVIDER
        self.provider = provider
        # OpenAI-format conversations carry the system prompt as message[0].
        self.messages = ([{"role": "system", "content": SYSTEM_PROMPT}]
                         if provider == "openrouter" else [])

    # ---- tool execution + gates (provider-agnostic) ----

    def _run_tool(self, name, params):
        spec = TOOLS.get(name)
        if not spec:
            return {"ok": False, "error": f"unknown tool {name}"}
        if spec["writes"] and self.confirm_fn:
            if not self.confirm_fn(self._describe(name, params)):
                _audit(self.log_path, {"tool": name, "params": params,
                                       "status": "declined"})
                return {"ok": False, "declined": True,
                        "summary": "Action cancelled by the user."}
        result = spec["fn"](region=self.region, **params)
        _audit(self.log_path, {"tool": name, "params": params,
                               "status": "ok" if result.get("ok") else "error",
                               "result": result.get("summary") or result.get("error")})
        return result

    @staticmethod
    def _describe(name, params):
        if name == "create_secure_bucket":
            return (f"Create a PRIVATE, encrypted, versioned S3 bucket "
                    f"named '{params.get('name')}'")
        if name == "create_secure_ec2":
            return (f"Launch a locked-down EC2 instance '{params.get('name')}' "
                    f"({params.get('instance_type', 't2.micro')}, no public IP). "
                    f"This costs money until terminated.")
        return f"Run {name} with {params}"

    # ---- entry point ----

    def send(self, user_message):
        if self.provider == "openrouter":
            return self._send_openrouter(user_message)
        return self._send_anthropic(user_message)

    # ---- OpenRouter (OpenAI-compatible) tool loop ----

    def _send_openrouter(self, user_message):
        from agent.llm import _openrouter_client, _to_openai_tools, LLMUnavailable
        try:
            client = _openrouter_client()
        except LLMUnavailable as e:
            return {"reply": f"[Agent unavailable] {e}"}

        tools = _to_openai_tools(TOOL_SCHEMAS)
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(6):
            resp = client.chat.completions.create(
                model=self.model, messages=self.messages,
                tools=tools, max_tokens=1024)
            m = resp.choices[0].message

            if m.tool_calls:
                self.messages.append({
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [{
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments},
                    } for tc in m.tool_calls],
                })
                for tc in m.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = self._run_tool(tc.function.name, args)
                    self.messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "content": json.dumps(result)})
                continue

            self.messages.append({"role": "assistant", "content": m.content or ""})
            return {"reply": m.content or ""}

        return {"reply": "Stopped after too many tool steps. Please rephrase."}

    # ---- Anthropic (Claude) tool loop ----

    def _send_anthropic(self, user_message):
        from agent.llm import _anthropic_client, LLMUnavailable
        try:
            client = _anthropic_client()
        except LLMUnavailable as e:
            return {"reply": f"[Agent unavailable] {e}"}

        self.messages.append({"role": "user", "content": user_message})
        for _ in range(6):
            resp = client.messages.create(
                model=self.model, max_tokens=1024,
                system=SYSTEM_PROMPT, tools=TOOL_SCHEMAS,
                messages=self.messages)

            if resp.stop_reason == "tool_use":
                self.messages.append({"role": "assistant", "content": resp.content})
                results = []
                for block in resp.content:
                    if getattr(block, "type", "") == "tool_use":
                        r = self._run_tool(block.name, block.input or {})
                        results.append({"type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(r)})
                self.messages.append({"role": "user", "content": results})
                continue

            text = "".join(b.text for b in resp.content
                           if getattr(b, "type", "") == "text")
            self.messages.append({"role": "assistant", "content": resp.content})
            return {"reply": text}

        return {"reply": "Stopped after too many tool steps. Please rephrase."}
