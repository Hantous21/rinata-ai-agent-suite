# Rinata Review Agent — n8n Automation & Approval

This describes the n8n workflow that runs the pipeline on a schedule and gates
every draft behind your approval before it is treated as "ready to post".

> **Honest scope note:** there is no Google review *posting* integration (Build 1
> scrapes; it cannot post). "Approved" means a draft lands in
> `output/approved_responses.csv` — a clean, owner-approved list you paste into
> Google Business Profile. The approval gate is real; the final paste is manual
> until/unless we move onto the Google Business Profile API.

---

## Architecture

```
Schedule Trigger (weekly)
   -> Execute Command:  python run_all.py
        |-- non-zero exit  -> Email you "PIPELINE FAILED" (stop)
        |-- success        -> continue
   -> Read output/response_drafts.csv  + output/urgent_responses.csv
   -> Keep rows where status == "Pending Review"
   -> Loop over each row:
         -> Gmail "Send and Wait for Response" (Approval: Approve / Reject)
              |-- Approved  -> append row to output/approved_responses.csv
              |-- Rejected  -> append row to output/rejected_responses.csv
   -> Summary email: "X approved, Y rejected, paste approved ones into Google"
```

The rating filter (3★ and below) is already enforced **in code**
(`generate_responses.py`, `MAX_RATING = 3`), so n8n never even sees 4–5★ reviews.

---

## Quick start: import the prebuilt workflow

A starter workflow is provided: **`docs/n8n_workflow.json`**.

1. In n8n: **Workflows → Import from File →** select `docs/n8n_workflow.json`.
2. Create a **Gmail OAuth2 credential**, then open the two Gmail nodes
   ("Send & Wait for Approval", "Alert: pipeline failed") and select it
   (placeholder is `REPLACE_WITH_GMAIL_CRED_ID`).
3. Confirm the project path in the three **Execute Command** nodes matches
   `C:\Users\shant\projects\Rinata` and that `python` resolves on the n8n host.
4. Activate. It runs Mondays 08:00, emails one Approve/Reject per pending
   review, and records each decision via `record_decision.py`.

**Honest caveats on the JSON:** it is a scaffold built to current n8n node
shapes and is **untested in your instance**. Node `typeVersion`s and the
`sendAndWait` parameter names drift between n8n releases — if a node imports
"unrecognized" or the approval boolean path differs, fix it using the
node-by-node spec below (the Python side is fully tested and stable; only the
n8n wiring may need a nudge).

---

## Node-by-node build (n8n)

1. **Schedule Trigger** — e.g. every Monday 08:00.
2. **Execute Command** — `python run_all.py` (Working Directory =
   `C:\Users\shant\projects\Rinata`). In *Settings*, turn **Continue On Fail** OFF
   so a failed pipeline routes to the error path.
   - Add an **IF** on `{{$json.exitCode}}` ≠ 0 → **Gmail: Send** "Rinata pipeline
     failed" to yourself, then stop. (This is your scraper-broke alarm.)
3. **Read/Write Files From Disk** (Read) → `output/urgent_responses.csv`, then an
   **Extract From File** (CSV) node. Do the same for `output/response_drafts.csv`.
   Merge both; urgent first.
4. **Filter** — keep items where `status` is `Pending Review`.
5. **Loop Over Items** (Split In Batches, batch size 1).
6. **Gmail → "Send and Wait for Response"**, Response Type = **Approval**
   (Approve / Disapprove buttons). Email body should include: rating, the
   original `review_text`, the `draft_response`, and the `qc_flag` if any.
   Subject for urgent rows: prefix `URGENT —`.
   n8n pauses this execution until you click.
7. **IF `{{$json.data.approved}}` is true**
   - **true** → **Code/Set** to add `status = Approved` + timestamp →
     **Read/Write Files (Append)** to `output/approved_responses.csv`.
   - **false** → append to `output/rejected_responses.csv` (optionally capture a
     reason via a second prompt).
8. After the loop: **Gmail: Send** a summary ("12 approved, 3 rejected — open
   approved_responses.csv and post the approved replies").

---

## The one genuinely tricky part: where n8n runs

`Execute Command` must be able to call this project's Python.

- **Easiest (recommended to start):** run **n8n on this Windows host** (n8n
  desktop or `npx n8n`), not in Docker. Then `python run_all.py` "just works"
  with the existing `.env` and installed packages.
- **Docker (your preference long-term):** mount the project into the n8n
  container and use a Python-capable image, OR keep n8n in Docker but have it
  trigger the pipeline on the host via SSH/webhook. This is more setup; do it
  once the host version is proven.

Start on the host, move to Docker once the flow is validated end-to-end.

---

## Volume / cost notes

- The 3★-and-below filter keeps this small: a normal week is a handful of
  reviews, not hundreds. The current backlog is **32** (16 urgent, 16 standard)
  — approve those in a first pass, then steady-state is light.
- One approval email per review. If a backlog feels heavy, approve urgent first
  and standard later; the workflow can be run in two passes.

---

## Known limitations / honest risks

- **Scraper fragility:** the weekly run depends on the Google scraper. The
  `run_all.py` sanity checks abort (exit 1) on a suspicious result so n8n alerts
  you instead of producing garbage — but a broken scraper still means no new
  reviews until fixed. The durable fix is the Google Business Profile API.
- **No auto-post:** approval produces a list; posting to Google is still manual
  and human-controlled by design.
- **Re-approval:** today every `Pending Review` row is sent each run. A small
  follow-up (have `generate_responses.py` skip reviews already in
  approved/rejected CSVs) makes reruns idempotent — flag this when you want it.
- This guide is **untested in your n8n** — node names match current n8n; adjust
  if your version differs.
