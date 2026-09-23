# A/K1/265 Site Facts and Evidence Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In the existing planning library, show the A/K1/265 site facts from the reviewed official snapshot and take the practitioner from each cited claim to the correct original PDF passage.

**Architecture:** A versioned, read-only sample dataset supplies source claims and unresolved questions. A folder-scoped API resolves each citation against the *actual saved PDF version* before presenting a navigation target. The existing PDF.js reader performs page and excerpt matching, then draws a temporary visible highlight only when the match is unique; story 2 will add review events and edits to the stable claim IDs.

**Tech Stack:** Python 3.11+, FastAPI, SQLite folder and run views, committed official PDFs, PDF.js 6.3.289, plain JavaScript/CSS, pytest, Node syntax checks, isolated browser smoke test.

**Spec:** `_bmad-output/specs/spec-practitioner-review/SPEC.md`, `stories.yaml` story `1`; read its `site-information.md`, `architecture.md`, `interaction.md`, `acceptance.md`, `case-ak1-265.md`, and `case-ak1-265-gaps.md` companions.

**Observed starting point:** The current local library has two A/K1/265 runs and saved P/G/M PDFs whose hashes match the frozen official sample. The plan still tests an empty or mismatched folder, since another installation may not have those originals.

## Global Constraints

- Show the 2022 application and decision claims with their actual dates and stages. The 2026-09-05 download is an acquisition date, not a 2026 land-use survey.
- Preserve the source's approximations and units: Site Area **about 5,410 m²**, non-domestic GFA **about 7,638 m²**, application PR **about 1.41**. The PR planning limit needs the applicable OZP/Notes text; it cannot be filled from the application PR.
- Record the original permission deadline **2026-10-14** separately from unknown EOT submission, publication and decision status. The roof garden is outside this application; lease assignment to FSI and LCSD management are different claims. Do not subtract roof area from the reported Site Area.
- A/K1/265 and A/K1/265-1 are distinct identities. No document hash, page, quote or highlight may be silently carried to another version or case.
- Keep originals unchanged, source selection and historical range behavior intact, and tests in an isolated data directory. Use Traditional Chinese UI copy and existing MiSans styling.
- This story supplies **read-only sample claims and navigation**. Its `已確認` markings for Site Area and original deadline reflect the user's 2026-09-23 feedback; other sample facts remain `待覆核`. Confirm/edit/remove storage is story 2.

## File ownership and data contract

| File | Responsibility |
|---|---|
| `app/site_facts.py` (create) | Load the checked-in 21-claim sample, validate IDs, source hashes and citation fields, and resolve available source versions from `Library.view`. No filesystem path leaves the API. |
| `app/sample_data/ak1_265.json` (create) | Machine-readable transcription of the 21 rows in `case-ak1-265.md`, including the 2026-09-23 user feedback and nine linked research gaps. Stable claim IDs are the future review-event keys. |
| `app/site_fact_routes.py` (create) | `GET /api/folders/{id}/site-facts` with the same `run`/`cutoff` selection rules as the folder endpoint. Return 404 for a different case or nonexistent folder. |
| `app/main.py` (modify) | Attach the route beside `attach_library_routes`; use the existing local-only boundary. |
| `web/site-facts.js` (create) | Render the seven question groups, claim metadata, citation states and source buttons; emit a navigation request without owning PDF reader state. |
| `web/reader.js` (modify) | Add a version-checked `jumpToEvidence` operation: await the requested PDF and text layer, move to the cited page, locate the unique excerpt, draw/remove a transient highlight. |
| `web/app.js`, `web/index.html`, `web/style.css` (modify) | Add a `場地資料` tab in the existing workspace, fetch claims when folder/scope changes, resolve the exact saved document version and call the reader. Preserve file switching, focus mode and saved reading position. |
| `tests/test_site_facts.py`, `tests/test_site_fact_api.py` (create) | Test sample preservation, source version binding, run/cutoff visibility, absent originals and wrong-case access. |

The API record is `{id, question, label, value, unit, time, nature, scope, stage, asserted_by, approximation, review_status, citations, issue_ids}`. Each citation is `{source_sha256, source_url, page, excerpt, context_before, context_after, availability, doc_id, source_run}`; `doc_id` and `source_run` are returned only after matching a document version visible in the selected folder scope. `availability` is one of `ready`, `missing_original`, `outside_scope`, `version_mismatch`, or `unlocatable`. The response also carries `as_of`, sample provenance and nine issues. Unknown metadata stays explicit rather than becoming zero or a blank claim of certainty.

The 21 stable IDs follow the sample rows in order: `site-address`, `lot`, `application-boundary`, `site-area`, `government-land-roof`, `actual-use-2022`, `op-use`, `applied-use`, `approved-use`, `ozp-zoning`, `planning-intention`, `gfa-nondomestic`, `pr-application`, `site-coverage`, `building-height`, `storeys-blocks`, `loading-facilities`, `application-history`, `original-expiry`, `approval-conditions`, `department-advice`. Each value and citation is transcribed from `case-ak1-265.md`; the nine issues are transcribed from `case-ak1-265-gaps.md`. Source abbreviations P/G/M/D remain provenance labels, never the version key. D is JSON: it keeps its JSON path and source link but receives no invented PDF page or highlight.

## Task 1: Freeze sample claims and resolve actual source versions

**Files:** Create `app/sample_data/ak1_265.json`, `app/site_facts.py`, `tests/test_site_facts.py`.

**Interfaces:** `load_sample() -> dict` returns the immutable sample structure; `resolve_sample(folder_view: dict) -> dict` returns a copy with citation availability and matching `doc_id`/`source_run`. Match `source_sha256` plus the source URL when present against both displayed documents and their `versions`; do not select merely by title or application-number substring.

- [ ] **Step 1: Write tests** for 21 unique IDs, seven question categories and nine issues; verify the two user-confirmed statuses, PR-as-application-versus-missing-limit distinction, the three roof relations, EOT unknown state, and P/G/M/D snapshot hashes from `case-ak1-265.md`.

  ```python
  from app.site_facts import load_sample, resolve_sample

  def test_sample_keeps_proposal_pr_separate_from_planning_limit():
      claims = {row['id']: row for row in load_sample()['claims']}
      assert len(claims) == 21
      assert claims['site-area']['review_status'] == 'user_confirmed_source_value'
      assert claims['pr-application']['value'] == '约 1.41'
      assert claims['pr-application']['nature'] == 'application_proposal'
      assert any(issue['id'] == 'ozp-notes-pr-limit' for issue in load_sample()['issues'])

  def test_missing_saved_pdf_cannot_become_navigation_target():
      view = {'case_no': 'A/K1/265', 'documents': []}
      claim = next(x for x in resolve_sample(view)['claims'] if x['id'] == 'site-area')
      assert claim['citations'][0]['availability'] == 'missing_original'
      assert claim['citations'][0]['doc_id'] is None
  ```
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_site_facts.py -q`; expect failure because `app.site_facts` does not exist.
- [ ] **Step 3: Transcribe the sample** into `app/sample_data/ak1_265.json`. Give PDF citations one-based page numbers and short verbatim excerpts plus nearby context. Keep multiple citations for a claim rather than fusing different stages. For source D use a JSON path, no PDF page. Validate that each excerpt occurs on the declared page of the frozen file; if the page text cannot support a unique match, record `unlocatable` rather than inventing coordinates.
- [ ] **Step 4: Implement `load_sample` and `resolve_sample`** as pure functions; compare exact SHA-256 first, then URL when available. A saved file with the same title but a changed hash gets `version_mismatch`; absent PDF gets `missing_original`. A citation hidden by the selected run/date gets `outside_scope`.

  ```python
  def matching_version(documents, citation):
      for display in documents:
          for version in [display, *display.get('versions', [])]:
              if (version.get('sha256') == citation['source_sha256']
                      and version.get('url') == citation['source_url']
                      and version.get('status') == 'ready'):
                  return {'doc_id': version['id'], 'source_run': version['source_run']}
      return None
  ```

  `resolve_sample` uses this exact-version match to fill navigation fields; separate checks of other visible versions and the full folder history distinguish `version_mismatch` from `outside_scope`. A failed match never receives a file URL.
- [ ] **Step 5: Rerun** `.venv/bin/python -m pytest tests/test_site_facts.py -q`; expect all checks to pass. Commit the dataset and resolver as one reviewable change.

## Task 2: Serve the sample within an existing folder scope

**Files:** Create `app/site_fact_routes.py`, `tests/test_site_fact_api.py`; modify `app/main.py`.

**Interfaces:** `attach_site_fact_routes(app, lib)` registers `GET /api/folders/{id}/site-facts?run=<run-id>` or `?cutoff=<YYYY-MM-DD>`. It calls the same `lib.view(id, run, cutoff)` scope as the document list; invalid combined selection returns 422, wrong folder or case returns 404.

- [ ] **Step 1: Write API tests** using `TestClient(create_app(tmp_path))`. Seed an A/K1/265 folder with `Store.content` and one frozen PDF as an actual saved document. Assert its citation resolves to the right `source_run` and SHA; another case gets 404, missing or mismatched versions never yield a `ready` target, and run/cutoff selection cannot expose excluded versions.

  ```python
  def test_site_facts_are_bound_to_requested_folder(client):
      lib = client.app.state.library
      run = lib.store.create('A/H7/183', '', '2026-09-23')
      run['phase'] = 'complete'
      lib.store.save(run)
      folder_id = lib.import_run(run)
      assert client.get(f'/api/folders/{folder_id}/site-facts').status_code == 404
  ```
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_site_fact_api.py -q`; expect a 404 for the absent route.
- [ ] **Step 3: Add the route** with explicit folder/case validation and return the resolver's public record. Do not copy the bundled PDFs into the user's data directory or create a new research run on GET. Existing saved originals remain the only in-app navigation targets; a missing original is visible as a gap with the official link.
- [ ] **Step 4: Rerun** both site-fact test files and `tests/test_library_api.py`; commit the API integration after they pass.

## Task 3: Render the table and navigate to source text

**Files:** Create `web/site-facts.js`; modify `web/index.html`, `web/app.js`, `web/reader.js`, `web/style.css`; add focused browser checks to the story acceptance record.

**Interfaces:** `renderSiteFacts(container, payload, onCitation)` displays claims and calls `onCitation(citation)` on activation. `Reader.jumpToEvidence({version, page, excerpt, context_before, context_after}) -> Promise<{ok:boolean, reason?:string}>` works only after opening the exact version. `web/app.js` finds a document in `p.documents` or its `versions` with matching SHA and source URL, calls the existing `selectDocument`, waits for the reader to finish, and then calls `jumpToEvidence`.

- [ ] **Step 1: Add the `場地資料` tab** and render seven question groups with value, unit, time, nature, source and review status. Show conflicts and gaps as text; keep the `文件` and `申請與決定` tabs intact. Source buttons use escaped text and keyboard focus.
- [ ] **Step 2: Add page navigation** after version verification. `Reader.jumpToEvidence` checks `this.version`, waits for the PDF load and PDF.js `textlayerrendered` for the cited page, and matches normalized excerpt plus context across text spans. A single match yields a temporary overlay from DOM `Range.getClientRects()` in the page text layer; zero/multiple matches or a scanned page return a visible reason and no overlay. Clear the overlay on document switch, page switch and new navigation; recompute its geometry after zoom or rotation. The existing `selectDocument` returns before `Reader.open` completes, so add an awaitable reader-ready promise; do not assume awaiting `selectDocument` is sufficient.

  ```js
  async function openEvidence(citation, visibleDocuments) {
    const versions = visibleDocuments.flatMap((d) => [d, ...(d.versions || [])]);
    const saved = versions.find((d) =>
      d.sha256 === citation.source_sha256 &&
      d.url === citation.source_url &&
      d.source_run === citation.source_run
    );
    if (!saved) return { ok: false, reason: '所引文件版本不在目前資料範圍' };
    await selectDocument(saved);
    await reader.whenReady(saved.sha256);
    return reader.jumpToEvidence(citation);
  }
  ```
- [ ] **Step 3: Add scope-safe UI wiring.** Refetch facts whenever the folder, run or cutoff changes; use the existing `loadToken`/document token pattern so stale network or PDF responses cannot switch the reader back. Opening evidence may change the reader's position; leaving the fact panel or switching documents must preserve the existing saved reading state.
- [ ] **Step 4: In isolated test data, inspect** `site-area` at G p.1, `pr-application` at G p.1, `original-expiry` at M p.12–13 and a multi-source roof claim at P p.2/p.4. Repeat at 75%, 100%, 150% and in focus mode. For an excerpt missing from the page, a mismatched hash, a scanned/unreadable page and a hidden historical version, verify the UI explains the failure and draws no highlight.
- [ ] **Step 5: Run** `.venv/bin/python -m pytest -q`, `node --check web/app.js`, `node --check web/site-facts.js`, `node --check web/reader.js`; inspect the app in an isolated test profile. Commit after the regression and browser checks pass.

## Story acceptance and review gate

The practitioner can open A/K1/265, read all 21 sample claims and nine explicit gaps, distinguish the reported Site Area from application PR and the missing OZP/Notes limit, and open a frozen original from each available PDF citation. The selected document's SHA, source run, page and text highlight must all agree. Any unresolved location is visibly unresolved; the original PDF and page remain accessible. Existing folder search, file versions, reading position and ZIP export still work.

This completes `stories.yaml` story 1 only. The sample remains a partly reviewed reference set; confirmation/edit/remove persistence and Kimi extraction belong to later stories. At the configured `done_checkpoint`, show the user the running A/K1/265 example and the list of citations that could not be located.

## Plan self-review

Coverage: Task 1 preserves 21 claims and issues with stable provenance; Task 2 binds citations to the current saved versions and scope; Task 3 provides the seven-question view and guarded original-text navigation. The reader highlight is based on PDF.js text-layer geometry rather than model coordinates. Existing-regression checks cover document identity, historical scope, version switching and local file access. The one unresolved implementation input is whether every sample citation can be turned into a unique quote on the frozen PDF; the plan treats non-unique or missing text as an explicit location failure.
