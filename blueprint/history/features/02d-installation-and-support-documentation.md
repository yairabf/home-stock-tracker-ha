# Feature: Installation and support documentation

**From build-plan:** feature 2d
**Status:** verified

## Goal

Make the repository self-serve for a Home Assistant administrator: explain the
supported installation and configuration path, the integration's observable
behavior and limits, and how to troubleshoot or report a problem without
sharing credentials or household data. This is a documentation-only release
readiness feature.

## In scope

- Expand the public README with prerequisites, HACS custom-repository
  installation, configuration, the three entities, polling and unavailable
  behavior, and clear read-only/security expectations.
- Add concise troubleshooting and support coverage for invalid service URLs,
  connectivity failures, rejected/expired tokens and reauthentication,
  unavailable entities, duplicate configuration, and safe issue reporting.
- Cross-link the release policy, issue tracker, and Apache-2.0 license using
  stable repository-relative or existing public URLs.
- Check every documentation claim against the current config flow, coordinator,
  sensors, manifest, and release policy.

## Out of scope

- Runtime, config-flow, coordinator, sensor, manifest, API, test-harness, CI,
  HACS workflow, or release/tag changes.
- New support channels, issue templates, automated diagnostics, telemetry, or
  a compatibility promise for a particular Home Assistant or service version.
- Manual/non-HACS installation instructions, write actions, token-generation
  instructions, and service-side setup outside this repository.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan the next unchecked step before code changes.
2. Implement only that step and run its focused checks.
3. Show the diff and evidence; wait for review before the next step.
4. Create optional checkpoints only after the relevant checks pass.

## Build steps

- [x] **Step 1 — Document installation, configuration, and behavior** — revise
  `README.md` into a clear HACS setup guide with prerequisites; retain the
  exact custom-repository URL/category and configuration flow; state the
  accepted service-origin form, three entity IDs/attributes, five-minute
  polling, unavailable-state behavior, and read-only `GET` boundary. *Done
  when:* a first-time administrator can follow the README from HACS to the
  integration form without guessing; every factual behavior statement matches
  the current runtime; and no example contains a real token or credentialed URL.
- [x] **Step 2 — Document recovery, support, and release references** — add
  troubleshooting and support guidance to the README, including known
  config-flow errors and reauthentication, a minimum safe issue report,
  explicit secrets/data exclusions, and links to the issue tracker, release
  policy, and license. *Done when:* each listed failure has an actionable next
  step; the issue guidance never asks for an API token, authorization header,
  credentialed URL, or source-record contents; and all Markdown links resolve
  to their intended existing targets.
- [x] **Step 3 — Verify documentation against the shipped contract** — inspect
  the final Markdown and compare it with relevant source and metadata; run the
  existing Python regression suite. *Done when:* Markdown is readable, links
  and code literals are accurate, `python3 -m json.tool
  custom_components/home_stock_tracker/manifest.json` succeeds,
  `.venv/bin/python -m pytest -q tests` passes (or the documented prepared
  environment fallback passes), and `git diff --check` passes.

## Files / areas

- `README.md` — primary installation, behavior, troubleshooting, and support
  guide; the only planned content change.
- `RELEASE.md`, `LICENSE`, `custom_components/home_stock_tracker/manifest.json`,
  `config_flow.py`, `coordinator.py`, `sensor.py`, and `const.py` — read-only
  sources of truth for documentation claims and links.
- `tests/` — existing regression suite only; no production behavior changes
  require new pytest cases.
- `blueprint/context/current-feature.md` and `blueprint/.state/run.json` —
  feature progress and dashboard activity.

## Data / contracts

No runtime or stored-data contracts change. The documentation must preserve
these load-bearing public contracts:

| Surface | Required documentation contract |
| --- | --- |
| Installation | HACS custom repository `https://github.com/yairabf/home-stock-tracker-ha`, category `Integration`, then restart Home Assistant and add **Home Stock Tracker** through Devices & services. |
| Configuration | A service URL must be an HTTP(S) origin without a path, query, or fragment; it and the bearer token are validated against the authenticated grocery endpoint. |
| Config entry | Only one integration configuration is allowed; a base URL already configured is rejected rather than creating a second entry. |
| Recovery | A rejected token triggers Home Assistant reauthentication, which requests a replacement token while retaining the configured URL. |
| Entities | `sensor.pending_groceries` exposes `items`; `sensor.tracked_inventory` exposes `current` and `uncertain`; `sensor.low_stock_recommendations` exposes `recommendations`. |
| Freshness/failure | Polling occurs every five minutes. Empty valid results are `0`; authentication, connectivity, non-success, and invalid-payload failures make entities unavailable rather than presenting stale data as current. |
| Security/read-only | The integration makes authenticated `GET` requests only. Tokens, authorization headers, credentialed URLs, and source-record contents must not appear in examples or issue-report requests. |

## Testing

| Check | Evidence / expected result |
| --- | --- |
| Documentation/source comparison | Inspect the README alongside config flow, constants, coordinator, sensors, manifest, and `RELEASE.md`; every user-facing statement agrees with shipped code and policy. |
| Link and secret review | Verify local links target existing files and public issue/repository links are correct; search examples and support text for token/header/credentialed-URL or source-record requests. |
| Metadata sanity | `python3 -m json.tool custom_components/home_stock_tracker/manifest.json` exits successfully. |
| Runtime regression | `.venv/bin/python -m pytest -q tests`; if `.venv` is unavailable, use a prepared environment with `requirements-test.txt` and run `python3 -m pytest -q tests`. |
| Final local check | `git diff --check` passes. |

- No browser-test command, standalone build, formatter, linter, or combined
  Verify command is configured in `AGENTS.md`; none is introduced here.
- No new pytest test is planned because the feature changes documentation only;
  direct content/link review plus the existing regression suite are the
  proportionate evidence.

## Notes for the AI

- Keep this a documentation-only feature. Do not alter runtime files, metadata,
  workflow configuration, or the existing product plan.
- Match Home Assistant's visible labels and the integration's actual behavior;
  do not invent manual installation, service compatibility, diagnostics, or
  support channels.
- State operational assumptions carefully: the service must be reachable from
  Home Assistant, and `localhost` is appropriate only when both share a network
  namespace.
- Do not document private endpoints, API request payloads, raw record samples,
  token-generation procedures, or any workaround that weakens the read-only or
  secret-handling boundary.
- Keep the README scannable. Link to `RELEASE.md` rather than duplicating its
  versioning and publication procedure.
