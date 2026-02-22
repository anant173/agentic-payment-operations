# Development Challenge: Mastercard Payment Operations Agent

## Problem Statement

Payment Operations and Risk teams investigate transaction issues, monitor merchant performance, manage fraud exposure, and escalate operational incidents daily.

These workflows require analysts to:

- Diagnose why transactions were approved or declined  
- Assess fraud indicators and authentication signals  
- Monitor merchants against chargeback and network thresholds  
- Detect operational anomalies such as decline spikes  
- Retrieve internal remediation playbooks  
- Escalate structured updates to Slack  
- Ensure PCI-safe communication at all times  

Much of this process is manual, tool-heavy, and audit-sensitive.

This challenge is to build a **production-ready conversational agent** that performs these responsibilities using a structured demo dataset — replicating how a Payment Operations Specialist or Network Compliance Advisor would operate in a real enterprise environment.

The focus is not on building a chatbot that “sounds intelligent.”  
The focus is on building an agent that solves structured payment operations problems **correctly, deterministically, and auditable end-to-end.**

---

## Goal

Build a production-ready conversational agent that:

- Diagnoses transaction issues  
- Evaluates fraud signals and merchant monitoring criteria (demo-only)  
- Retrieves internal playbook guidance (policy-backed, not model-generated)  
- Escalates to Slack when required  
- Uses tool-first reasoning  
- Produces observable traces for auditability  

The agent must operate with enterprise discipline:

- Deterministic facts from tools only  
- Policy-backed remediation only  
- Structured, audit-friendly responses  
- Correct Slack channel routing  

---

## Included Demo Data

- `merchants.json`  
- `transactions.json`  
- `chargebacks.json`  
- `policies_kb.json`  
- `tool_schemas.json`  

These datasets simulate:

- Monitoring thresholds  
- Decline patterns (05, 91 spikes)  
- High-risk merchants with weak authentication signals  
- Chargeback early warning scenarios  
- Internal remediation playbooks  

---

## Implemented MCP Tools

The agent must use these tools:

1. `list_transactions`  
2. `list_transactions_last_48h`  
3. `pick_representative_transaction`  
4. `analyze_transaction`  
5. `check_merchant_compliance`  
6. `lookup_internal_policy`  
7. `slack_get_conversations`  
8. `slack_send_message`  
9. `web_search` (context only — never for internal policy or thresholds)  