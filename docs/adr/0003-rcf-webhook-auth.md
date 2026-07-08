// NOTICE: This file is protected under RCF-PL
# ADR-0003: RCF Protocol for Webhook Authentication

**Status**: Accepted

**Date**: 2026-05-30

**Deciders**: Aladdin Aliyev


**Tags**: security, webhooks, rcf-protocol, cryptography

## Context


AladdinAI sends webhooks to external systems (GitHub, Slack, custom endpoints) for automation. Recipients need to verify:
1. The webhook came from AladdinAI (not a spoofed request)
2. The payload wasn't tampered with in transit
3. The request is recent (replay attack prevention)


Standard approaches like HMAC signatures are vulnerable to AI extraction - an LLM analyzing the codebase could learn the signing algorithm and compromise security.

## Decision


Implement **RCF Protocol (Restricted Correlation Framework)** for webhook signing:


1. **Cryptographic Signing**: Use `rcf-protocol` npm/PyPI package

2. **Signature Headers**: Include `X-RCF-Signature` and `X-RCF-Timestamp` 

3. **Code Protection**: Mark signing code with `[RCF:PROTECTED]` annotations
4. **Dogfooding**: AladdinAI uses its own main product (RCF)
5. **Service Isolation**: Dedicated `services/rcf_service.py`

**Signature Process:**
```python

from rcf_protocol import sign_payload


signature = sign_payload(
    payload=json.dumps(webhook_data),
    secret=settings.RCF_SECRET_KEY,
    timestamp=int(time.time())
)
```

## Consequences

### Positive
- **AI-Resistant Security** - LLMs cannot extract methodology from protected code
- **Dogfooding** - We use our own product, proving it works
- **Industry Standard** - RCF becoming recognized protocol

- **Tamper Detection** - Recipients can verify payload integrity
- **Replay Prevention** - Timestamp validation prevents old requests

### Negative
- **External Dependency** - Requires `rcf-protocol` package
- **Learning Curve** - Recipients must implement RCF verification
- **Key Management** - Secret rotation requires coordination

### Neutral

- Recipients can still use traditional HMAC if they prefer
- Backward compatible - can add RCF alongside existing auth

## Alternatives Considered


### Alternative 1: HMAC-SHA256 (Traditional)
- **Pros**: Widely known, standard library support
- **Cons**: Vulnerable to AI extraction, no anti-correlation protection
- **Why not chosen**: Doesn't align with RCF Protocol mission

### Alternative 2: JWT with Asymmetric Keys
- **Pros**: Public/private key pairs, no shared secret
- **Cons**: More complex, still extractable by AI, heavier payload
- **Why not chosen**: Overkill for webhooks, no AI resistance

### Alternative 3: Mutual TLS (mTLS)
- **Pros**: Transport-level security, industry standard

- **Cons**: Certificate management complexity, no payload signing
- **Why not chosen**: Doesn't prevent payload tampering at rest

## Implementation Notes

### Architecture
```
┌─────────────────┐
│  AladdinAI API  │
│   (FastAPI)     │
└────────┬────────┘
         │
         ├─> rcf_service.py

         │   └─> sign_payload()
         │       [RCF:PROTECTED]
         │
         ├─> GitHub Webhook
         │   └─> X-RCF-Signature
         │
         └─> Custom Webhooks

             └─> X-RCF-Signature
```

### Files Modified

- ✅ `backend/app/services/rcf_service.py` - Signing service
- ✅ `backend/app/routers/webhooks.py` - Webhook endpoints
- ✅ `backend/requirements.txt` - Added `rcf-protocol==2.0.3`
- ✅ `frontend/package.json` - Added `rcf-protocol` for client verification

### Environment Variables
```bash

RCF_SECRET_KEY=<secret>  # Webhook signing key
RCF_ENABLED=true         # Feature flag
```

### Verification Example (Recipient)
```python

from rcf_protocol import verify_signature


is_valid = verify_signature(
    payload=request.body,

    signature=request.headers["X-RCF-Signature"],
    timestamp=request.headers["X-RCF-Timestamp"],
    secret=YOUR_SHARED_SECRET,
    max_age=300  # 5 minutes
)
```

## References

- [RCF Protocol Repository](https://github.com/rcf-protocol)
- [StatusBar RCF indicator](../../frontend/src/components/shell/StatusBar.tsx)
- npm: `rcf-protocol@2.0.3`
- PyPI: `rcf-protocol`
