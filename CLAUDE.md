# CLAUDE.md — High-Throughput Document Barcode Engine
**Project Scope (Field Guide)**: App Development  
**Master Briefing Reference**: `/home/aria/projects/CLAUDE_PRIME.md`  
**Temporal Baseline**: October 2026 ($1 USD = 280,000 Tomans)  
**Operator**: Ariya Sarrafzadeh (HaroSS)

---

## 01 / STANDING BRIEF (PROJECT INSTRUCTIONS)
* **Outcome**: High-throughput barcode detection, orientation correction, and payload extraction service for multi-page documents.
* **Audience**: Enterprise document processing and logistics automation.
* **References**: requirements.txt, scanner/, tests/
* **Style**: OpenCV, ZBar/ZXing, FastAPI, Dockerized microservice.
* **Done means**: pytest passes, sample skewed barcode PDF decoded with 100% accuracy.
* **Missing inputs**: Provide sample corrupted/skewed test PDF before asserting scanner accuracy.
* **Ask before**: Altering decoding engine thresholds.
* **Coordination**: Run automated test suite after each modification.

---

## 02 / STRICT OPERATIONAL GUARDRAILS (ZERO EXCEPTIONS)
1. **Strict ADHD Versioning (Never Overwrite)**:
   - Never overwrite existing working files, layouts, or build scripts in place.
   - Increment explicitly: `name_v1.ext` -> `name_v2.ext`.
2. **Minimal Code Discipline (YAGNI)**:
   - Shortest correct diff. No unsolicited refactors, no speculative abstractions, no added dependencies without prompt.
3. **Evidence Before Assertion**:
   - Never declare that code works or passes without running verification commands and observing clean output.
   - Verification command for this project: `pytest`.
4. **DEAD INITIATIVE BAN (n8n is DEAD)**:
   - n8n is completely ABANDONED. Never propose, discuss, build, or reference n8n workflows.
5. **Zero Plaintext Secrets**:
   - Never commit, push, or log credentials, private keys, or API tokens.

---

## 03 / RUNNING THE WORK (STEERING TOOLKIT)
- `PLAN FIRST`: Outline tasks and wait for operator approval before touching code.
- `START NOW`: Begin work using the stated scope immediately.
- `LIMIT PARALLEL WORK`: Favor at most two active threads.
- `REDUCE UPDATES`: Report completed work and blockers only.
- `CHECK STATUS`: List active threads, their results, and next steps.
- `KEEP IT SIMPLE`: Solve directly in the active thread; avoid spawning unnecessary subprocesses.
- `CONTINUE THE RIGHT TASK`: Reuse the existing thread for direct follow-ups.
- `REVIEW BEFORE CHANGES`: Describe proposed diffs before applying edits.
