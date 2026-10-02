# Compliance and Legal Verification Record

This document records the legal and policy compliance gate required before automated scheduled runs may be executed by the KBM Tender Monitoring Agent.

---

## 1. Compliance Rule (Brief Section 3.6)
> **Compliance Gate**: Before the first scheduled production run, the product owner must confirm in writing (recorded in `docs/COMPLIANCE.md`) that KBM's portal subscriptions permit automated retrieval. Until then, the agent may only run manually with a human present.

---

## 2. In-Scope Portals & Subscription Verification

| Portal ID | Portal Name | Subscription / Account Type | Terms / robots.txt Status | Written Confirmation Received? | Confirmation Date | Confirmed By |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `capt` | Central Agency for Public Tenders (`https://capt.gov.kw/ar/`) | KBM Registered Corporate Account | Bot detection active for unauthenticated requests. Authenticated portal session. | [ ] Pending / [ ] Confirmed | YYYY-MM-DD | Product Owner |
| `kuwait_alyawm` | Kuwait Al-Yawm Official Gazette (`https://kuwaitalyawm.media.gov.kw/`) | KBM Paid Gazette Subscription | `robots.txt` disallows automated crawling. Requires subscription authorization. | [ ] Pending / [ ] Confirmed | YYYY-MM-DD | Product Owner |

---

## 3. Product Owner Sign-Off

I, **Khaled Abed** (Digital Solutions Lead, Khorafi Business Machines, Kuwait), confirm the following for KBM Tender Monitoring Agent:

- [ ] KBM holds valid authorized access/subscriptions to the portals listed above.
- [ ] KBM's subscription agreements and company policies permit automated retrieval of tender notices for internal presales and sales purposes.
- [ ] The agent is configured strictly in accordance with non-negotiable rules: read-only actions, polite sequential access (3–8s delays), no challenge circumvention, and session conflict avoidance.

**Signed:** ______________________________________  
**Date:** ________________________________________  
**Status:** `GATE_PENDING` (Agent restricted to human-present manual runs only)

---

## 4. Operational Guardrails

1. **Read-Only Behaviour**: No form submissions other than login. No purchasing, bidding, or setting modifications.
2. **Polite Access**: Sequential requests only; 1 session per portal; 3–8s random delay; max pages capped per run.
3. **Challenge Handling**: Immediate halt on CAPTCHA / OTP / 2FA. Never bypass or solve.
4. **Session Collision**: Immediate logout on collision or completion. No forcing out of concurrent user sessions.
