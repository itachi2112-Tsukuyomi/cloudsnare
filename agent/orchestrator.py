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


DECLINED = {"ok": False, "declined": True,
            "summary": "Action cancelled by the user."}


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
        # Set when a write action was proposed but the confirmation has to come
        # from somewhere this call can't reach (a browser). Resolved by resume().
        self.pending = None

    # ---- tool execution + gates (provider-agnostic) ----

    def _execute(self, name, params):
        """Run a tool unconditionally and audit the outcome."""
        spec = TOOLS.get(name)
        if not spec:
            return {"ok": False, "error": f"unknown tool {name}"}
        try:
            result = spec["fn"](region=self.region, **params)
        except TypeError as e:
            result = {"ok": False, "error": f"bad parameters for {name}: {e}"}
        _audit(self.log_path, {"tool": name, "params": params,
                               "status": "ok" if result.get("ok") else "error",
                               "result": result.get("summary") or result.get("error")})
        return result

    def _gate(self, name, params):
        """
        Decide whether a tool may run right now: "run" | "declined" | "defer".

        confirm_fn returns True/False to answer inline (the CLI blocks on input),
        or None to say "I can't answer here" — which defers instead of denying.
            Treating a deferral as a denial is what used to break the web flow:
            the model was told the action was cancelled, so confirming afterwards
            produced another apology instead of the action.
        """
        spec = TOOLS.get(name)
        if not spec or not spec["writes"] or not self.confirm_fn:
            return "run"
        decision = self.confirm_fn(self._describe(name, params))
        if decision is True:
            return "run"
        if decision is False:
            return "declined"
        return "defer"

    def _defer(self, name, params, assistant_text):
        """Record a proposed action and hand it back for out-of-band approval."""
        description = self._describe(name, params)
        self.pending = {"name": name, "params": params, "description": description}
        note = (assistant_text or "").strip()
        # Keep the proposal in history (so a later turn has context) but without
        # the tool-call protocol — nothing ran, so nothing may claim a result.
        self.messages.append({
            "role": "assistant",
            "content": (note + "\n" if note else "") +
                       f"[Proposed action awaiting user confirmation: {description}]",
        })
        return {"reply": note, "pending": description}

    def resume(self, approved):
        """
        Resolve the action left by a deferral. Executes it directly rather than
        asking the model again, so a confirmed action always actually happens.
        """
        if not self.pending:
            return {"reply": "There is nothing awaiting confirmation.",
                    "pending": None}
        p, self.pending = self.pending, None

        if not approved:
            _audit(self.log_path, {"tool": p["name"], "params": p["params"],
                                   "status": "declined"})
            text = f"Cancelled — I did not proceed with: {p['description']}"
        else:
            result = self._execute(p["name"], p["params"])
            text = result.get("summary") or result.get("error") or "Done."

        self.messages.append({"role": "assistant", "content": text})
        return {"reply": text, "pending": None}

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
        from agent.llm import (_openrouter_client, _to_openai_tools,
                               LLMUnavailable, openai_first_message)
        try:
            client = _openrouter_client()
        except LLMUnavailable as e:
            return {"reply": f"[Agent unavailable] {e}", "pending": None}

        tools = _to_openai_tools(TOOL_SCHEMAS)
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(6):
            resp = client.chat.completions.create(
                model=self.model, messages=self.messages,
                tools=tools, max_tokens=1024)
            m = openai_first_message(resp)

            if m.tool_calls:
                # Resolve every gate BEFORE touching history, so a deferral can
                # bail out without leaving a half-finished tool exchange behind.
                resolved = []
                for tc in m.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    resolved.append(
                        (tc, args, self._gate(tc.function.name, args)))

                deferred = next((r for r in resolved if r[2] == "defer"), None)
                if deferred:
                    tc, args, _ = deferred
                    return self._defer(tc.function.name, args, m.content)

                self.messages.append({
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [{
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments},
                    } for tc in m.tool_calls],
                })
                for tc, args, gate in resolved:
                    if gate == "declined":
                        _audit(self.log_path, {"tool": tc.function.name,
                                               "params": args, "status": "declined"})
                        result = DECLINED
                    else:
                        result = self._execute(tc.function.name, args)
                    self.messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "content": json.dumps(result)})
                continue

            self.messages.append({"role": "assistant", "content": m.content or ""})
            return {"reply": m.content or "", "pending": None}

        return {"reply": "Stopped after too many tool steps. Please rephrase.",
                "pending": None}

    # ---- Anthropic (Claude) tool loop ----

    def _send_anthropic(self, user_message):
        from agent.llm import _anthropic_client, LLMUnavailable
        try:
            client = _anthropic_client()
        except LLMUnavailable as e:
            return {"reply": f"[Agent unavailable] {e}", "pending": None}

        self.messages.append({"role": "user", "content": user_message})
        for _ in range(6):
            resp = client.messages.create(
                model=self.model, max_tokens=1024,
                system=SYSTEM_PROMPT, tools=TOOL_SCHEMAS,
                messages=self.messages)

            if resp.stop_reason == "tool_use":
                text_so_far = "".join(b.text for b in resp.content
                                      if getattr(b, "type", "") == "text")
                uses = [b for b in resp.content
                        if getattr(b, "type", "") == "tool_use"]

                # Same ordering rule as the OpenRouter path: gates first, so a
                # deferral leaves history clean.
                resolved = [(b, b.input or {}, self._gate(b.name, b.input or {}))
                            for b in uses]
                deferred = next((r for r in resolved if r[2] == "defer"), None)
                if deferred:
                    block, args, _ = deferred
                    return self._defer(block.name, args, text_so_far)

                self.messages.append({"role": "assistant", "content": resp.content})
                results = []
                for block, args, gate in resolved:
                    if gate == "declined":
                        _audit(self.log_path, {"tool": block.name, "params": args,
                                               "status": "declined"})
                        r = DECLINED
                    else:
                        r = self._execute(block.name, args)
                    results.append({"type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(r)})
                self.messages.append({"role": "user", "content": results})
                continue

            text = "".join(b.text for b in resp.content
                           if getattr(b, "type", "") == "text")
            self.messages.append({"role": "assistant", "content": resp.content})
            return {"reply": text, "pending": None}

        return {"reply": "Stopped after too many tool steps. Please rephrase.",
                "pending": None}
