"""
CLOUDSNARE Mapper — exposure scoring.

Turns a list of findings into a single 0-100 "Exposure Score" — a composite,
at-a-glance measure of how exposed the account currently is right now.
Higher = worse (more exposed), matching how most CSPM/risk scores read.

Pure and deterministic: same findings in, same score out. No AWS calls,
so it's cheap to unit-test and cheap to recompute on every request.
"""

from config import EXPOSURE_SEVERITY_WEIGHTS, EXPOSURE_SCORE_CAP

# Ordered low -> high; the highest threshold the score clears wins.
_BANDS = [
    (0, "CLEAR"),
    (1, "LOW"),
    (25, "MEDIUM"),
    (50, "HIGH"),
    (75, "CRITICAL"),
]


def band_for(score):
    """Map a 0-100 score to a human label."""
    band = _BANDS[0][1]
    for threshold, name in _BANDS:
        if score >= threshold:
            band = name
    return band


def score_findings(findings):
    """
    Compute the composite exposure score for a list of findings.

    Callers are expected to pass only "real" findings (decoys already
    filtered out) — a decoy is deliberately exposed, so it shouldn't move
    the needle on how exposed the real account is.

    Returns:
        {
            "score": int,        0-100, capped, higher = more exposed
            "band": str,         CLEAR | LOW | MEDIUM | HIGH | CRITICAL
            "raw": int,          uncapped weighted sum (useful for trend deltas
                                  once the account is already maxed out at 100)
            "by_service": {...}, weighted contribution per AWS service
            "by_risk": {...},    finding count per risk level
        }
    """
    raw = 0
    by_service = {}
    by_risk = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for f in findings or []:
        risk = f.get("risk", "LOW")
        weight = EXPOSURE_SEVERITY_WEIGHTS.get(risk, 0)
        raw += weight
        by_risk[risk] = by_risk.get(risk, 0) + 1
        svc = f.get("service", "OTHER")
        by_service[svc] = by_service.get(svc, 0) + weight

    score = min(EXPOSURE_SCORE_CAP, raw)
    return {
        "score": score,
        "band": band_for(score),
        "raw": raw,
        "by_service": by_service,
        "by_risk": by_risk,
    }
