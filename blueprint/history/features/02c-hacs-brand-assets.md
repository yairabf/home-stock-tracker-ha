# Feature: HACS brand assets

**From build-plan:** feature 2c
**Status:** verified

## Goal

Give Home Stock Tracker HA an original, locally shipped brand icon so Home
Assistant can present the integration recognizably and the HACS validation
workflow can run without its temporary `brands` exemption. This changes no
runtime, service, or read-only behavior.

## Design reference

Use the established Home Stock Tracker application icon at
`../home-stock-tracker/docs/brand/home-stock-tracker-icon.png` as the source.
It shows a household outline, grocery basket, and stock indicators against its
intentional dark-green field. Preserve that artwork unchanged and ensure it
remains recognizable at small Home Assistant UI sizes.

## In scope

- One original PNG icon at the local Home Assistant brand path for the
  `home_stock_tracker` domain.
- Validation of the PNG's file type, square dimensions, and readable small-size
  rendering.
- Removal of the temporary `brands` ignore from the HACS workflow, followed by
  local regression checks and hosted HACS/Hassfest evidence after an authorized
  push.

## Out of scope

- A `dark_icon.png`, logo lockup, README social image, marketplace artwork, or
  an expanded visual identity.
- A submission to `home-assistant/brands`, HACS default-list inclusion, or any
  change to remote repository settings.
- Release, tag, dependency, HACS workflow trigger, runtime, config-flow,
  coordinator, sensor, API, or write-behavior changes.
- Installation/support documentation expansion (Feature 2d).

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan the next unchecked step before code changes.
2. Implement only that step and run its focused checks.
3. Show the diff and evidence; wait for review before the next step.
4. Create optional checkpoints only after the relevant tests pass.

## Build steps

- [x] **Step 1 - Create the local integration icon** - copy the established
  PNG at `custom_components/home_stock_tracker/brand/icon.png`
  following the design brief, with a square canvas suitable for Home Assistant
  branding. *Done when:* the file is a non-empty, square PNG copied unchanged
  from the established Home Stock Tracker icon, and a small-size inspection
  confirms the house, grocery basket, and stock indicators remain identifiable.
- [x] **Step 2 - Re-enable brands validation** - remove only `brands` from the
  HACS workflow's `ignore` setting and its adjacent temporary-exception comment.
  *Done when:* `validate.yml` retains all existing triggers, permissions,
  timeouts, jobs, and HACS inputs other than the deleted exemption; no ignored
  checks remain; and the icon is still at the domain-matching local brand path.
- [x] **Step 3 - Verify the publication boundary** - run image/metadata/workflow
  structure checks and the existing integration tests; after a separately
  authorized push, inspect the candidate branch-push workflow. *Done when:* the
  PNG and JSON files validate, `.venv/bin/python -m pytest -q tests` passes (or
  the documented Python fallback), `git diff --check` passes, and both HACS and
  Hassfest report success for the pushed candidate revision with no `brands`
  ignore. If hosted execution is not authorized or available, record that as a
  remaining verification gap rather than declaring the feature verified.

## Files / areas

- `custom_components/home_stock_tracker/brand/icon.png` - new, original local
  brand icon; this path is load-bearing because it matches the integration
  domain and is the path HACS currently checks.
- `.github/workflows/validate.yml` - remove the temporary Feature 2c brands
  exception only after the icon is present.
- `tests/` - run the existing regression suite; no runtime behavior is changed.
- `blueprint/context/current-feature.md` and `blueprint/.state/run.json` -
  workflow progress and activity.

## Data / contracts

No service API, config-entry, coordinator snapshot, sensor, or stored-data
contract changes.

**Load-bearing branding contract:**

| Surface | Required value / behavior |
| --- | --- |
| Integration domain | `home_stock_tracker` (unchanged) |
| Local asset path | `custom_components/home_stock_tracker/brand/icon.png` |
| Asset format | Non-empty, square PNG; the established source's opaque dark-green background is intentional |
| Asset content | Established Home Stock Tracker house, grocery basket, and stock-indicator mark, legible at small UI size |
| Workflow change | Delete the `brands` ignore and its Feature 2c comment; preserve every other validator setting |
| Validation evidence | Candidate branch-push HACS and Hassfest jobs both pass after the exemption is removed |

- `dark_icon.png` is intentionally not required: the supplied source icon is
  the complete brand treatment for this feature.
- Local assets satisfy the current HACS action's brands-path check; this feature
  does not claim inclusion in the separate Home Assistant Brands repository or
  HACS default list.
- Never place service URLs, API tokens, user data, or a third-party trademark in
  the asset, repository metadata, logs, or tests.

## Testing

| Check | Evidence / expected result |
| --- | --- |
| PNG integrity | Inspect `icon.png` with an available image-metadata tool; it reports PNG, square dimensions, and non-zero size. |
| Source fidelity and visual suitability | Confirm the repository icon has the same checksum as the established Home Stock Tracker source, then open it and an approximately 32 px rendition; the house, grocery basket, and stock indicators are distinguishable without clipping. |
| Workflow structure | Parse and inspect `.github/workflows/validate.yml`; HACS has no `ignore: brands` (or other ignored checks), while its category/comment inputs and all existing jobs/triggers/permissions/timeouts are unchanged. |
| Metadata | `python3 -m json.tool` succeeds for `hacs.json` and all existing integration JSON files. |
| Runtime regression | `.venv/bin/python -m pytest -q tests`; if `.venv` is unavailable, use a prepared environment with `requirements-test.txt` installed and `python3 -m pytest -q tests`. |
| Final local check | `git diff --check` passes. |
| Hosted validation | Following explicit authorization to push, both HACS and Hassfest pass for the candidate branch-push commit and logs show the brands check is enabled. |

- No browser-test command, standalone build, formatter, linter, or combined
  Verify command is configured in `AGENTS.md`; none is introduced here.
- No new pytest test is needed: this feature changes a static visual asset and
  validator configuration, not Python behavior. Direct image inspection and
  the official validators provide the focused evidence.

## Verification evidence

- The local icon is byte-identical to the approved Home Stock Tracker source:
  SHA-256 `f68fc5b2cf0963164f485a6697654d0438c5ba32993e35fbf2dde27af414b8a2`.
  It is a non-empty 1254×1254 PNG; its opaque dark-green background is part of
  the approved supplied artwork. A 32 px rendition remains identifiable.
- All HACS and integration JSON files parsed successfully. The workflow parsed
  with the HACS job inputs exactly `category: integration` and `comment: false`,
  with no `ignore` input. `git diff --check` passed.
- `.venv/bin/python -m pytest -q tests`: **11 passed** (0.83 seconds).
- Checkpoint commit `8dd550440d81a9b9e3648a9baaa1ca61f3ea0f74` was pushed to
  `feature/hacs-brand-assets`. Its branch-push [Validate run 34595193838](https://github.com/yairabf/home-stock-tracker-ha/actions/runs/34595193838)
  completed successfully: **HACS** and **Hassfest** both passed. HACS ran its
  repository validation with the brands exemption removed; Hassfest validated
  the pushed integration metadata.

## Notes for the AI

- Preserve the integration's read-only boundary and do not alter runtime files
  beyond adding the local asset under the existing integration directory.
- Copy the approved established Home Stock Tracker icon from the Design
  reference unchanged; do not regenerate, download, or adapt an asset.
- Keep the brand directory free of unrelated files. Do not add a dark variant
  or other marketing assets without a separately approved feature.
- The HACS validator previously passed only because
  `.github/workflows/validate.yml` ignores `brands`; Step 2 must remove that
  exact exemption, not add a different ignore or workaround.
- Do not push, publish, modify GitHub settings, or create a release while
  implementing this feature. Hosted workflow evidence requires separate user
  authorization.
