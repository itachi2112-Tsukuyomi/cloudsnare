"""
Tests for mapper/scoring.py — pure logic, no AWS calls needed.

Run with:
    python -m unittest tests.test_scoring -v
"""

import unittest

from mapper.scoring import score_findings, band_for


def _finding(risk, service="S3"):
    return {"id": f"{service}:x", "service": service, "risk": risk}


class TestBandFor(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(band_for(0), "CLEAR")
        self.assertEqual(band_for(1), "LOW")
        self.assertEqual(band_for(24), "LOW")
        self.assertEqual(band_for(25), "MEDIUM")
        self.assertEqual(band_for(49), "MEDIUM")
        self.assertEqual(band_for(50), "HIGH")
        self.assertEqual(band_for(74), "HIGH")
        self.assertEqual(band_for(75), "CRITICAL")
        self.assertEqual(band_for(100), "CRITICAL")


class TestScoreFindings(unittest.TestCase):
    def test_no_findings_is_clear(self):
        result = score_findings([])
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["band"], "CLEAR")

    def test_single_high_scores_and_bands_correctly(self):
        result = score_findings([_finding("HIGH")])
        self.assertEqual(result["score"], 15)
        self.assertEqual(result["band"], "LOW")

    def test_score_caps_at_100(self):
        findings = [_finding("HIGH") for _ in range(10)]  # 150 raw
        result = score_findings(findings)
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["raw"], 150)
        self.assertEqual(result["band"], "CRITICAL")

    def test_by_service_breakdown(self):
        findings = [_finding("HIGH", "S3"), _finding("MEDIUM", "EC2-SG")]
        result = score_findings(findings)
        self.assertEqual(result["by_service"], {"S3": 15, "EC2-SG": 7})

    def test_by_risk_counts(self):
        findings = [_finding("HIGH"), _finding("HIGH"), _finding("LOW")]
        result = score_findings(findings)
        self.assertEqual(result["by_risk"], {"HIGH": 2, "MEDIUM": 0, "LOW": 1})

    def test_unknown_risk_contributes_zero_weight(self):
        result = score_findings([_finding("UNKNOWN")])
        self.assertEqual(result["score"], 0)


if __name__ == "__main__":
    unittest.main()
