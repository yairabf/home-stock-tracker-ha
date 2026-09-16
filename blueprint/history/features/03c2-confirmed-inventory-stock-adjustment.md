# Feature: Confirmed inventory stock adjustment

**From build-plan:** feature 3c2
**Status:** verified

## Goal

Let a household member explicitly set a product's current stock, decrement it
after consumption, or mark it out from Home Assistant. Each action must use an
exact product UUID, submit one authenticated fail-closed request, and refresh
the read-model sensors only after the source service returns a validated receipt.

## In scope

- Register one opt-in Home Assistant service,
  `home_stock_tracker.adjust_inventory_stock`.
- Require `confirm: true`, one canonical source `product_id` UUID, and exactly
  one supported operation: `set`, `decrement`, or `mark_out`.
- For `set` and `decrement`, require a finite positive `quantity`; accept an
  optional trimmed non-empty `unit`. For `mark_out`, reject both fields.
- Send the sole source-supported mutation, `POST /api/v1/inventory/stock/:productId`,
  through the coordinator and strictly validate the event-and-stock receipt.
- Fail closed for invalid input, authentication, connection, HTTP, malformed
  response, receipt mismatch, and source conflicts; never retry an uncertain
  write.
- Refresh coordinator data once, and only after a valid source receipt.
- Add focused pytest coverage and a README Developer Tools example.

## Out of scope

- An additive/increment operation (for example, “add two”)—the paired source
  service does not expose one. `set` records an explicit total instead.
- Purchases, restocks, generic event creation, prediction feedback, grocery
  changes, catalog resolution, automatic adjustments, name-based selection,
  or a caller-selected endpoint/event type.
- Batch or cross-product mutations, units inferred from sensor records, source
  receipts exposed as service data, and changes to the paired source service.
- The broader installation, safety, troubleshooting, and support documentation
  work reserved for 3c3.

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

- [x] **Step 1 - Define and register the explicit stock-adjustment service** -
  add constants, strict discriminated operation validation, config-entry
  lifecycle registration/cleanup, and a thin handler. *Done when:* only
  `confirm: true`, one canonical UUID `product_id`, and exactly one supported
  operation reach the coordinator; `set`/`decrement` require finite positive
  `quantity` and accept only an optional trimmed non-empty `unit`; `mark_out`
  rejects both fields; rejected input makes no transport.

- [x] **Step 2 - Submit and validate one stock-adjustment receipt** - add the
  coordinator-owned authenticated transport and operation-specific receipt
  validator. *Done when:* pytest proves exactly one POST to the selected
  product route with local `confirm` omitted and only the allowed JSON fields;
  it accepts only a receipt whose event is for that product with the expected
  mapped event type (`STOCK_SET`, `STOCK_CONSUMED`, or `STOCK_OUT`) and whose
  stock projection identifies the same product and links its `recordedEventId`
  to that event; no failure path retries, falls back, or performs another write.

- [x] **Step 3 - Refresh confirmed data and document the narrow workflow** -
  refresh only on a valid receipt and add a Developer Tools example. *Done
  when:* pytest proves one refresh after each accepted operation and none after
  source rejection, 401, transport/HTTP/JSON failure, or invalid receipt;
  failures leave coordinator data unavailable; README shows exact-ID,
  confirmation-required `set`, `decrement`, and `mark_out` calls without
  presenting them as automatic or additive operations.

## Files / areas

- `custom_components/home_stock_tracker/const.py` - service, route, operation,
  and attribute constants.
- `custom_components/home_stock_tracker/services.py` - discriminated service
  schema and coordinator routing.
- `custom_components/home_stock_tracker/__init__.py` - service registration
  and final-unload cleanup.
- `custom_components/home_stock_tracker/coordinator.py` - shared authenticated
  mutation transport, receipt validation, and unavailable-state handling.
- `tests/test_services.py` and `tests/test_coordinator.py` - validation,
  routing, exact source-contract, receipt, refresh, and failure coverage.
- `README.md` - concise Developer Tools examples and safety boundary.

## Data / contracts

**Load-bearing Home Assistant service**

| Service | Required input | Optional input | Behavior |
| --- | --- | --- | --- |
| `home_stock_tracker.adjust_inventory_stock` | `confirm: true`; canonical UUID `product_id`; `operation` | finite positive `quantity` and trimmed non-empty `unit` only for `set`/`decrement` | Applies one explicit source stock operation to the selected product. |

| Operation | Required fields | Prohibited fields | Expected receipt event |
| --- | --- | --- | --- |
| `set` | `quantity` | none | `STOCK_SET` |
| `decrement` | `quantity` | none | `STOCK_CONSUMED` |
| `mark_out` | none | `quantity`, `unit` | `STOCK_OUT` |

`confirm` is local-only and must never be sent upstream. UUIDs avoid matching a
stale or ambiguous product name. Units remain source-validated: the integration
does not infer compatibility or substitute a sensor value.

**Confirmed source request**

```json
POST /api/v1/inventory/stock/01234567-89ab-4cde-8f01-23456789abcd
{ "operation": "decrement", "quantity": 1, "unit": "liter" }
```

The body must be exactly one of `set` or `decrement` with a positive quantity
and optional unit, or `mark_out` alone. Do not send `confirm`, a product ID in
the body, confidence, metadata, or an invented increment/event operation.

A successful response is accepted only when it has `event` and `stock` mappings:
`event.id` is non-empty, `event.productId` is the requested product, and
`event.eventType` matches the operation; `stock.productId` is the requested
product and `stock.recordedEventId` equals `event.id`. The receipt is not
exposed to Home Assistant. Any 401, transport failure, non-2xx response,
malformed JSON, source conflict, or mismatched receipt is final: no retry,
refresh, fallback mutation, raw response, authorization header, or token exposure.

## Testing

- Run `.venv/bin/python -m pytest -q tests` when `.venv` exists; otherwise run
  `python3 -m pytest -q tests` after installing `requirements-test.txt`.
- Add service tests for confirmation, UUID canonicalization/rejection, each
  operation shape, finite positive quantities, units, sole-entry routing, and
  no transport for rejected input.
- Add coordinator tests for each exact one-POST URL/body, optional-unit
  omission, valid receipt mapping, 401, transport failure, non-success status,
  malformed JSON, source conflict, wrong product/event type, missing event ID,
  wrong stock product, and broken event-to-stock linkage.
- Prove every accepted operation requests exactly one refresh; every rejected or
  uncertain outcome requests no refresh or secondary write and marks the
  coordinator unavailable.
- Manual Home Assistant check: obtain an exact product ID from sensor data, call
  one operation in Developer Tools with `confirm: true`, confirm the projection
  changes after one refresh, and verify a failed attempt produces a safe error
  rather than an automatic retry.

## Notes for the AI

- This is a narrow approved exception to the read-only boundary. Keep runtime
  code under `custom_components/home_stock_tracker/`, HTTP in the coordinator,
  and Home Assistant async/aiohttp conventions intact.
- Reuse strict parsing helpers only when they preserve the operation-specific
  contract. Do not weaken validation for a generic inventory-event API.
- Preserve config-entry ownership and final-unload cleanup. The integration has
  one configured coordinator, and service routing must retain that guard.
- Never log or return API tokens, authorization headers, raw source errors, or
  inventory records. Preserve unavailable-state behavior after uncertain writes.
- Do not implement 3c3 safeguards beyond this feature's minimal Developer Tools
  example.
