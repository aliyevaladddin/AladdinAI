---
title: "Your Code Is Being Eaten. RCF Is the Lock."
seoTitle: "Restricted Correlation Framework "
seoDescription: "RCF Protocol — A licensing framework protecting proprietary methodologies from automated extraction and AI/ML training."
datePublished: 2026-05-27T13:55:05.100Z
cuid: cmpo4m2o9004q2hme3f41ex9d
slug: your-code-is-being-eaten-rcf-is-the-lock
cover: https://cdn.hashnode.com/uploads/covers/6a15086f7d85e6a1af2aeb8c/24e81bf3-7a96-46e2-9cd8-9ad5c555b4e4.jpg
tags: security, license, protection, protocols, protected-routes, software-licensing

---

*How the Restricted Correlation Framework protects sovereign codebases from unauthorized AI extraction*

There's a quiet arms race happening right now, and most developers don't know they're losing it.

Every time you push a public repo, open a PR, paste code into an AI chat, or work in an IDE with a telemetry-enabled assistant, you're feeding a machine. The code you wrote at 2am — the clever algorithm, the custom protocol, the novel data structure — becomes training data. It gets absorbed into a model that then competes with you, or the company that paid you to write it.

This isn't a hypothetical. It's the default state of the internet in 2026.

The **Restricted Correlation Framework (RCF)** is a cryptographic and legal protocol built into Aurora Access (dOS) to close this gap. This post breaks down exactly how it works and why the problem it solves is deeper than most people realize.

* * *

## The Problem Is Architectural, Not Ethical

Let's set aside the ethics debate for a moment. Whether AI training on public code is "fair" is a different argument. The engineering problem is this:

**There is currently no technical mechanism to prove that your code was used to train a model, or to prevent it.**

Copyright law gives you ownership of original code. Licenses like GPL, MIT, or Apache tell others what they can do with it. But none of these mechanisms have any effect on a crawler that simply reads your repository and feeds it into a training pipeline. You can't sue a gradient descent step.

The gap is between **legal ownership** and **technical enforceability**.

This is the gap RCF is designed to close.

* * *

## What RCF Actually Is

RCF stands for **Restricted Correlation Framework**. At its core, it's a multi-modal protocol that binds three things together:

1.  **Cryptographic identity** — who wrote this code, when, and in what context
    
2.  **Semantic fingerprinting** — a tamper-evident representation of what the code does
    
3.  **Usage restrictions** — machine-readable rules about what transformations (including AI training) are permitted
    

These three components are not separate files or metadata. They are **soldered into the logic block itself** at the time of creation, signed with the author's RCF key, and verifiable by any node running an RCF-compliant tool.

Here's the anatomy of an RCF-protected block:

```plaintext
             
                  RCF Logic Block v1.3 
     
│ Header          │ SHA-256 of source + timestamp     │
│ Author ID       │ Dilithium2 public key fingerprint │
│ Semantic Hash   │ AST-derived structural signature  │
│ Restriction Map │ Encoded usage policy bitmap       │
│ Signature       │ Dilithium2 signature over above   │

```

The signature uses **Dilithium2** — the NIST-standardized post-quantum lattice signature scheme — not RSA or ECDSA. The reason is deliberate: a protection mechanism built on classically-vulnerable cryptography is a protection mechanism with an expiration date. Quantum computers will break RSA. They won't break Dilithium2.

* * *

## The Three Enforcement Layers

RCF isn't one thing. It's a stack.

### Layer 1: Cryptographic Auditability

Every RCF-protected block carries a verifiable chain of custody. The SHA-256 hash covers the source content plus a timestamp and author key fingerprint. The Dilithium2 signature proves this specific person signed this specific content at this specific time.

This does two things:

*   **Non-repudiation**: you can prove authorship without trusting a centralized registry
    
*   **Tamper detection**: any modification to the code invalidates the signature, making silent extraction detectable if the consumer is RCF-aware
    

The `rcf-cli audit` tool verifies this chain:

```bash
$ rcf-cli audit --file src/pi_transducer.c

[RCF] Block: pi_transduce_bpm
[RCF] Author: aladdin:dilithium2:3f9a...
[RCF] Signed: 2026-04-12T03:17:44Z
[RCF] Hash: sha256:8b3c2d...
[RCF] Restrictions: NO_AI_TRAINING | NO_DERIVATIVE_EXTRACTION
[RCF] Status: ✓ VALID
```

### Layer 2: Semantic Fingerprinting

Cryptographic hashes are brittle. Rename a variable, reformat the code, translate it to another language — the hash changes completely, but the algorithm is the same. This is how naive extraction works: take code, transform it slightly, re-publish it, defeat the hash check.

RCF's semantic fingerprint operates on the **Abstract Syntax Tree (AST)**, not the raw text. It captures structural relationships between operations: the control flow graph, the dependency chain between computations, the signature of the algorithm as a mathematical object.

Two functions that are textually different but algorithmically identical will produce the same semantic fingerprint. This makes obfuscation-based extraction significantly harder — you have to change what the code *does*, not just what it *looks like*.

```plaintext
Source code → Parser → AST → Canonical form → Hash
                                ↑
                    (variable names stripped,
                     whitespace normalized,
                     comment-free structural encoding)
```

The semantic hash is separate from the content hash in the RCF block. An auditor can check both: content integrity (was this specific file modified?) and semantic integrity (was this algorithm extracted, even in disguised form?).

### Layer 3: Restriction Map

The restriction map is a compact bitmap encoding what operations on this code are permitted or prohibited. Current fields in RCF v1.3.0:

| Bit | Restriction | Effect |
| --- | --- | --- |
| 0 | `NO_AI_TRAINING` | Block cannot be used as AI training data |
| 1 | `NO_DERIVATIVE_EXTRACTION` | AST-derived representations are restricted |
| 2 | `AUDIT_REQUIRED` | Any consumer must produce an audit log |
| 3 | `RCF_CHAIN_REQUIRED` | Derivatives must carry RCF blocks |
| 4 | `SOVEREIGN_ONLY` | Restricted to RCF-compliant execution environments |

These restrictions are **machine-readable**. An RCF-compliant pipeline — a CI system, an IDE plugin, a training data curator — can read this map and enforce it programmatically, without human review.

The key word is *compliant*. RCF cannot stop a bad actor who ignores it. But it can:

*   Make violations **detectable** (the audit trail exists)
    
*   Make compliance **verifiable** (the signature proves what was allowed)
    
*   Create **legal standing** (you can prove what the restriction said, when it was set, and that it was ignored)
    

This shifts the enforcement burden from technical impossibility to legal accountability — which is how most IP protection actually works in practice.

* * *

## Why Dilithium2 Specifically

The choice of signature algorithm matters more here than in most contexts.

RCF is meant to protect code that may exist for **decades**. A protection scheme that's broken by quantum computers in 2030 provides zero long-term protection — it just means your code was "protected" until it wasn't.

Dilithium2 is a lattice-based scheme standardized by NIST in 2024. Its security assumption is the hardness of the Module Learning With Errors (MLWE) problem, which has no known quantum algorithm that breaks it efficiently. Shor's algorithm — the one that breaks RSA and ECC — doesn't apply.

The tradeoff is key size: Dilithium2 public keys are 1312 bytes vs 32 bytes for Ed25519. For a signing protocol where keys are embedded in code blocks, this is acceptable. The security properties are not.

Benchmark on Apple M2, 10,000 iterations:

| Algorithm | Sign | Verify | Key Size | Quantum-Safe |
| --- | --- | --- | --- | --- |
| Dilithium2 | 1.2ms | 0.4ms | 1312B | ✓ |
| RSA-3072 | 4.5ms | 0.2ms | 384B | ✗ |
| Ed25519 | 0.4ms | 1.1ms | 32B | ✗ |

Dilithium2 signs faster than RSA and verifies faster than Ed25519. The size cost is real but the performance story is clean.

* * *

## What RCF Doesn't Do

Honest accounting matters. RCF is not a DRM system and doesn't claim to be.

**It cannot prevent reading.** If your code is public, it can be read. RCF operates on what happens *after* reading — it creates a verifiable record of what restrictions were declared.

**It cannot stop non-compliant actors.** A training pipeline that deliberately ignores RCF blocks will still ingest your code. RCF makes this a documented violation, not an impossible one.

**It cannot retrofit the past.** Code that was ingested before RCF protection was applied is already gone. RCF is forward-looking.

**It is not a substitute for access control.** Private repositories with proper authentication are still the strongest protection for truly sensitive code. RCF operates in the space *after* you've decided to publish.

What RCF does: it closes the accountability gap. It creates a technically verifiable, cryptographically signed record that says *these restrictions existed, at this time, for this code*. That's the foundation everything else can build on.

* * *

## The Bigger Picture: Sovereign Codebases

RCF is one component of a larger architecture — the Aurora Access dOS philosophy of **Digital Sovereignty**.

The premise is that as AI systems become more capable and more aggressive about data collection, developers who care about ownership need technical tools that match the threat. Licenses and terms of service are not enough. You need cryptographic proof, machine-readable restrictions, and post-quantum durability.

RCF is the enforcement layer. The C-Core kernel, the Sovereign VFS, and Pure Intelligence are the execution environment. Together they form a system where the user's digital will is encoded into the infrastructure itself — not assumed by policy, but enforced by math.

The full RCF specification is in [ARCHITECTURE.md](https://github.com/aladdin-aliyev/aurora-access). The `rcf-cli` toolchain is available for any codebase, independent of the Aurora kernel.

* * *

## Getting Started with RCF

To apply RCF protection to any codebase:

```bash
# Install rcf-cli
pip install rcf-cli

# Generate your Dilithium2 keypair
rcf-cli keygen --algo dilithium2 --out ~/.rcf/keys

# Sign a file
rcf-cli sign src/my_algorithm.c \
  --key ~/.rcf/keys/private.key \
  --restrict NO_AI_TRAINING,AUDIT_REQUIRED

# Audit a file
rcf-cli audit src/my_algorithm.c

# Verify the full repo
rcf-cli audit --recursive ./src
```

The signed block is embedded as a structured comment in the source file — no separate sidecar files, no external registry, no central authority. The proof travels with the code.

* * *

*Aurora Access is an open architecture project. The RCF specification is documented in* [*ARCHITECTURE.md*](https://github.com/aladdin-aliyev/aurora-access)*. Contributions to the RCF toolchain are welcome — see* [*CONTRIBUTING.md*](https://github.com/aladdin-aliyev/aurora-access/blob/main/CONTRIBUTING.md)*.*

*Built by Aladdin Aliyev. Sovereignty is not a feature — it's a right.*