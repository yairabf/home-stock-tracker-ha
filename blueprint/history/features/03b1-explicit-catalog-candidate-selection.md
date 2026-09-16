# Feature: Explicit catalog-candidate selection

**From build-plan:** feature 3b1
**Status:** verified

## Goal

Let a Home Assistant user explicitly search the Home Stock Tracker catalog and
then either select one exact candidate as an alias or provide final facts for a
new product before adding the requested grocery line. The integration must never
choose a candidate, accept proposal data as authority, or make a catalog or
grocery write without a new explicit service call.

## In scope

- Add a response-only `home_stock_tracker.search_products` service for the
  source service's deterministic, read-only product search.
- Add explicit services for confirming a new product and confirming an alias
  against one exact returned product ID.
- Validate and normalize all Home Assistant inputs before HTTP access, then use
  the existing coordinator and config-entry bearer token for each request.
- Send the source service's two catalog-confirmation POST contracts; handle
  `created` and `confirmation_required` outcomes without retries.
- Refresh coordinator data only after a confirmed `created` grocery line.
- Add focused pytest coverage and README examples for the three services.

## Out of scope

- Automatically selecting a search candidate, accepting advisory proposal data,
  creating an alias from a search result, or retrying a stale/uncertain write.
- Creating a generic product-management surface, modifying/deleting products or
  aliases, or changing the paired Home Stock Tracker service.
- Resolving a pending-grocery duplicate after either confirmation route returns
  `confirmation_required`; that is feature 3b2.
- Purchase, completion, inventory, quantity, or other grocery mutations.

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

- [x] **Step 1 - Define and register explicit Home Assistant service contracts** -
  add constants, voluptuous schemas, lifecycle registration/unregistration, and
  thin routing for catalog search plus the two confirmation services. *Done
  when:* malformed or incomplete product facts, blank aliases, invalid UUIDs,
  invalid product types, invalid quantities, and absent `confirm: true` are
  rejected before transport; `search_products` requires a service response and
  a valid call reaches the sole configured coordinator.

- [x] **Step 2 - Add fail-closed catalog search and confirmation transport** -
  add coordinator-owned authenticated GET/POST helpers that translate the
  contracts below, strictly validate source response shapes, and preserve the
  existing one-request/no-retry write rule. *Done when:* pytest proves the exact
  query and POST JSON, search returns only the documented candidate projection,
  and authentication, connection, non-success, malformed, stale-conflict, or
  unknown-outcome failures expose no source body or token and leave coordinator
  data unavailable.

- [x] **Step 3 - Surface decision outcomes and document the manual flow** -
  return a safe search response, refresh only after `created`, make a duplicate
  result an explicit non-mutating error, and document the select-or-create flow.
  *Done when:* pytest proves `created` performs one refresh, every
  `confirmation_required` result performs no refresh or follow-up write, and
  README examples show search followed by one explicitly confirmed alias or
  final new-product payload.

## Files / areas

- `custom_components/home_stock_tracker/const.py` - service, attribute, and API
  path constants.
- `custom_components/home_stock_tracker/__init__.py` - config-entry-scoped
  registration, response support, and unload cleanup for all new services.
- `custom_components/home_stock_tracker/services.py` - voluptuous schemas and
  thin service routing.
- `custom_components/home_stock_tracker/coordinator.py` - shared authenticated
  product-search and catalog-confirmation HTTP access, validation, and refresh
  ownership.
- `tests/test_services.py` and `tests/test_coordinator.py` - schema, routing,
  source-contract, outcome, and failure coverage.
- `README.md` - Developer Tools service-response and confirmation examples.

## Data / contracts

**Load-bearing Home Assistant services**

| Service | Input | Result / behavior |
| --- | --- | --- |
| `search_products` | Required trimmed `query`; optional integral `limit` from 1 through 20 | Register with `SupportsResponse.ONLY`; return `{exact_match, candidates}`, using only the candidate projection below. It is read-only. |
| `confirm_grocery_new_product` | `confirm: true`, required `product` mapping, and required `grocery_item` mapping | Make exactly one source confirmation POST. |
| `confirm_grocery_product_alias` | `confirm: true`, exact `target_product_id` UUID, trimmed non-empty `alias`, and required `grocery_item` mapping | Make exactly one source confirmation POST. |

All `grocery_item` mappings allow optional positive finite
`requested_quantity`, trimmed non-empty `unit`, and trimmed non-empty `note`.
They are required mappings even when empty. `confirm` is local-only and is never
sent upstream. The confirmed-new-product `product` mapping must contain a
trimmed non-empty `canonical_name`, an `aliases` list of trimmed non-empty
strings, a trimmed non-empty `category`, `typical_unit` as a trimmed non-empty
string or `null`, `product_type` as one of `fast_consumable`, `pantry_staple`,
`household_consumable`, or `discrete_consumable`, and boolean `is_perishable`.

**Read-only candidate search**

```text
GET /api/v1/products/search?query=<query>&limit=<limit>
```

The source result must be a mapping with nullable `exactMatch` and a `candidates`
list. Each candidate must contain `id`, `canonicalName`, `aliases`, nullable
`category`, nullable `typicalUnit`, nullable `productType`, boolean
`isPerishable`, and boolean `predictionEnabled`. Return those fields to Home
Assistant in the snake-case candidate projection `id`, `canonical_name`,
`aliases`, `category`, `typical_unit`, `product_type`, `is_perishable`, and
`prediction_enabled`. Do not return advisory proposals, authorization headers,
or unvalidated source fields. Returned ordering is authoritative; the
integration never selects from it.

**Confirmed source writes**

```json
POST /api/v1/grocery/items/confirm-new-product
{
  "product": {
    "canonicalName": "3% Milk",
    "aliases": ["Three Percent Milk"],
    "category": "dairy",
    "typicalUnit": "carton",
    "productType": "fast_consumable",
    "isPerishable": true
  },
  "groceryItem": {"requestedQuantity": 2, "unit": "cartons"}
}
```

```json
POST /api/v1/grocery/items/confirm-product-alias
{
  "targetProductId": "<exact search-result UUID>",
  "alias": "Three Percent Milk",
  "groceryItem": {"requestedQuantity": 2, "unit": "cartons"}
}
```

Both endpoints accept only final user-approved data; proposal state, source
attribution, and `ifPendingExists` must never be sent. A valid response is
either `created` or `confirmation_required`, with the normal source grocery
result shape. `created` means the grocery line was confirmed and triggers one
coordinator refresh. `confirmation_required` means catalog confirmation may
have succeeded but an existing pending grocery line was not changed; report a
non-sensitive error and make no refresh, retry, quantity change, or further
POST. HTTP 401, transport failure, non-2xx, malformed JSON, unknown outcome,
`PRODUCT_NAME_CONFLICT`, and `PRODUCT_NOT_FOUND` are final for this invocation:
do not retry and never expose raw records or error bodies.

## Testing

- Run `.venv/bin/python -m pytest -q tests` when `.venv` exists; otherwise run
  `python3 -m pytest -q tests` after installing `requirements-test.txt`.
- Add schema and routing tests for every service: required confirmation, nested
  product/grocery validation, UUID and enum validation, response-only search,
  and sole-entry routing.
- Add coordinator tests for search query encoding and the safe candidate
  projection; reject missing or wrong-shaped fields without publishing them.
- Add exact POST-payload tests for both confirmation routes, including omitted
  optional grocery fields; test both permitted outcomes, 401, conflict/not-found
  responses, malformed JSON, connection failure, and one POST only per
  invocation.
- Add service tests proving only `created` requests a refresh and a
  `confirmation_required` response produces no refresh or subsequent write.
- Manual Home Assistant check: call `search_products` from Developer Tools and
  inspect its response; explicitly choose a returned UUID for the alias service
  or enter complete final product facts for the new-product service. Verify one
  created line updates sensors. Re-run against a pending line and verify that no
  quantity or extra line is created; use the later 3b2 flow to decide it.

## Notes for the AI

- Runtime remains in `custom_components/home_stock_tracker/`. Keep all HTTP in
  the coordinator, use Home Assistant async APIs and its provided aiohttp
  session, and preserve single-entry setup/unload behavior.
- Treat catalog records as untrusted response data. Validate before returning a
  service response; never log API tokens, authorization headers, raw source
  errors, candidate records, or confirmation payloads.
- This is an approved exception to the read-only boundary only for the two
  explicit, confirmed catalog-and-grocery requests. No polling, automation, or
  background task may invoke them.
- Preserve unavailable-state behavior for authentication, connection, and
  payload failures. Do not add a fallback that converts an unresolved or stale
  catalog decision into a write.
- Feature 3b2 owns pending-duplicate choices. Do not add quantity arithmetic,
  `create_separate`, or an override to this feature.
