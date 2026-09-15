# Feature: Confirmed grocery-list addition

**From build-plan:** feature 3a
**Status:** verified

## Goal

Let a Home Assistant user or automation explicitly add one named item to the
Home Stock Tracker grocery list. The operation must fail closed: ambiguous
products, an existing pending item, and any uncertain HTTP outcome must never
silently create or alter a record.

## In scope

- Register `home_stock_tracker.add_grocery_item` for the configured entry.
- Require a trimmed, non-empty `product_name` and `confirm: true`; accept an
  optional finite positive `requested_quantity` plus non-empty `unit` and
  `note` strings when supplied.
- Submit one authenticated `POST /api/v1/grocery/items` request using the
  duplicate-safe, non-mutating-on-ambiguity policy described below.
- Refresh the existing coordinator only after a confirmed `created` result.
- Surface clear Home Assistant service errors without including tokens,
  authorization headers, raw records, or full source responses.
- Add focused pytest coverage and document the service call.

## Out of scope

- Creating products, resolving product aliases, or accepting an unknown-product
  proposal.
- Overriding a `confirmation_required` duplicate result or changing an existing
  grocery item's quantity.
- Deleting, completing, purchasing, restocking, or otherwise changing inventory.
- Background, polling-triggered, or automatic write actions.
- Multiple config entries; the integration remains single-entry.

## Build loop

Build one step at a time, never the whole feature at once.

1. Plan mode lays out the step before any code.
2. The AI implements just that step.
3. It shows the diff (not full files); you read it and understand it.
4. You approve, then choose whether to commit a checkpoint or roll straight on.
   Checkpoints are optional; `/complete` makes the real feature-level commit at
   the end.

Never accept a step you have not read. If a diff is too big to review, split it.

## Build steps

- [x] **Step 1 - Register and validate the explicit Home Assistant service** -
  add the service name, voluptuous schema, lifecycle registration/unregistration,
  and handler routing to the configured coordinator. *Done when:* a call without
  `confirm: true`, with an empty name or optional string, or with an invalid
  quantity is rejected locally before any HTTP request; a valid call reaches the
  coordinator for the sole configured entry.

- [x] **Step 2 - Add fail-closed grocery-add transport** - add a coordinator-owned
  authenticated POST helper that emits the fixed policy payload, validates the
  outcome shape, and maps authorization, connection, HTTP, and malformed-response
  errors to safe Home Assistant errors. *Done when:* pytest proves the exact
  request contract, no automatic POST retry occurs, and uncertain or malformed
  responses leave coordinator data unavailable rather than presenting it as
  current.

- [x] **Step 3 - Handle outcomes and document use** - complete the service
  handler's `created`, `confirmation_required`, and `product_resolution_required`
  paths; refresh sensor data only after `created`; add README usage and safety
  notes. *Done when:* pytest proves a created item triggers a refresh, while
  duplicate or unresolved-product results make no follow-up mutation or refresh;
  the documented YAML example requires `confirm: true`.

## Files / areas

- `custom_components/home_stock_tracker/const.py` - service and request-path
  constants.
- `custom_components/home_stock_tracker/__init__.py` - config-entry-scoped
  service lifecycle and handler registration.
- `custom_components/home_stock_tracker/coordinator.py` - shared authenticated
  POST access, response validation, failure mapping, and refresh ownership.
- `custom_components/home_stock_tracker/services.py` *(new, if it keeps
  lifecycle code small)* - service schema and handler orchestration.
- `tests/test_coordinator.py` and `tests/test_services.py` *(new)* - transport,
  failure, service-validation, and outcome coverage.
- `README.md` - service call, confirmation requirement, and non-automatic-write
  safety documentation.

## Data / contracts

**Load-bearing source request contract**

```json
POST /api/v1/grocery/items
{
  "unknownProductPolicy": "propose_if_missing",
  "productName": "<product_name>",
  "groceryItem": {
    "ifPendingExists": "return_existing",
    "requestedQuantity": "<optional positive number>",
    "unit": "<optional string>",
    "note": "<optional string>"
  }
}
```

- The integration always sends `unknownProductPolicy: "propose_if_missing"`;
  it never sends a product-creation payload.
- The integration always sends `ifPendingExists: "return_existing"`; it never
  chooses `create_separate`.
- Valid source outcomes are:

  | Outcome | Integration behavior |
  | --- | --- |
  | `created` | Treat as confirmed, then request one coordinator refresh. If that refresh fails, leave sensors unavailable without retrying or undoing the confirmed source mutation. |
  | `confirmation_required` | Raise a non-sensitive service error; do not retry, mutate, or refresh. |
  | `product_resolution_required` | Raise a non-sensitive service error; do not choose a candidate, retry, mutate, or refresh. |

- No idempotency key is available in this source contract. The integration must
  issue at most one POST per service invocation and never retry it after a
  timeout, disconnect, non-success response, or invalid response.
- `confirm` is a Home Assistant-only boolean; it is never forwarded to the
  source service. Input strings are trimmed; blank optional strings are rejected
  before the request is sent.
- Authorization uses the existing config-entry bearer token and must never be
  logged or returned in errors.

## Testing

- Run `.venv/bin/python -m pytest -q tests` when `.venv` exists; otherwise run
  `python3 -m pytest -q tests` after installing `requirements-test.txt`.
- Add service tests for schema rejection before transport and valid-call routing.
- Add coordinator tests for the exact POST JSON and headers, each declared
  source outcome, 401, connection failure, non-success response, malformed JSON,
  and no retry after a failed POST.
- Add integration-level tests that `created` refreshes sensor state and every
  non-created or uncertain outcome makes no additional POST or refresh.
- Manual Home Assistant check: call `home_stock_tracker.add_grocery_item` from
  Developer Tools with `confirm: true`; verify one new grocery item and an
  updated sensor count. Repeat the request and verify the integration reports a
  duplicate decision without adding another item.

## Notes for the AI

- The runtime remains within `custom_components/home_stock_tracker/`; do not
  modify the paired Home Stock Tracker service.
- Keep shared HTTP in the coordinator, use Home Assistant async APIs and its
  provided aiohttp session, and preserve config-entry unload behavior.
- The write path is deliberately narrower than the source API. Do not expand it
  while implementing this feature.
- Do not expose source records in service errors. Keep existing unavailable-state
  behavior for connection, authentication, and payload failures.
