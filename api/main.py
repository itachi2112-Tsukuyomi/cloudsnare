"""
CLOUDSNARE API — the FastAPI backend (Part 8).

This is the single interface the dashboard (Part 9) talks to. It exposes
every stage of the loop over REST:

  GET  /api/status            summary counts for the dashboard header
  GET  /api/surface           current attack surface (latest scan)
  GET  /api/score             composite 0-100 exposure score (+ trend)
  GET  /api/changes           what changed since the previous scan
  GET  /api/decoys            deployed decoys
  GET  /api/attacks           captured attacker activity (+ breach flag)
  GET  /api/intel             intelligence (time-to-attack, techniques...)
  GET  /api/report            the incident report (markdown)
  GET  /api/remediations      remediation recommendations
  POST /api/scan              trigger a fresh scan + sync the remediation queue
  POST /api/remediations/{id}/approve   approve one fix
  POST /api/remediations/apply          apply approved fixes

Read endpoints simply serve what the engines wrote to disk, so they work
with no AWS calls. Action endpoints (scan, apply) call AWS and need creds.

Interactive docs are auto-generated at /docs — great for demos.

Run it (project root, venv active):
    uvicorn api.main:app --reload --port 8000
then open http://localhost:8000/docs
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, FileResponse

from config import (
    AWS_REGION, SNAPSHOT_DIR, DECOY_STATE_FILE, CAPTURE_FILE,
    INTEL_FILE, REPORT_FILE, REMEDIATION_FILE, ENDPOINTS_FILE,
)
from mapper.snapshot import list_snapshots, load_snapshot, diff_latest_two
from mapper.scoring import score_findings
from api import models

app = FastAPI(
    title="CLOUDSNARE API",
    description="Cloud Attack Surface Intelligence & Deception Platform",
    version="1.0.0",
)

# Allow the React dashboard (a different port, or file://) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # demo-friendly; tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the dashboard from the same origin at /dashboard — this avoids any
# browser file:// restrictions. Open http://localhost:8000/dashboard
_DASH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "dashboard", "index.html")


@app.get("/dashboard")
def dashboard():
    if os.path.exists(_DASH):
        return FileResponse(_DASH)
    raise HTTPException(status_code=404, detail="dashboard/index.html not found")


# ---- helpers ---------------------------------------------------------------

def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _latest_snapshot():
    snaps = list_snapshots(SNAPSHOT_DIR)
    if not snaps:
        return {"timestamp": None, "count": 0, "findings": []}
    return load_snapshot(snaps[-1])


def _real_findings(snapshot, decoys_state):
    """Findings with our own decoys filtered out, for an honest exposure view."""
    decoy_names = {d["bucket"] for d in decoys_state.get("decoys", [])}
    return [f for f in snapshot.get("findings", [])
            if f.get("resource") not in decoy_names
            and not str(f.get("resource", "")).startswith("cloudsnare")]


# ---- root ------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "CLOUDSNARE API",
        "loop": "MAP -> DECEIVE -> CAPTURE -> LEARN -> ACT",
        "docs": "/docs",
    }


# ---- status (dashboard header) ---------------------------------------------

@app.get("/api/status", response_model=models.StatusResponse)
def status():
    snap = _latest_snapshot()
    decoys = _load_json(DECOY_STATE_FILE, {"decoys": []})
    captures = _load_json(CAPTURE_FILE, {"captures": []}).get("captures", [])
    remeds = _load_json(REMEDIATION_FILE, {"recommendations": []}).get("recommendations", [])

    # count real exposures (exclude decoys) for an honest number
    real = _real_findings(snap, decoys)
    sc = score_findings(real)

    breach = any(c.get("severity") == "CONFIRMED_BREACH" for c in captures)
    pending = [r for r in remeds if r.get("status") == "pending"]

    return models.StatusResponse(
        region=AWS_REGION,
        exposed_resources=len(real),
        decoys_active=len(decoys.get("decoys", [])),
        captures=len(captures),
        confirmed_breach=breach,
        pending_remediations=len(pending),
        exposure_score=sc["score"],
        exposure_band=sc["band"],
    )


# ---- MAP -------------------------------------------------------------------

@app.get("/api/surface", response_model=models.SurfaceResponse)
def surface():
    return _latest_snapshot()


@app.get("/api/changes", response_model=models.ChangesResponse)
def changes():
    diff, _old, _new = diff_latest_two(SNAPSHOT_DIR)
    if diff is None:
        return models.ChangesResponse()
    return diff


@app.get("/api/score", response_model=models.ExposureScore)
def exposure_score():
    """Composite 0-100 exposure score for the current real attack surface,
    with the delta since the previous scan when one exists."""
    snaps = list_snapshots(SNAPSHOT_DIR)
    if not snaps:
        return models.ExposureScore()

    decoys = _load_json(DECOY_STATE_FILE, {"decoys": []})
    current = score_findings(_real_findings(load_snapshot(snaps[-1]), decoys))
    result = models.ExposureScore(**current)

    if len(snaps) >= 2:
        previous = score_findings(_real_findings(load_snapshot(snaps[-2]), decoys))
        result.previous_score = previous["score"]
        result.delta = current["score"] - previous["score"]

    return result


@app.post("/api/scan", response_model=models.ActionResult)
def scan():
    """Trigger a fresh attack-surface scan (calls AWS) and keep the
    remediation queue in sync with it — a fixed/removed exposure drops out,
    a new one shows up, and any prior approve/apply decision is preserved."""
    try:
        from mapper.scanner import scan_all
        from mapper.snapshot import save_snapshot
        from remediation.engine import refresh_state
        findings, errors = scan_all(AWS_REGION)
        save_snapshot(findings, errors, SNAPSHOT_DIR)
        decoys = _load_json(DECOY_STATE_FILE, {"decoys": []})
        refresh_state(findings, decoys, REMEDIATION_FILE)
        return models.ActionResult(
            ok=True,
            message=f"Scan complete: {len(findings)} internet-facing resources. "
                    f"Remediation queue synced.",
            detail={"count": len(findings), "errors": len(errors)},
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Scan failed: {e}")


# ---- DECEIVE ---------------------------------------------------------------

@app.get("/api/decoys", response_model=models.DecoysResponse)
def decoys():
    state = _load_json(DECOY_STATE_FILE, {"decoys": []})
    return models.DecoysResponse(
        naming=state.get("naming"),
        deployed_at=state.get("deployed_at"),
        count=len(state.get("decoys", [])),
        decoys=state.get("decoys", []),
    )


# ---- CAPTURE ---------------------------------------------------------------

@app.get("/api/attacks", response_model=models.AttacksResponse)
def attacks():
    data = _load_json(CAPTURE_FILE, {"captures": []})
    caps = data.get("captures", [])
    breach = any(c.get("severity") == "CONFIRMED_BREACH" for c in caps)
    return models.AttacksResponse(count=len(caps), confirmed_breach=breach,
                                  captures=caps)


# ---- LEARN -----------------------------------------------------------------

@app.get("/api/intel", response_model=models.IntelResponse)
def intel():
    return _load_json(INTEL_FILE, {})


@app.get("/api/report", response_class=PlainTextResponse)
def report():
    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No incident report yet. Run the intelligence engine first."


# ---- ACT (remediation) -----------------------------------------------------

@app.get("/api/remediations", response_model=models.RemediationsResponse)
def remediations():
    data = _load_json(REMEDIATION_FILE, {"recommendations": []})
    recs = data.get("recommendations", [])
    return models.RemediationsResponse(count=len(recs), recommendations=recs)


@app.post("/api/remediations/{rec_id}/approve", response_model=models.ActionResult)
def approve_remediation(rec_id: str):
    from remediation.engine import load_state, save_state, approve
    state = load_state(REMEDIATION_FILE)
    msg = approve(state, rec_id)
    if msg == "not found":
        raise HTTPException(status_code=404, detail="Recommendation not found")
    save_state(state, REMEDIATION_FILE)
    return models.ActionResult(ok=True, message=f"[{rec_id}] {msg}")


@app.post("/api/remediations/apply", response_model=models.ActionResult)
def apply_remediations():
    """Apply all approved fixes (calls AWS)."""
    try:
        from remediation.engine import load_state, save_state, apply_approved
        state = load_state(REMEDIATION_FILE)
        approved = [r for r in state["recommendations"] if r["status"] == "approved"]
        if not approved:
            return models.ActionResult(ok=True, message="Nothing approved to apply.")
        outcomes = apply_approved(state, AWS_REGION)
        save_state(state, REMEDIATION_FILE)
        applied = sum(1 for _, s, _ in outcomes if s == "applied")
        failed = sum(1 for _, s, _ in outcomes if s == "failed")
        return models.ActionResult(
            ok=True,
            message=f"Applied {applied} fix(es), {failed} failed.",
            detail={"outcomes": [{"id": i, "status": s, "result": r}
                                 for i, s, r in outcomes]},
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Apply failed: {e}")


# ---- RAG (SOC analyst chat) ------------------------------------------------

@app.post("/api/chat")
def chat(payload: dict):
    """
    Ask a plain-English question about CLOUDSNARE's own data.
    Body: {"question": "..."}  ->  {answer, mode, sources}
    """
    question = (payload or {}).get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Provide a 'question'.")
    from rag.chat import answer
    return answer(question)


# ---- Agent (secure provisioning assistant) ---------------------------------

_AGENT_SESSIONS = {}


@app.post("/api/agent")
def agent_chat(payload: dict):
    """
    Talk to the secure provisioning agent.
    Body: {"message": "...", "session": "abc", "confirm": true|false|null}

    A browser can't answer a terminal prompt, so confirmation is handled over
    two calls: the agent returns a `pending` action, the UI shows a confirm
    button, and the next call carries confirm=true to actually execute.
    """
    from config import (AWS_REGION, LLM_PROVIDER, LLM_MODEL,
                        ANTHROPIC_MODEL, AGENT_AUDIT_LOG)
    from agent.orchestrator import Agent
    from agent.llm import available

    if not available():
        return {"reply": "[Agent unavailable] Set OPENROUTER_API_KEY (or "
                         "ANTHROPIC_API_KEY) and install the SDK.", "pending": None}

    message = (payload or {}).get("message", "").strip()
    session = (payload or {}).get("session", "default")
    confirm = (payload or {}).get("confirm", None)
    model = LLM_MODEL if LLM_PROVIDER == "openrouter" else ANTHROPIC_MODEL

    holder = {"decision": confirm, "pending": None}

    def _confirm(action_text):
        if holder["decision"] is True:
            return True
        if holder["decision"] is False:
            return False
        holder["pending"] = action_text
        return False  # defer — nothing executes until the UI confirms

    if session not in _AGENT_SESSIONS:
        _AGENT_SESSIONS[session] = Agent(
            region=AWS_REGION, model=model,
            log_path=AGENT_AUDIT_LOG, confirm_fn=_confirm)
    agent = _AGENT_SESSIONS[session]
    agent.confirm_fn = _confirm

    result = agent.send(message)
    return {"reply": result.get("reply", ""), "pending": holder["pending"]}
