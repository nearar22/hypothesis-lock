# HypothesisLock

HypothesisLock is a standalone GenLayer Intelligent Contract that freezes a research preregistration before a final report exists, then produces a consensus-derived deviation matrix across five fixed methodological dimensions.

The primitive addresses outcome switching and selective reporting without pretending that an LLM can prove whether a scientific conclusion is true. It answers a narrower, auditable question: did the report preserve what was preregistered, and were material changes explicitly disclosed?

## Fixed comparison matrix

Every evaluation covers exactly, and in order:

1. `HYPOTHESIS`
2. `PRIMARY_OUTCOME`
3. `POPULATION`
4. `EXCLUSIONS`
5. `ANALYSIS_WINDOW`

Each dimension is classified as `MATCH`, `DISCLOSED_CHANGE`, `UNDISCLOSED_CHANGE`, or `UNVERIFIABLE`. Contract code derives the consequence:

- all `MATCH` -> `ALIGNED / TRUSTED`
- any disclosed change, with no worse state -> `DISCLOSED_DEVIATION / QUALIFIED`
- any undisclosed change -> `SELECTIVE_REPORTING / BLOCKED`
- missing comparison data, with no undisclosed change -> `INCONCLUSIVE / BLOCKED`

## Why decentralized judgment is necessary

Research protocols and reports often describe the same concept with different wording. Byte comparison cannot distinguish harmless wording changes from a substituted endpoint, narrowed population, hidden exclusion, or extended analysis window. GenLayer validators compare the same complete frozen documents, while the contract restricts their output to a small canonical matrix and derives the trust gate deterministically.

## Lifecycle

1. `create_study(...)`
2. `freeze_preregistration(study_id)`
3. `submit_report(study_id, report_url, deviation_notice)`
4. `freeze_report(study_id)`
5. `evaluate_report(study_id)`

The preregistration body and digest are immutable before a report URL can be submitted. Evaluation is terminal: there is no owner-controlled revision, appeal, or silent overwrite path.

## Security boundaries

- Public HTTPS documents only.
- Complete bodies are bounded to 10,000 normalized characters.
- Only the study owner may attach a final report.
- The report must be a distinct document URL.
- Both bodies receive SHA-256 receipts and are stored in one comparison snapshot.
- The five consensus fields are schema-checked and order-enforced.
- Missing information can never produce a trusted result.
- The contract audits reporting alignment; it does not establish scientific truth, ethical approval, or causal validity.

## Tests

```bash
pytest -q
```

The suite covers immutable preregistration, authorization, lifecycle order, distinct report binding, complete ordered output, outcome switching, disclosed deviations, missing evidence, terminal state, receipts, and trust-gate consequences.

## Demonstration fixtures

The two files in `docs/` contain an explicit undisclosed switch from “complete applications within 7 days” to “applications started within 14 days.” They are repository-controlled fixtures for reproducibility, not real research evidence.

## Studio Next

- RPC: `https://studio-next.genlayer.com/api`
- Chain ID: `61997`
- Explorer: `https://explorer-studio-dev.genlayer.com/`

Verified deployment:

- Contract: [`0x8eb5BE1491EAAD0C3A9F33cB1DE555177b4E9234`](https://explorer-studio-dev.genlayer.com/address/0x8eb5BE1491EAAD0C3A9F33cB1DE555177b4E9234)
- Deployment transaction: [`0x67ed8a...22dc`](https://explorer-studio-dev.genlayer.com/tx/0x67ed8ae890c455c0e1218cd9fe4c4b09508f71534b6c0a56babed8aca5b122dc)
- Live study: `hypothesis-lock-mvbdv1x5`
- Live result: `SELECTIVE_REPORTING / BLOCKED`; `PRIMARY_OUTCOME` was classified `UNDISCLOSED_CHANGE`
- Local and deployed source SHA-256: `d35565c232e00d60a707085314f6f90495c8a4d2731a02ef6113e3bc3242bcc0`

Every transaction hash and the machine-readable result are recorded in `deployment.json`.

