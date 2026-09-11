# Feature: Automated HACS validation

**From build-plan:** feature 2b
**Status:** in progress
**Branch:** `feature/automated-hacs-validation`

## Goal

Add automated HACS repository validation and Home Assistant Hassfest checks so
maintainers can catch distribution and integration-metadata failures before a
release. Connect these checks to the release policy established by Feature 2a.

## In scope

- One GitHub Actions workflow with independent HACS and Hassfest jobs.
- Validation on branch pushes, pull requests, manual runs, and a weekly schedule.
- Minimal metadata corrections required by these validators, preserving the
  integration domain, current version, configuration, and entity contracts.
- A temporary HACS `brands` exception with an explicit Feature 2c handoff.
- Required repository topics: `home-assistant`, `hacs`, and `custom-integration`.
  Preserve any existing topics when applying these during implementation.
- A focused update to the pre-release checklist explaining checks and failures.

## Out of scope

- Brand artwork or publication of assets (Feature 2c); installation and support
  guide expansion (Feature 2d); submission to the HACS default repository list.
- Release creation, tags, release uploads, or automated version/changelog changes.
- Branch protection, unrelated repository settings, a general CI framework,
  dependency upgrades, or a new combined Verify, build, lint, or browser command.
- Runtime logic, service requests, config entries, sensors, and write operations
  against Home Stock Tracker.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan the next unchecked step before editing.
2. Implement only that step and run its focused checks.
3. Show the diff and evidence for review before proceeding, matching
   `blueprint/config.json` (`stepReview: every`).
4. Offer an optional checkpoint after checks pass; `/complete` creates the final
   feature commit.

The explicit `$autopilot` request permits this run to continue through passing
steps and create local checkpoints without per-step prompts. Hosted changes
and pushing remain outside that authorization.

## Build steps

- [x] **Step 1 - Add Hassfest validation** - create
  `.github/workflows/validate.yml` with the shared triggers and a Hassfest job;
  include only validator-driven metadata corrections. *Done when:* the workflow
  parses, uses the event checkout and official Hassfest action on Ubuntu, has
  read-only permissions and a finite timeout, and metadata remains valid JSON.
  Execute Hassfest locally when its container runtime is available and record
  any findings; run the existing pytest suite if integration metadata changes.
- [x] **Step 2 - Add HACS repository validation** - add the independent HACS job
  using `category: integration`, disabled PR comments, and only the temporary
  `brands` ignore. Record the exact additive topic update needed for hosted
  verification in Step 4. *Done when:* both jobs are present without a dependency on
  each other; the HACS job uses the event repository, requires no custom secret,
  and propagates validation failure; the brands exception names Feature 2c in
  an adjacent comment and the required topic update is ready for review.
- [ ] **Step 3 - Connect the release gate** - replace the future
  Feature 2b placeholder in `RELEASE.md` with the workflow/check names, run and
  failure-inspection instructions, and the temporary exception. *Done when:*
  the release checklist requires successful HACS and Hassfest checks for the
  release candidate, documents repository prerequisites and how to inspect or
  rerun failures, and the existing pytest suite and whitespace checks pass.
- [ ] **Step 4 - Verify hosted validation** - after local changes are reviewable,
  apply the additive repository-topic update and obtain workflow evidence
  through an authorized push. *Done when:* the repository has the required
  topics and both hosted jobs pass with evidence recording the run URL and
  checked revision. Keep this step unchecked while hosted verification is
  pending; local success alone is insufficient.

## Files / areas

- `.github/workflows/validate.yml` - new validation workflow.
- `RELEASE.md` - existing pre-release checklist and concise validation guidance.
- `hacs.json`, `custom_components/home_stock_tracker/manifest.json`,
  `custom_components/home_stock_tracker/strings.json`, and
  `custom_components/home_stock_tracker/translations/en.json` - inspect;
  change only when a validator identifies a concrete metadata problem.
- GitHub repository topics for `yairabf/home-stock-tracker-ha` - the narrowly
  scoped hosted prerequisite; no topic removal.
- `tests/` - existing regression suite; update only if a necessary metadata
  correction changes an asserted contract.
- `blueprint/context/current-feature.md` and `blueprint/.state/run.json` -
  workflow progress and activity.

## Data / contracts

No service API, stored config-entry, or sensor-data contract changes.

**Load-bearing workflow contract:**

| Surface | Required behavior |
| --- | --- |
| Workflow | `.github/workflows/validate.yml`, display name `Validate` |
| Triggers | All branch pushes (`push.branches: ["**"]`), normal `pull_request`, `workflow_dispatch`, and weekly Monday `17 4 * * 1` (04:17 UTC) |
| Hassfest job | ID `hassfest`, name `Hassfest`; `actions/checkout@v7` with `persist-credentials: false`, followed by `home-assistant/actions/hassfest@master` |
| HACS job | ID `hacs`, name `HACS`; `hacs/action@main` with `category: integration`, `comment: "false"`, and `ignore: brands`; no checkout or hardcoded repository override |
| Runtime | Both jobs use `ubuntu-latest` and `timeout-minutes: 15` |
| Permissions | Workflow defaults to `permissions: {}`; Hassfest grants only `contents: read` for checkout; HACS uses its default automatic GitHub token without write permissions |
| Failure | Both validators run independently; no `continue-on-error`, unconditional success fallback, or additional ignored checks |
| Release contract | Preserve `manifest.json` version `0.1.0`, domain `home_stock_tracker`, and the `X.Y.Z` / `vX.Y.Z` policy from Feature 2a |

- HACS reads repository content through GitHub. Checkout changes alone do not
  change the revision it validates. Preserve its normal push/PR event selection.
- For the release gate, require a successful branch-push run for the candidate
  commit and check the source/ref reported by both validators. HACS PR runs
  target the contributor branch while Hassfest checks GitHub's event checkout.
  Scheduled/manual HACS runs can target the latest published release (or the
  default branch when there are no releases); do not use such a run to assert
  validation of an unreleased candidate. Document this distinction in
  `RELEASE.md`. The weekly run is a maintenance signal, not candidate evidence.
- `brands` is the sole temporary exception because artwork belongs to Feature
  2c. That feature must remove the ignore after accepted assets satisfy the
  validator. A passing run with this exception does not establish eligibility
  for HACS default-list inclusion.
- Upstream validator branch references intentionally follow the official
  examples. The weekly run detects changed requirements; this feature does not
  promise a frozen validator environment or introduce an action-update bot.
- Never supply a Home Stock Tracker API token, personal access token, or live
  service URL to validation jobs. Use neither `pull_request_target` nor PR
  comments, write permissions, or workflow publication steps.

## Testing

| Check | Evidence / expected result |
| --- | --- |
| Workflow structure | Parse as GitHub Actions-compatible YAML and inspect triggers, action inputs, independent jobs, permissions, timeout, and the sole ignore; avoid a YAML 1.1 parser treating `on` as a boolean |
| Metadata | `python3 -m json.tool` succeeds for `hacs.json` and any integration JSON files touched; validator-driven changes preserve existing identity/version values |
| Hassfest | Run the official Hassfest container against the candidate checkout if Docker is available; record validator output and exit status |
| HACS | After an authorized push, inspect a real HACS run for category, checked source, enabled checks, sole brands exception, and pass/fail outcome |
| Candidate identity | Match the release candidate to a successful branch-push run and the refs actually selected by both validators; do not substitute a scheduled/manual run of an older release |
| Repository prerequisites | Confirm public/unarchived repository, nonempty description/topics, and enabled issues; expose failures without adding ignores |
| Runtime regression | `.venv/bin/python -m pytest -q tests`; if `.venv` is unavailable, use a prepared environment with `requirements-test.txt` installed and `python3 -m pytest -q tests` |
| Release instructions | Confirm `RELEASE.md` identifies both job names, explains where failures appear and how to rerun after correction, and prohibits release on failed checks |
| Final local check | `git diff --check` passes |

- No new runtime logic or custom validation script is planned, so do not add
  pytest tests that merely mirror workflow YAML. The official validators check
  their respective schemas; the existing suite guards runtime behavior.
- No browser-test command, standalone build, formatter, linter, or combined
  Verify command is configured in `AGENTS.md`. None is introduced by this spec.
- Local parsing and pytest cannot prove hosted workflow execution. If GitHub
  Actions is unavailable or publication has not been authorized, complete the
  local work and record the hosted validation gap explicitly; do not report a
  green hosted check or verified feature without evidence.
- Missing/malformed metadata, repository-check failures, rate limits, and
  validator download/execution failures must remain visible failures. Correct
  the input or retry an infrastructure failure; never add an ignore or convert
  the result to success to finish the feature. No deliberate failing commits
  or repository-setting regressions are required just to test upstream actions.

## Verification evidence

- 2026-09-11, Step 1: parsed workflow YAML with PyYAML `BaseLoader` so `on`
  remains a string; inspected triggers, job permissions, timeout, and checkout.
  All four repository/integration JSON files parsed successfully.
- The official Hassfest image, digest
  `sha256:d0f082cb684c7560666138e501cdbe36137927acb075e276729728179108651d`,
  passed against a read-only mount of this checkout: `Integrations: 1`,
  `Invalid integrations: 0`, exit 0. Command:
  `docker run --rm --mount type=bind,source=/Users/yairabramovitch/Documents/workspace/home-stock-tracker-ha,target=/github/workspace,readonly ghcr.io/home-assistant/hassfest`.
  No integration metadata corrections were needed.
- `.venv/bin/python -m pytest -q tests`: **11 passed** (0.52 seconds).
  `git diff --check`: passed.
- Step 2: parsed and reviewed the complete workflow. HACS and Hassfest have no
  `needs` dependency; HACS inherits empty permissions, uses `comment: "false"`,
  and ignores only `brands` with a Feature 2c removal comment. No result is
  suppressed. Hosted HACS execution remains pending Step 4.
- Refreshed the overview from the unchanged plans after detecting its stale
  source fingerprint. Split the last build step into local release documentation
  and hosted verification without removing any acceptance criteria.
- Hosted topic update prepared for Step 4: add `home-assistant`, `hacs`, and
  `custom-integration` to `yairabf/home-stock-tracker-ha`, preserving all current
  topics. Exact additive command, to run only with external-action authorization:

  ```bash
  gh repo edit yairabf/home-stock-tracker-ha --add-topic home-assistant --add-topic hacs --add-topic custom-integration
  ```

  No hosted repository settings have been changed by this Autopilot run.

## Notes for the AI

- This is repository automation; Home Assistant remains the runtime host.
  There is no new application client or server code.
- Keep runtime files inside `custom_components/home_stock_tracker/` and retain
  HACS' root layout. Preserve unavailable-state behavior and credential secrecy.
- Planning inspection found no `.github/` directory. The public repository has
  a description and enabled issues but no topics as of 2026-09-11. Topics are a
  required prerequisite, not grounds for ignoring the check.
- `RELEASE.md` and the archived Feature 2a spec resolve the overview's stale
  release-policy TODO. Use that established policy without changing the plans.
- Keep the hosted topic update explicit in the implementation review. Prepare
  local changes before any approval needed for external actions. Do not create
  releases, tags, or outbound comments as part of validation.
- Source references checked for this spec:
  [HACS workflow and ignore documentation](https://hacs.xyz/docs/publish/action/),
  [HACS action inputs](https://github.com/hacs/action/blob/main/action.yml),
  [HACS repository requirements](https://hacs.xyz/docs/publish/start/),
  [HACS default-list requirements](https://hacs.xyz/docs/publish/include/),
  [Hassfest guidance](https://developers.home-assistant.io/blog/2020/04/16/hassfest/),
  [Hassfest action](https://github.com/home-assistant/actions/blob/master/hassfest/action.yml),
  and [checkout usage](https://github.com/actions/checkout).
