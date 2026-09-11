# Feature: Release and versioning policy

**From build-plan:** feature 2a
**Status:** verified

## Goal

Establish a documented, repeatable version and GitHub release contract for the
Home Stock Tracker HA custom integration. This gives HACS users a stable,
identifiable release stream while preserving the existing read-only runtime.

## In scope

- Adopt Semantic Versioning (`MAJOR.MINOR.PATCH`) for integration releases.
- Define `custom_components/home_stock_tracker/manifest.json` as the source of
  the installed integration version.
- Define the matching Git tag and GitHub Release naming convention, release-note
  expectations, and changelog maintenance rules.
- Record the existing `0.1.0` integration state as the first changelog entry.
- Explain the local pre-release checks that an operator performs before creating
  a GitHub Release.

## Out of scope

- Creating, publishing, or pushing a Git tag or GitHub Release.
- GitHub Actions, HACS Action, Hassfest, or any automated validation (Feature
  2b).
- Home Assistant Brands or repository brand assets (Feature 2c).
- Installation, configuration, troubleshooting, or support-guide expansion
  (Feature 2d).
- Runtime behavior, config entries, sensors, API requests, dependencies, and
  any write action to Home Stock Tracker.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan the next unchecked step before code changes.
2. Implement only that step, including its focused verification.
3. Show the diff and evidence; wait for review before the next step.
4. Create optional checkpoints only after the relevant tests pass.

## Build steps

- [x] **Step 1 - Define the version and release contract** - add `RELEASE.md`
  describing SemVer increments, `manifest.json` as the canonical installed
  version, a matching `v<version>` Git tag and GitHub Release, stable-release
  expectations, and required release-note content. *Done when:* the document
  unambiguously maps manifest version `X.Y.Z` to release tag `vX.Y.Z`, says a
  GitHub Release—not a tag alone—is published after checks succeed, and states
  which change types require MAJOR, MINOR, or PATCH increments.
- [x] **Step 2 - Establish the public change-history baseline** - add
  `CHANGELOG.md` in Keep-a-Changelog-style sections with an `Unreleased` section
  and a `0.1.0` baseline that describes the shipped read-only integration without
  secrets or invented release claims. *Done when:* future releases have a named
  place for user-visible additions, fixes, breaking changes, and upgrade notes,
  and the baseline agrees with the existing README and manifest version.
- [x] **Step 3 - Verify the release metadata and regression boundary** - check
  JSON validity and version consistency, then run the repository's Home
  Assistant test suite. *Done when:* `manifest.json` remains valid JSON with
  version `0.1.0`, the documented policy and changelog agree with that version,
  and `.venv/bin/python -m pytest -q tests` passes (or the documented
  `python3 -m pytest -q tests` fallback when `.venv` is unavailable).

## Files / areas

- `RELEASE.md` - versioning, tagging, release, and pre-release-check policy.
- `CHANGELOG.md` - user-visible release history and unreleased changes.
- `custom_components/home_stock_tracker/manifest.json` - inspected as the
  version source; change only if the approved policy reveals an invalid value.
- `README.md` - inspected for baseline consistency; no installation/support
  rewrite in this feature.
- `blueprint/context/current-feature.md` - workflow progress.

## Data / contracts

- **Load-bearing release-version contract:**

  | Surface | Required value |
  | --- | --- |
  | Installed integration version | Plain SemVer `X.Y.Z` in `manifest.json` |
  | Git tag | `vX.Y.Z`, matching the manifest exactly after the `v` prefix |
  | GitHub Release | A published release using the matching tag; a tag by itself is insufficient for HACS release selection |
  | Changelog heading | `X.Y.Z`, matching the manifest and tag version |

- The current baseline is `0.1.0` / `v0.1.0`. This feature documents it but does
  not assert that a remote release already exists.
- Version increments: before `1.0.0`, increment PATCH for fixes and MINOR for
  any user-visible capability or breaking configuration/entity contract; from
  `1.0.0` onward, increment PATCH for fixes, MINOR for backward-compatible
  capabilities, and MAJOR for breaking contracts. Release notes identify any
  required upgrade action and preserve the read-only boundary.
- The policy must not introduce tokens, URLs containing credentials, or other
  secrets into version history or release notes.

## Testing

- This feature adds documentation and release metadata policy, not runtime
  logic; no new pytest unit test is required.
- Run `.venv/bin/python -m pytest -q tests` when `.venv` exists; otherwise run
  `python3 -m pytest -q tests` after installing `requirements-test.txt` in a
  prepared environment.
- Validate `custom_components/home_stock_tracker/manifest.json` and `hacs.json`
  as JSON, and manually compare the manifest version, changelog baseline, and
  documented tag convention.
- `/check` should confirm that no GitHub release or tag was created and that
  integration tests still pass; automated HACS validation belongs to Feature 2b.

## Notes for the AI

- Keep runtime files within `custom_components/home_stock_tracker/`; this
  feature should not need to modify them.
- Preserve the integration's read-only behavior and never place API tokens in
  release notes, changelog entries, logs, attributes, diagnostics, or tests.
- Home Assistant requires custom-integration manifest versions, and accepts
  valid SemVer; HACS uses the latest published GitHub Release tag when releases
  are used. See [Home Assistant manifest documentation](https://developers.home-assistant.io/docs/creating_integration_manifest/)
  and [HACS publishing guidance](https://hacs.xyz/docs/publish/start/).
- Do not publish remotely during `/implement`; publishing is expressly outside
  this feature and requires the user's separate authorization.
