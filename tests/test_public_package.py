#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_public_package", ROOT / "scripts" / "validate_public_package.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PublicPackageContractTest(unittest.TestCase):
    def test_public_package_validates(self):
        validator = load_validator()
        result = validator.validate_package(ROOT)
        self.assertTrue(result["ok"], result.get("errors"))
        summary = result["summary"]
        self.assertFalse(summary["payment_flow"])
        self.assertFalse(summary["real_data_used"])
        self.assertFalse(summary["owner_company_identity_used"])
        self.assertFalse(summary["unsupported_claims"])
        self.assertEqual(summary["true_paid_reputable_outcomes"], 0)

    def test_readme_has_public_proof_boundaries(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        for marker in [
            "synthetic examples only",
            "no real customer, company, user, or product data",
            "no payment, invoice, refund, support, or money flow",
            "not legal, tax, compliance, procurement, security, certification, or regulatory advice",
            "no guaranteed outcomes",
            "validation question",
        ]:
            self.assertIn(marker, text)

    def test_validator_rejects_unsafe_claims(self):
        validator = load_validator()
        unsafe = "We guarantee ROI and security compliance. Pay by invoice and send client logs."
        errors = validator.scan_text_for_risky_claims("unsafe.md", unsafe.lower())
        self.assertGreaterEqual(len(errors), 4)

    def test_docs_are_static_no_runtime_surface(self):
        text = (ROOT / "docs" / "index.html").read_text(encoding="utf-8").lower()
        for forbidden in ["<form", "fetch(", "xmlhttprequest", "websocket", "localstorage", "sessionstorage", "stripe", "paypal", "checkout", "analytics", "cookie"]:
            self.assertNotIn(forbidden, text)
        self.assertIn("synthetic examples only", text)
        self.assertIn("no payment", text)


if __name__ == "__main__":
    unittest.main()
