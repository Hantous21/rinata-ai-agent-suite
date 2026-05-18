# Rinata Restaurant AI Agent Suite

A multi-build AI agent system designed and deployed for a real operating restaurant (Rinata, South Minneapolis). Each build targets a specific manual workflow, replacing hours of weekly labor with an automated, auditable pipeline.

**Governing principle:** deterministic Python does the work; Claude handles only the judgment calls that require language understanding.

---

## Builds Shipped

| Build | Workflow | Status |
|---|---|---|
| 1–2 | Google Reviews analysis | ✅ Complete |
| 3–4 | Supplier email triage | ✅ Complete |
| 5–6 | Vendor invoice reconciliation | ✅ Complete |

**Total estimated labor recovered:** 6–10 hours/week

---

## Build 1–2: Google Reviews Analysis

Scrapes Google Reviews, cleans and categorizes every review using Claude, and produces a structured Excel analysis workbook.

**Output:** Multi-sheet workbook with sentiment trends, top themes, and staff mentions.

**Why it matters:** Restaurant managers spend hours manually reading reviews to spot patterns. This delivers a structured summary in minutes — surfacing what actually needs to be acted on.

```
Google Reviews API → scraper.py → Claude (categorization) → Excel workbook
```

---

## Build 3–4: Supplier Email Triage

Connects to the restaurant's Gmail via the Gmail API, fetches all supplier emails, and classifies each one into five categories: **invoice**, **delivery**, **price change**, **dispute**, or **other**. Flags urgent items. Outputs a color-coded Excel triage workbook.

**Output:** `Rinata_Email_Triage.xlsx` — every supplier email categorized, urgent items surfaced, invoice amounts extracted where available.

**Why it matters:** The owner was spending significant time every week triaging supplier emails manually. This reduces it to a 5-minute review of the output file.

```
Gmail API → fetch_emails.py → Claude Haiku (classification) → color-coded Excel triage
```

---

## Build 5–6: Vendor Invoice Reconciliation

Parses vendor invoice PDFs, extracts line items using Claude, matches them against a master price list, and flags discrepancies.

**Output:** Exception report highlighting price variances, quantity mismatches, and unrecognized line items.

**Why it matters:** Manual invoice checking is slow and error-prone. Overcharges get missed. This catches them automatically on every delivery.

```
Invoice PDFs → pdf_parser.py → Claude (line-item extraction) → price list matching → exception report
```

---

## Architecture

```
Rinata/
├── scraper/              ← Build 1: Google Reviews scraper
├── categorizer/          ← Build 2: Review categorization
├── email_triage/         ← Builds 3–4: Supplier email triage
│   ├── gmail_auth.py     ← One-time OAuth setup
│   ├── fetch_emails.py   ← Gmail API fetcher
│   └── categorize_emails.py  ← Claude Haiku classifier
├── agent/                ← Builds 5–6: Invoice reconciliation
│   ├── build_n8n_workflow.py
│   ├── google_auth_setup.py
│   └── reauth_google.py
├── prompts/              ← System prompts for each Claude task
├── output/               ← Generated artifacts (git-ignored)
├── docs/                 ← Build guides and phase plans
├── run_all.py            ← Single-entrypoint orchestrator
└── Deliverables/         ← HTML/PDF project summaries and reports
```

---

## Tech Stack

- **Python** — orchestration, data processing, API integration
- **Claude API** (`claude-haiku-4-5`) — classification and extraction
- **Gmail API** — supplier email access
- **Google Sheets API** — data output and reporting
- **pandas / openpyxl** — Excel workbook generation
- **OAuth 2.0** — Google Workspace authentication
- **n8n** — workflow scheduling

---

## Design Principles

1. **Accuracy over speed** — this is financial and operational data. Every AI output is validated before writing.
2. **Idempotent** — re-running the pipeline never double-processes or duplicates output.
3. **Auditable** — every classification and extraction is logged with a timestamp and the reason.
4. **Human-in-the-loop** — all outputs are reports for review. Nothing is auto-posted or auto-sent.
5. **Cost-efficient** — Claude Haiku keeps API costs under $1 per full pipeline run.

---

## Context

This project serves a dual purpose:

1. **Operational** — eliminates real manual work at a real business the owner has a stake in.
2. **Proof of concept** — the workflows built here (email triage, invoice reconciliation, document extraction) directly map to the surety bond, funds-control, and construction-finance industry workflows described in [`business-plan.md`](business-plan.md). Every sales demo starts here.

---

## Contact

**Sammi Hantous** — AI Automation Consultant | Finance Operations  
[hantous93@gmail.com](mailto:hantous93@gmail.com) · [calendly.com/hantous93](https://calendly.com/hantous93)
