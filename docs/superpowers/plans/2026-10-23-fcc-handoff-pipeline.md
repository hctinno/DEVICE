# FCC Handoff and Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a complete collection request package and an executable offline FCC workflow core.

**Architecture:** A local Python service with SQLite and immutable content-addressed files. CLI and MCP use the same functions; method profiles separate verified knowledge from workflow mechanics. Reports remain drafts.

**Tech Stack:** Python 3.10+, SQLite, openpyxl, jsonschema, ReportLab, official MCP Python SDK.

**Spec:** docs/superpowers/specs/2026-10-23-fcc-handoff-pipeline-design.md

## Global Constraints

- Preserve existing equipment and regulatory artifacts.
- No live hardware writes, external filing, purchases, or invented normative limits.
- Synthetic provenance must propagate to reports; missing evidence blocks judgments.
- Public source discovery and imported bytes do not imply currentness or technical approval.
- Existing work branch and dedicated workspace remain the working location.

## Review Focus

- ZIP traversal, duplicate members, expanded-size limits, hash mismatch, and partial DB writes.
- Reused IDs with different content and repeated import requests.
- NaN/infinity, mismatched units, empty results, and cross-case references.
- Unreviewed or corrupted sources turning into PASS through alternate CLI/MCP paths.
- Search links mistaken for verified download URLs and stale KDB entries mistaken for a current exhaustive corpus.

### Task 1: Collection handoff and data contract

**Files:** `handoff/`, `tools/build_collection_request.py`, `docs/fcc/collection_handoff.md`.
**Interfaces:** Produces CSV requests, JSON Schema manifest, readable agent prompt, XLSX and ZIP. Later importer consumes manifest records with document_id, request_ids, status, source_url, path, sha256, bytes, media_type, rights, and version.

- [ ] Generate all regulatory and model requests from existing source files and database, label link verification honestly, and include recursive discovery instructions.
- [ ] Validate unique IDs, model/record coverage, Excel parity, relative links and ZIP integrity. This is data-artifact validation; prose receives no unit tests.
- [ ] Commit the new collection tooling and request contract, preserving existing untracked work.

### Task 2: Package intake and durable provenance

**Files:** `labflow/intake.py`, `labflow/store.py`, `labflow/schema.sql`, `tests/test_labflow.py`.
**Interfaces:** `Store(root: Path)`; `import_package(store: Store, path: Path) -> dict`; `store.import_artifact(path: Path, kind: str) -> str`.

- [ ] Write failing tests: valid ZIP import, repeated import, changed document ID conflict, hash mismatch, traversal, PDF disguised HTML, duplicate names, and no partial database commit.
- [ ] Run `python -m unittest discover -s tests -p test_labflow.py -v`; observe expected missing behavior.
- [ ] Implement validation, immutable blobs and SQLite records with transactions.
- [ ] Run the same tests until green and commit.

### Task 3: Cases, plans, runs and deterministic evaluation

**Files:** `labflow/workflow.py`, `labflow/calculations.py`, `tests/test_labflow.py`.
**Interfaces:** `create_case(store, data)`, `register_method(store, data)`, `add_plan(store, case_id, data)`, `record_run(store, plan_id, data, raw_path)`, `evaluate(store, run_id)`, `case_status(store, case_id)` return JSON-compatible dicts.

- [ ] Write failing tests for cross-case links, incomplete/failed runs, immutable IDs, unsupported method/scope, unit mismatch, finite-number checks, missing source/profile review, and synthetic provenance.
- [ ] Implement tested functions; use literal arithmetic fixture 30+10+2-20=22 and dBm 30→1 W. No normative FCC thresholds are supplied by production defaults.
- [ ] Run the whole unit suite and commit.

### Task 4: Reports, CLI, MCP and complete demonstration

**Files:** `labflow/reporting.py`, `labflow/__main__.py`, `labflow/mcp_server.py`, `labflow/demo.py`, `docs/fcc/pipeline_usage.md`, tests.
**Interfaces:** `render_report(store, case_id, output_dir)` returns paths; CLI and MCP wrap the same intake/workflow functions.

- [ ] Write failing end-to-end tests for DRAFT report generation, evidence links, escaped product text, corrupted evidence blocking, and a complete CLI synthetic workflow.
- [ ] Implement A4 PDF/HTML/JSON reports, CLI, SDK MCP tools and repeatable synthetic demo.
- [ ] Run all tests and demonstrate package intake→case→plan→run→calculation→report. Review capabilities and limitations in documentation.
- [ ] Commit implementation and request a fresh whole-change review; resolve material findings with regression tests and record results.
