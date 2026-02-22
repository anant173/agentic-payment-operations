# Scripted Demo Prompts (Mapped to Dummy Data + Enforced Tool Flow)

> The agent must follow TOOL-FIRST reasoning and escalate via Slack when required.

---

## Scenario A — Simple Approval (Baseline)

**User:**  
"Can you check transaction T10001 and summarize what happened?"

### Expected Tool Path
1. `analyze_transaction(transaction_id="T10001")`

### Expected Outcome
- Transaction approved.
- Low risk band.
- No escalation required.
- Structured investigation response returned.

---

## Scenario B — Straightforward Issuer Decline

**User:**  
"Why was T10005 declined? What should I tell the customer?"

### Expected Tool Path
1. `analyze_transaction(transaction_id="T10005")`
2. `lookup_internal_policy(query="customer messaging for issuer declines", context={...})`

### Expected Outcome
- Deterministic explanation of issuer decline (e.g., code 51 — Insufficient Funds).
- Policy-backed customer communication guidance.
- No escalation required.

---

## Scenario C — Merchant Monitoring Risk (Chargeback Threshold)

**User:**  
"Is TravelNow (M200) at risk of any monitoring criteria? What should we do?"

### Expected Tool Path
1. `check_merchant_compliance(merchant_id="M200")`
2. `lookup_internal_policy(query="chargeback remediation playbook", context={"merchant_id":"M200","verdict":<returned_verdict>})`
3. `slack_send_message(channel="#payments-ops-demo", text=<structured_summary>)`  
   *(Mandatory if verdict is EarlyWarning or higher.)*

### Expected Outcome
- Monitoring verdict clearly stated.
- Policy-backed remediation steps.
- Escalation posted to **#payments-ops-demo** if EarlyWarning or higher.

---

## Scenario D — Decline Spike (Operational Incident)

**User:**  
"ElectroHub (M400) suddenly has many declines since yesterday. Investigate and escalate if needed."

### Expected Tool Path
1. `list_transactions_last_48h(merchant_id="M400")`
2. `check_merchant_compliance(merchant_id="M400")`
3. `pick_representative_transaction(merchant_id="M400", window_hours=48)`
4. `analyze_transaction(transaction_id=<selected_txn_id>)`
5. `lookup_internal_policy(query="decline spike 05/91", context={"merchant_id":"M400"})`
6. `slack_send_message(channel="#payments-ops-demo", text=<concise_incident_summary>)`

### Expected Outcome
- Identification of decline spike (e.g., 05 / 91 pattern).
- Operational interpretation (issuer/switch/acquirer routing issue).
- Escalation posted to **#payments-ops-demo**.

---

## Scenario E — High-Risk Merchant + Weak Authentication Signals

**User:**  
"DigitalKeys (M500) seems risky. Use the last 24h transactions, pick a representative high-risk txn, and use internal policy/runbook to recommend next steps."

### Expected Tool Path (Mandatory Order)
1. `list_transactions_last_48h(merchant_id="M500")`
2. `check_merchant_compliance(merchant_id="M500")`
3. `pick_representative_transaction(merchant_id="M500", window_hours=48)`
4. `analyze_transaction(transaction_id=<selected_txn_id>)`
5. `lookup_internal_policy(query="3DS step-up authentication", context={"merchant_id":"M500","risk_score":<value>})`
6. `slack_send_message(channel="#risk-approvals-demo", text=<structured_high_risk_summary>)`

### Escalation Rule
Escalation to **#risk-approvals-demo** is mandatory when:
- `risk_band` is High OR `risk_score ≥ 0.80`
- AND authentication signals are weak (3DS FAILED / NOT_ENROLLED, AVS=N/U, CVV=N/U)

### Expected Outcome
- Representative high-risk transaction identified (e.g., T50009).
- Deterministic risk analysis returned.
- Policy-backed step-up authentication recommendation.
- Escalation posted to **#risk-approvals-demo**.

---

# Enforcement Summary

- Deterministic facts must come only from tools.
- Remediation guidance must come from `lookup_internal_policy`.
- Escalation must use `slack_send_message`.
- Channel routing must follow risk vs operational rules.
- Responses must be structured, audit-friendly, and enterprise-toned.