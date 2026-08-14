// NOTICE: This file is protected under RCF-PL
# Self-Forging: from traces to a proven-better model

Self-Forging is how AladdinAI turns its own agent traces into a specialised CRM
model. It's a three-layer loop. This guide covers what exists today and how to
use layers 2 and 3.

## The loop

```
Layer 0  Capture    every agent turn → agent_traces (tracing.py)
Layer 1  Signal     reward/quality_label: weak write-time score, overridden by human 👍/👎
Layer 2  Golden set freeze labeled traces into a fixed benchmark (golden_traces)
Layer 2b Export     render the frozen set as JSONL a trainer accepts
Layer 3  Harness    replay golden inputs through base vs forged → measure the delta
```

The doctrine that ties it together: **recording traces is not training.**
Accumulating unlabeled traces just piles ore with rock. Only a *reward* separates
good from bad, and only a *frozen benchmark* lets you prove a forged model is
better rather than merely different.

## Layer 1 — the signal (already built)

`tracing.py` writes each turn to the user's own `agent_traces` Mongo collection
with a `reward` and `quality_label`:

- **Write-time score** (`_score`) — a weak proxy from the loop's own outcome
  ("did it reach an answer without tool errors"). `reward is None` marks a trace
  *intentionally excluded* from training (infra error / blocked input).
- **Human score** (`human_score`) — a 👍/👎 on a reply overrides the weak score.
  This is the strong signal: what a person actually judged.

## Layer 2 — freeze a golden set

A golden example is `{input, expected, reward}` — a frozen input paired with the
answer we labeled good. Freezing (rather than querying live) means the benchmark
doesn't move under you as new traces arrive.

```bash
curl -X POST http://localhost:8000/api/forging/golden-set \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"min_reward": 0.5, "human_only": true, "limit": 500}'
# → { "frozen": 42, "frozen_at": "...", "human_only": true, "replaced": true }
```

- `human_only` (default `true`) — only traces with a human 👍/👎 are eligible.
  Set `false` to also admit the weak write-time score (larger set, noisier).
- Freezing is **idempotent**: it replaces the previous golden set for the user.

Inspect it: `GET /api/forging/golden-set`.

## Layer 2b — export the golden set for training

The golden set lives in Mongo; a trainer wants JSONL. This export is the step
between "we can measure a forged model" and actually having one.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/forging/golden-set/export?format=sft" \
  -o training.jsonl
```

`format` picks the schema, because NeMo Customizer detects a dataset's type from
its shape rather than from a flag:

| `format` | Line shape | Use for |
|---|---|---|
| `sft` (default) | `{"prompt", "completion"}` | supervised fine-tuning, LoRA |
| `chat` | `{"messages": [{role, content}, …]}` | models trained on a chat template |
| `dpo` | `{"prompt", "chosen_response", "rejected_response"}` | preference alignment |

Add `&system_prompt=...` to put a system turn in front of every `chat` example,
and `&download=false` to get a JSON summary instead of the file.

**DPO needs both verdicts on the same question.** A preference pair contrasts a
👍 answer with a 👎 answer *to the same input*, so prompts that were only ever
rated one way are skipped and counted in `skipped_unpaired`. An export far
smaller than the golden set is a fact about your labels, not a failure — it
means few questions have been answered both well and badly.

### Running the fine-tune

The export is deliberately the boundary: AladdinAI produces the dataset, your
GPU budget produces the model. With [NeMo Customizer][customizer] the shape is

```bash
# 1. upload training.jsonl as a dataset (training/ and optionally validation/)
# 2. create a customization job against a base model, e.g.
#      meta/llama-3.1-8b-instruct + LoRA
# 3. the job yields a model name you can serve through NIM
```

Then point the harness at it: `forged_model` = the new name, `base_model` = what
you started from. That delta is the whole reason the golden set is frozen — it
tells you whether the run was worth its cost.

[customizer]: https://docs.nvidia.com/nemo/microservices/latest/customizer/tutorials/sft-customization-job.html

## Layer 3 — run the harness

Replay every golden input through two models and score each reply against the
frozen `expected` answer. The headline is `delta = mean(forged) − mean(base)`.

```bash
curl -X POST http://localhost:8000/api/forging/harness \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
        "base_provider_id": 1, "base_model": "meta/llama-3.1-8b-instruct",
        "forged_provider_id": 2, "forged_model": "aladdin-crm-v1",
        "limit": 100
      }'
# → { "evaluated": 100, "mean_base": 0.31, "mean_forged": 0.47, "delta": 0.16, ... }
```

A positive `delta` is the evidence ADR-0001 called the "A/B base-vs-forged"
result: on your own labeled benchmark, the forged model is closer to the
answers you marked good.

### About the scorer

`score_response` is a dependency-free token-overlap (Jaccard) proxy, not a judge.
It's designed to detect **aggregate** movement across many examples — a forged
model regressing or improving — not to grade a single reply. Swapping in an
embedding-similarity or LLM-judge scorer later is a drop-in change to one pure
function.

## Editions

Forging endpoints are gated to internal/cloud editions (`ALADDIN_EDITION`). The
community self-hosted image returns `403` — it carries no forging pipeline, the
same reason trace capture defaults off there.

## Boundaries (not built yet)

Running the training job itself, scheduled re-freezing, and a UI for the harness
are out of scope. What exists is the full data path — capture → label → freeze →
**export** → measure — and the export hands off to whatever trainer you use.

The one thing no code can supply is the labels. Traces with `reward: null` are
*intentionally excluded*, not unlabeled — fine-tuning on unrated traces averages
your good and bad answers together and produces a model that is more confident,
not more correct. The 👍/👎 buttons are the input to all of this.

## See also

- [ADR-0001](../adr/0001-self-forging-training.md) — why self-forging exists
- [ADR-0009](../adr/0009-golden-set-and-harness.md) — golden set + harness design
- `app/services/forging.py`, `app/services/tracing.py`
