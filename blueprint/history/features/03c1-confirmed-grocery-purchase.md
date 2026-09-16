# Feature: Confirmed grocery purchase

**From build-plan:** feature 3c1
**Status:** verified

## Goal

Let a household member explicitly complete selected pending grocery items as a
single purchase from Home Assistant. The integration must submit one
authenticated, fail-closed request to the source service, then refresh its
read-model sensors only after the service confirms the purchase.

## In scope

- Register one opt-in Home Assistant service,
  `home_stock_tracker.complete_grocery_purchase`.
- Require a deliberate confirmation and exact UUIDs for one source product and
  one or more pending grocery items belonging to that product.
- Allow an optional non-negative actual quantity and optional trimmed unit as
  the one shared purchase measurement; omitted fields retain the source
  service's requested-measurement behavior.
- Send exactly one authenticated `POST /api/v1/inventory/purchases/complete`
  through the coordinator and strictly validate its purchase receipt.
- Fail closed for validation, authentication, connection, HTTP, malformed
  response, and source-conflict failures; never retry an uncertain write.
- Refresh the coordinator once, and only after a confirmed valid purchase.
- Add focused pytest coverage and a README Developer Tools example.

## Out of scope

- Partial purchase completion, batch completion across products, purchase date,
  confidence, metadata, expiration records, or a source-response service
  payload.
- Generic stock operations (`set`, `decrement`, or `mark_out`), direct inventory
  events, record-purchase endpoints, prediction feedback, or any other
  inventory mutation; these belong to 3c2 or later work.
- Completing an item by name, choosing a product or grocery item automatically,
  merging duplicates, changing a grocery request, or an automatic write from a
  sensor, polling cycle, automation, or recommendation.
- Changes to the paired Home Stock Tracker service or its API.

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

- [x] **Step 1 - Define and register the explicit purchase service** - add
  constants, UUID/list/quantity/unit validation, config-entry lifecycle
  registration and cleanup, and a thin handler. *Done when:* the service
  requires `confirm: true`, one canonical `product_id` UUID, and a non-empty
  duplicate-free list of canonical `grocery_item_ids` UUIDs; it accepts only an
  optional finite quantity of zero or more and an optional trimmed non-empty
  `unit`; invalid input performs no transport and a valid call routes only to
  the sole configured coordinator.

- [x] **Step 2 - Submit and validate one purchase receipt** - add a
  coordinator-owned transport helper that maps the locally validated input to
  the source contract and recognizes only a complete valid receipt. *Done
  when:* pytest proves one POST to the exact route with `confirm` omitted; the
  request contains only `productId`, `groceryItemIds`, and supplied optional
  measurement fields; a valid receipt contains one `PURCHASED` event for the
  requested product and a non-empty `groceryItems` list containing exactly the
  requested IDs, all marked `purchased` and linked to that event; no request is
  retried after any failure.

- [x] **Step 3 - Refresh confirmed data and document the safety boundary** -
  refresh once only after a valid receipt and document the Developer Tools flow.
  *Done when:* pytest proves a valid receipt requests one refresh, while source
  rejection, 401, connection failure, non-2xx response, malformed JSON, or
  invalid/mismatched receipt requests no refresh or secondary write and marks
  coordinator data unavailable; README shows an explicit confirmation example
  and says users must copy exact pending-item/product IDs from the existing
  sensor data.

## Files / areas

- `custom_components/home_stock_tracker/const.py` - purchase service, route,
  and attribute constants.
- `custom_components/home_stock_tracker/services.py` - service schema,
  coordinator routing, safe outcome handling.
- `custom_components/home_stock_tracker/__init__.py` - registration and final
  unload cleanup.
- `custom_components/home_stock_tracker/coordinator.py` - shared authenticated
  purchase transport, exact receipt validation, and unavailable-state failure
  handling.
- `tests/test_services.py` and `tests/test_coordinator.py` - validation,
  routing, source contract, receipt, refresh, and failure coverage.
- `README.md` - explicit Home Assistant Developer Tools invocation and safety
  boundaries.

## Data / contracts

**Load-bearing Home Assistant service**

| Service | Required input | Optional input | Behavior |
| --- | --- | --- | --- |
| `home_stock_tracker.complete_grocery_purchase` | `confirm: true`; canonical UUID `product_id`; non-empty duplicate-free list of canonical UUID `grocery_item_ids` | finite `quantity >= 0`; trimmed non-empty `unit` | Completes only the selected pending items for that product, creating one source purchase event. |

`confirm` is local-only and must not be sent upstream. IDs are explicit to avoid
matching by name or acting on stale inference. A call may include multiple item
IDs only where every item is intentionally purchased for the one supplied
product; cross-product and partial-purchase flows are intentionally excluded.
The integration accepts neither purchase date, confidence, metadata, arbitrary
event type, stock operation, nor a caller-selected route.

**Confirmed source request**

```json
POST /api/v1/inventory/purchases/complete
{
  "productId": "01234567-89ab-4cde-8f01-23456789abcd",
  "groceryItemIds": ["11111111-1111-4111-8111-111111111111"],
  "quantity": 2,
  "unit": "cartons"
}
```

`quantity` and `unit` are omitted when absent. The integration does not supply
or infer `confidence` or `metadata`; it does not call the source's generic
`/inventory/purchases`, `/inventory/stock/:productId`, or partial-completion
routes.

A receipt is accepted only when its mapping has an `event` mapping and a
`groceryItems` list: the event must identify the requested product and have
`eventType: "PURCHASED"`; every returned item must be one of the requested IDs,
be `status: "purchased"`, and reference that event ID; the returned ID set must
exactly equal the requested ID set. The receipt is not exposed to Home
Assistant. Any 401, transport failure, non-2xx response, malformed JSON, or
mismatched receipt is final: no retry, refresh, fallback mutation, raw source
body, authorization header, or token exposure.

## Testing

- Run `.venv/bin/python -m pytest -q tests` when `.venv` exists; otherwise run
  `python3 -m pytest -q tests` after installing `requirements-test.txt`.
- Add service tests for explicit confirmation, UUID normalization/rejection,
  non-empty duplicate-free item IDs, invalid quantity and unit, sole-entry
  routing, and no transport for rejected input.
- Add coordinator tests asserting the exact one-POST URL and JSON; absent
  optional fields are omitted and no local-only or unsupported source fields
  are transmitted.
- Cover accepted receipts, 401, transport failure, non-success response,
  malformed JSON, missing receipt fields, wrong product/event type, duplicate,
  missing, unrequested, non-purchased, or wrongly linked grocery items. Assert
  one request, no retry, safe errors, and unavailable coordinator data on every
  source or receipt failure.
- Add handler tests proving only a valid receipt requests exactly one refresh;
  each failure path has no refresh or secondary write.
- Manual Home Assistant check: inspect the `items` attribute of
  `sensor.pending_groceries`, copy a pending item's `productId` and `id`, then
  call the service in Developer Tools with `confirm: true`. Verify that exact
  item becomes purchased, related inventory state updates after one refresh,
  and a repeated call produces a safe error rather than a second purchase.

## Notes for the AI

- This is the narrowly approved exception to the read-only boundary. Keep all
  runtime code under `custom_components/home_stock_tracker/`, HTTP in the
  coordinator, and Home Assistant async/aiohttp conventions intact.
- Reuse only strict parsing helpers that still enforce this purchase receipt;
  do not weaken validation to support a generic inventory API.
- Preserve config-entry ownership and final-unload service cleanup. The current
  integration supports exactly one configured coordinator, and service routing
  must retain that guard.
- Never log or return API tokens, authorization headers, raw source errors, or
  purchase/grocery records. Preserve unavailable-state behavior after uncertain
  writes.
- Do not implement 3c2's stock adjustment or 3c3's broader safeguards and
  documentation in this feature.
