"""Payments data models for Mastercard Payment Operations Agent (demo)."""

from __future__ import annotations

import json
import os
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from traceloop.sdk.decorators import task
from pydantic.warnings import PydanticDeprecatedSince20
warnings.filterwarnings(
    "ignore",
    category=PydanticDeprecatedSince20)


def _parse_dt(value: str) -> datetime:
    # ISO 8601 with timezone (as generated in the dummy data)
    return datetime.fromisoformat(value)


class MerchantProfile(BaseModel):
    merchant_id: str
    merchant_name: str
    mcc: str
    region: str
    avg_ticket_size: float
    monthly_volume: float
    chargeback_ratio: float
    monitoring_program_status: str
    risk_segment: str
    onboarding_date: str
    processor: str
    integration: Dict[str, Any] = Field(default_factory=dict)
    primary_contact: Dict[str, Any] = Field(default_factory=dict)


class Transaction(BaseModel):
    transaction_id: str
    merchant_id: str
    amount: float
    currency: str
    timestamp: str  # ISO string
    status: str  # "approved" | "declined"
    decline_code: Optional[str] = None
    decline_reason: Optional[str] = None
    avs_result: Optional[str] = None
    cvv_result: Optional[str] = None
    three_ds_result: Optional[str] = None
    risk_score: float
    issuer_country: str
    channel: str
    card_token: Optional[str] = None
    masked_pan: Optional[str] = None
    note: Optional[str] = None


class Chargeback(BaseModel):
    chargeback_id: str
    merchant_id: str
    transaction_id: str
    reason_code: str
    amount: float
    currency: str
    received_date: str  # ISO string
    status: str  # open/won/lost/etc.


class PaymentsPolicyKB(BaseModel):
    version: str
    monitoring_program: Dict[str, Any]
    fraud_risk_bands: Dict[str, Any]
    decline_code_guidance: Dict[str, Any]
    kb_snippets: List[Dict[str, Any]]
    pci_hygiene: Dict[str, Any]
    escalation: Dict[str, Any]


class PaymentsData(BaseModel):
    """In-memory demo datastore + deterministic business logic."""

    merchants: List[MerchantProfile]
    transactions: List[Transaction]
    chargebacks: List[Chargeback]
    policies: PaymentsPolicyKB

    @classmethod
    def load_from_dir(cls, data_dir: str | Path) -> "PaymentsData":
        data_dir = Path(data_dir)
        merchants = json.loads((data_dir / "merchants.json").read_text(encoding="utf-8"))
        transactions = json.loads((data_dir / "transactions.json").read_text(encoding="utf-8"))
        chargebacks = json.loads((data_dir / "chargebacks.json").read_text(encoding="utf-8"))
        policies = json.loads((data_dir / "policies_kb.json").read_text(encoding="utf-8"))

        return cls(
            merchants=[MerchantProfile(**m) for m in merchants],
            transactions=[Transaction(**t) for t in transactions],
            chargebacks=[Chargeback(**c) for c in chargebacks],
            policies=PaymentsPolicyKB(**policies),
        )

    # ---------- Lookup helpers ----------

    @task()
    async def get_merchant(self, merchant_id: str) -> MerchantProfile:
        for m in self.merchants:
            if m.merchant_id.lower() == merchant_id.lower():
                return m
        raise ValueError(f"Merchant '{merchant_id}' not found.")

    @task()
    async def get_transaction(self, transaction_id: str) -> Transaction:
        for t in self.transactions:
            if t.transaction_id.lower() == transaction_id.lower():
                return t
        raise ValueError(f"Transaction '{transaction_id}' not found.")

    @task()
    async def list_transactions(
        self,
        merchant_id: str,
        start_time: str,
        end_time: str,
        status: Optional[str] = None,
        decline_code: Optional[str] = None,
    ) -> List[Transaction]:
        start_dt = _parse_dt(start_time)
        end_dt = _parse_dt(end_time)

        out: List[Transaction] = []
        for t in self.transactions:
            if t.merchant_id.lower() != merchant_id.lower():
                continue
            ts = _parse_dt(t.timestamp)
            if not (start_dt <= ts <= end_dt):
                continue
            if status and t.status != status:
                continue
            if decline_code and t.decline_code != decline_code:
                continue
            out.append(t)

        # sort most recent first
        out.sort(key=lambda x: _parse_dt(x.timestamp), reverse=True)
        return out

    # ---------- Deterministic business logic ----------

    def _risk_band(self, risk_score: float) -> str:
        bands = self.policies.fraud_risk_bands
        if risk_score < float(bands["low"]["max_exclusive"]):
            return bands["low"]["label"]
        if float(bands["medium"]["min_inclusive"]) <= risk_score < float(bands["medium"]["max_exclusive"]):
            return bands["medium"]["label"]
        return bands["high"]["label"]

    def _monitoring_verdict(self, chargeback_ratio: float) -> str:
        mp = self.policies.monitoring_program
        if chargeback_ratio >= float(mp["monitoring_threshold"]):
            return "Monitoring"
        if chargeback_ratio >= float(mp["approaching_threshold"]):
            return "Approaching"
        if chargeback_ratio >= float(mp["early_warning_threshold"]):
            return "EarlyWarning"
        return "Healthy"

    @task()
    async def evaluate_transaction(self, transaction_id: str) -> Dict[str, Any]:
        t = await self.get_transaction(transaction_id)
        band = self._risk_band(t.risk_score)

        signals: List[str] = []
        if t.status == "declined":
            signals.append(f"Declined: {t.decline_code or 'UNKNOWN'} ({t.decline_reason or 'No reason provided'})")
        if t.three_ds_result in ("FAILED", None) and t.channel == "ecom":
            signals.append("Weak/absent 3DS signal for e-commerce")
        if t.avs_result in ("N", "U", None):
            signals.append("AVS not strong")
        if t.cvv_result in ("N", "U", None):
            signals.append("CVV not strong")
        if t.risk_score >= 0.80:
            signals.append("High risk score")

        next_actions: List[str] = []
        if band == "High":
            next_actions.append("Recommend step-up authentication (3DS) and additional screening for similar transactions.")
        if t.status == "declined" and t.decline_code:
            guidance = self.policies.decline_code_guidance.get(t.decline_code)
            if guidance and guidance.get("general_guidance"):
                next_actions.extend(guidance["general_guidance"])

        if not next_actions:
            next_actions.append("No immediate action required based on current signals.")

        return {
            "transaction": t.model_dump(),
            "risk_band": band,
            "signals": signals,
            "next_actions": next_actions,
        }

    @task()
    async def check_merchant_compliance(self, merchant_id: str) -> Dict[str, Any]:
        m = await self.get_merchant(merchant_id)
        verdict = self._monitoring_verdict(m.chargeback_ratio)

        # Choose remediation snippet based on MCC / risk segment (demo heuristic)
        recs: List[str] = []

        def add_snip(snip_id: str):
            for snip in self.policies.kb_snippets:
                if snip.get("id") == snip_id:
                    recs.extend(snip.get("content", []))

        # Travel MCC (4722) -> chargeback remediation playbook
        if m.mcc == "4722":
            add_snip("KB-CHARGEBACK-REMEDIATION")

        # Digital goods / high-risk segments -> 3DS step-up guidance
        elif m.risk_segment in ("High",) or m.mcc in ("5815", "5816"):
            add_snip("KB-3DS-STEPUP")

        # Default
        else:
            add_snip("KB-CHARGEBACK-REMEDIATION")

        if not recs:
            recs = ["Review fraud controls and customer support workflows."]

        thresholds = {
            "early_warning_threshold": self.policies.monitoring_program["early_warning_threshold"],
            "approaching_threshold": self.policies.monitoring_program["approaching_threshold"],
            "monitoring_threshold": self.policies.monitoring_program["monitoring_threshold"],
        }

        return {
            "merchant_id": m.merchant_id,
            "chargeback_ratio": m.chargeback_ratio,
            "thresholds": thresholds,
            "verdict": verdict
            }

    @task()
    async def lookup_internal_policy(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        q = query.lower().strip()
        hits: List[Dict[str, Any]] = []

        # simple tag/title/content matching
        for snip in self.policies.kb_snippets:
            hay = " ".join(
                [
                    snip.get("id", ""),
                    snip.get("title", ""),
                    " ".join(snip.get("tags", []) or []),
                    " ".join(snip.get("content", []) or []),
                ]
            ).lower()
            if q in hay or any(tok in hay for tok in q.split()):
                hits.append(snip)

        return {
            "results": hits[:5],
            "source": f"internal-demo-kb:{self.policies.version}",
            "context_used": context or {},
        }


def load_payments_store() -> PaymentsData:
    """
    Load demo data from a directory.

    Configure via env var:
      PAYMENT_DEMO_DATA_DIR=/path/to/mastercard_agent_demo_data
    Default:
      ./mastercard_agent_demo_data (relative to project root)
    """
    env_dir = os.getenv("PAYMENT_DEMO_DATA_DIR")
    if env_dir:
        return PaymentsData.load_from_dir(env_dir)

    # default: look for a sibling folder
    # If your service runs from repo root, place dataset at ./mastercard_agent_demo_data
    default_dir = Path(os.getcwd()) / "mastercard_agent_demo_data"
    if default_dir.exists():
        return PaymentsData.load_from_dir(default_dir)

    # fallback: allow running from within src/ or other working dirs
    alt_dir = Path(__file__).resolve().parents[2] / "mastercard_agent_demo_data"
    if alt_dir.exists():
        return PaymentsData.load_from_dir(alt_dir)

    raise FileNotFoundError(
        "Demo data not found. Set PAYMENT_DEMO_DATA_DIR to the dataset folder "
        "containing merchants.json, transactions.json, chargebacks.json, policies_kb.json."
    )