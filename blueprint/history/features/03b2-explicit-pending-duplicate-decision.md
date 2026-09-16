# Feature: Explicit pending-duplicate decision

**From build-plan:** feature 3b2
**Status:** verified

## Goal

Let a Home Assistant user explicitly choose to create a separate pending grocery
line after a duplicate result. The integration must make exactly one confirmed
request with the source service's `create_separate` policy, and refresh its
coordinator only after that request confirms creation.

## In scope

- Add one dedicated, opt-in Home Assistant service for the only supported
  pending-duplicate choice: create a separate grocery line.
- Require explicit local confirmation and validate the product name and optional
  requested quantity, unit, and note before network access.
- Make one authenticated request through the existing coordinator using the
  exact source duplicate-decision contract.
- Fail closed for unresolved product, authentication, connection, HTTP, payload,
  and unknown-outcome failures; never retry an uncertain write.
- Refresh coordinator data only after a confirmed `created` result.
- Add focused pytest coverage and a README Developer Tools example.

## Out of scope

- Incrementing, merging into, setting, removing, purchasing, or otherwise
  changing an existing pending grocery line; quantity mutations remain feature
  3c.
- Automatically deciding after `confirmation_required`, reusing a stale result,
  or making a write from polling, a sensor, or an automation.
- Catalog search, new-product creation, alias creation, or accepting proposal
  data; these are owned by 3b1.
- Any change to the paired Home Stock Tracker service or its API.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan mode lays out the step before any code.
2. The AI implements just that step.
3. It shows the diff (not full files); you read it and understand it.
4. You approve, then choose whether to commit a checkpoint or roll straight on.
   Checkpoints are optional; `/complete` makes the real feature-level commit at
   the end.

Never accept a step you have not read. If a diff is too big to review, the step
was too big, so split it.

## Build steps

- [x] **Step 1 - Define and register the confirmed duplicate-decision service**
  - add its constant, `voluptuous` schema, lifecycle registration/unregistration,
  and thin handler routing. *Done when:* the new service requires `confirm:
  true` and a trimmed non-empty `product_name`; optional quantity is positive
  and finite and optional `unit`/`note` are trimmed non-empty strings; invalid
  input is rejected before transport and a valid call routes only to the sole
  configured coordinator.

- [x] **Step 2 - Send the one fail-closed duplicate-decision request** - add a
  coordinator-owned helper that translates validated fields to the source JSON,
  validates only permitted outcomes, and preserves the one-request/no-retry
  rule. *Done when:* pytest proves the exact POST path, authorization-safe
  request body, and one POST per invocation; 401, transport failure, non-2xx,
  malformed JSON, or an unknown outcome expose no source body or token and
  leave coordinator data unavailable; known non-created outcomes produce a safe
  service error without a refresh or secondary write.

- [x] **Step 3 - Refresh only a confirmed creation and document the deliberate
  flow** - connect the created outcome to exactly one coordinator refresh and
  document the Developer Tools call and safety boundary. *Done when:* pytest
  proves `created` refreshes once while every non-created result performs no
  refresh or follow-up write, and README tells users to call this service only
  after reviewing a duplicate result and choosing an additional line.

## Files / areas

- `custom_components/home_stock_tracker/const.py` - duplicate-decision service
  constant and, if needed, a local policy constant.
- `custom_components/home_stock_tracker/services.py` - schema and thin service
  handler.
- `custom_components/home_stock_tracker/__init__.py` - config-entry-scoped
  service registration and final-unload cleanup.
- `custom_components/home_stock_tracker/coordinator.py` - shared authenticated
  duplicate-decision transport, strict result validation, and failure handling.
- `tests/test_services.py` and `tests/test_coordinator.py` - input, routing,
  source-contract, outcome, and failure coverage.
- `README.md` - explicit duplicate-decision example and no-merge safety note.

## Data / contracts

**Load-bearing Home Assistant service**

| Service | Required input | Optional input | Behavior |
| --- | --- | --- | --- |
| `home_stock_tracker.confirm_grocery_duplicate_as_separate` | `confirm: true`; trimmed non-empty `product_name` | positive finite `requested_quantity`; trimmed non-empty `unit`; trimmed non-empty `note` | Creates one intentional additional pending line, never alters an existing line. |

`confirm` is local-only and must not be sent upstream. The service does not
accept a grocery-item ID, an expected quantity, a merge action, a generic
duplicate-policy value, product facts, proposal state, or a caller-controlled
source. Its intentionally narrow name and schema make `create_separate` a
separate user decision rather than a relaxed default on `add_grocery_item`.

**Confirmed source request**

```json
POST /api/v1/grocery/items
{
  "unknownProductPolicy": "propose_if_missing",
  "productName": "3% Milk",
  "groceryItem": {
    "ifPendingExists": "create_separate",
    "requestedQuantity": 2,
    "unit": "cartons",
    "note": "for the children"
  }
}
```

`requestedQuantity`, `unit`, and `note` are omitted from `groceryItem` when the
corresponding service input is absent; `ifPendingExists: "create_separate"` is
always present. This follows the paired service's existing policy-aware add
contract. It is not a relative quantity request: omitted quantity means the
new line's normal source default, never an increment to an existing line.

A valid response has the existing policy-aware grocery-result envelope and an
outcome of `created`, `confirmation_required`, or
`product_resolution_required`. Only `created` means the separate line was
confirmed and requests one refresh. `confirmation_required` and
`product_resolution_required` are final, non-mutating outcomes for this
invocation: raise a non-sensitive Home Assistant error and perform no refresh,
retry, or fallback. HTTP 401, transport failure, non-2xx, malformed JSON, and
unknown outcomes are likewise final; do not expose raw records, error bodies,
authorization headers, or tokens.

## Testing

- Run `.venv/bin/python -m pytest -q tests` when `.venv` exists; otherwise run
  `python3 -m pytest -q tests` after installing `requirements-test.txt`.
- Add schema and routing tests for required confirmation, blank/non-string name,
  invalid quantity, blank optional strings, sole-entry routing, and no
  transport for rejected input.
- Add coordinator tests asserting the exact one-POST URL and JSON, omission of
  absent optional fields, forced `propose_if_missing` and `create_separate`, and
  no caller-controlled policy or source fields.
- Cover `created`, `confirmation_required`, and
  `product_resolution_required`, plus 401, non-success, malformed JSON, and
  connection failures. Assert exactly one request with no retry, safe error
  handling, no refresh for known non-created outcomes, and unavailable
  coordinator data for transport/authentication/payload failures.
- Add service tests proving only `created` calls `async_request_refresh` once;
  all other outcomes make no refresh or secondary write.
- Manual Home Assistant check: first call the normal add or catalog-confirmation
  service until it reports a pending duplicate. Review the duplicate, then call
  `confirm_grocery_duplicate_as_separate` from Developer Tools with `confirm:
  true`. Verify one additional pending line and refreshed count. Repeat no
  automatic action: every additional line must come from another deliberate
  confirmed call.

## Notes for the AI

- Runtime remains under `custom_components/home_stock_tracker/`; keep HTTP in
  the coordinator, use Home Assistant async APIs and its provided aiohttp
  session, and preserve single-entry setup/unload behavior.
- This is an approved exception to the read-only boundary only for one explicit,
  confirmed separate-line decision. No polling, automation, background task, or
  sensor may invoke it.
- Reuse the existing validated policy-aware result parser only if it remains
  strict for all three outcomes. Do not weaken response validation or publish
  source response records as a service response.
- Never log or expose API tokens, authorization headers, raw source errors, or
  grocery records beyond the existing sensor boundary.
- Do not implement any PATCH quantity route, arithmetic, merge behavior, or
  mutation of an existing grocery item; those require the later 3c scope.
