# Security Lab — future connected update

The security lab will be external to the normal officer UI.

Planned controlled tests against KAIRO infrastructure owned by the team:
- insider modification of a test document
- authenticated but unauthorized document access
- unauthenticated API request
- replay/forged request where the final API design supports it

The attacker client must make real requests to the real KAIRO backend. KAIRO must generate and persist the resulting security event. No print-only fake attack scripts.
