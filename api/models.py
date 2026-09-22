"""
CLOUDSNARE API — response models (Pydantic).

These define the shape of every API response, which gives us:
  - automatic validation
  - clean, typed JSON
  - auto-generated interactive docs at /docs

They mirror the data the engines produce.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Finding(BaseModel):
    id: str
    service: str
    type: str
    resource: str
    detail: str
    risk: str


class SurfaceResponse(BaseModel):
    timestamp: Optional[str] = None
    count: int = 0
    findings: List[Finding] = []


class ChangesResponse(BaseModel):
    added: List[Finding] = []
    removed: List[Finding] = []
    changed: List[Dict[str, Any]] = []


class Decoy(BaseModel):
    bucket: str
    base: Optional[str] = None
    token_id: Optional[str] = None
    real_access_key_id: Optional[str] = None


class DecoysResponse(BaseModel):
    naming: Optional[str] = None
    deployed_at: Optional[str] = None
    count: int = 0
    decoys: List[Decoy] = []


class Capture(BaseModel):
    severity: str
    type: str
    decoy: Optional[str] = None
    token_id: Optional[str] = None
    access_key_id: Optional[str] = None
    source_ip: Optional[str] = None
    event_name: Optional[str] = None
    time: Optional[str] = None


class AttacksResponse(BaseModel):
    count: int = 0
    confirmed_breach: bool = False
    captures: List[Capture] = []


class IntelResponse(BaseModel):
    time_to_attack_seconds: Optional[float] = None
    time_to_attack_human: str = "n/a"
    attacker: Dict[str, Any] = {}
    techniques: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    priority: List[Dict[str, Any]] = []


class Recommendation(BaseModel):
    id: str
    status: str
    auto_fixable: bool
    recommendation: str
    finding: Finding
    result: Optional[str] = None


class RemediationsResponse(BaseModel):
    count: int = 0
    recommendations: List[Recommendation] = []


class StatusResponse(BaseModel):
    region: str
    exposed_resources: int = 0
    decoys_active: int = 0
    captures: int = 0
    confirmed_breach: bool = False
    pending_remediations: int = 0
    exposure_score: int = 0
    exposure_band: str = "CLEAR"


class ExposureScore(BaseModel):
    score: int = 0
    band: str = "CLEAR"
    raw: int = 0
    by_service: Dict[str, int] = {}
    by_risk: Dict[str, int] = {}
    previous_score: Optional[int] = None
    delta: Optional[int] = None


class ActionResult(BaseModel):
    ok: bool
    message: str
    detail: Optional[Dict[str, Any]] = None


# ---- Endpoint agent (laptop scanner) ---------------------------------------

class EndpointFinding(BaseModel):
    check: str
    detail: str
    risk: str          # HIGH | MEDIUM | LOW


class EndpointReport(BaseModel):
    hostname: str
    os: Optional[str] = None
    user: Optional[str] = None
    agent_version: Optional[str] = None
    reported_at: Optional[str] = None
    findings: List[EndpointFinding] = []


class EndpointSummary(BaseModel):
    hostname: str
    os: Optional[str] = None
    user: Optional[str] = None
    reported_at: Optional[str] = None
    risk_score: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    findings: List[EndpointFinding] = []


class EndpointsResponse(BaseModel):
    count: int = 0
    endpoints: List[EndpointSummary] = []
