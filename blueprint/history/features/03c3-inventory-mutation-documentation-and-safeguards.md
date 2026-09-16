# Feature: Inventory mutation documentation and safeguards

**From build-plan:** feature 3c3
**Status:** verified

## Goal

Make the approved purchase and inventory-stock services safe to discover and
operate from Home Assistant: expose their strict inputs in the service UI and
document one concise, fail-closed workflow that prevents accidental or repeated
mutations.

## In scope

- Add Home Assistant `services.yaml` metadata for
  `complete_grocery_purchase` and `adjust_inventory_stock`, including their
  confirmation, exact-ID, and operation-specific field requirements.
- Consolidate the two inventory mutation workflows in `README.md`: selection
  source, valid inputs, one-request/no-retry behavior, refresh timing, and
  expected safe failure handling.
- Explain the boundary between a purchase and a stock correction, including the
  absence of an additive stock-increment operation.
- Add focused documentation/metadata regression coverage only where the
  repository's existing Python test harness can verify a stable declared
  contract without duplicating Home Assistant's own UI behavior.

## Out of scope

- New services, source routes, mutations, configuration options, automation
  triggers, response payloads, or changes to the paired Home Stock Tracker API.
- Changing the already approved validation, transport, receipt, refresh, or
  unavailable-state behavior of 3c1 or 3c2.
- Documentation for grocery/catalog writes, full HACS installation/support
  material, issue templates, diagnostics, or a generic inventory guide.

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

- [x] **Step 1 - Declare inventory services for Home Assistant** - add precise
  `services.yaml` descriptions and selectors for the existing purchase and
  stock-adjustment service schemas. *Done when:* Developer Tools exposes both
  services with `confirm` described as required, exact UUID targets clearly
  identified, purchase IDs/optional measurement documented, and stock
  `set`/`decrement`/`mark_out` field combinations unambiguous; metadata adds no
  new accepted input or source behavior.

- [x] **Step 2 - Publish the consolidated safety workflow** - revise the README
  inventory-write material into one concise decision and failure guide. *Done
  when:* it tells users where to obtain exact IDs, when to choose purchase versus
  correction, which fields are valid for each operation, that only `set` changes
  a total (no additive increment exists), and that failed/uncertain calls must
  not be retried and refresh only follows a validated receipt.

- [x] **Step 3 - Verify declared contracts stay aligned** - add proportionate
  regression coverage and run the repository tests. *Done when:* a focused test
  or stable fixture proves metadata names and required field/operation choices
  match the registered services; malformed metadata or a renamed service is
  caught, while UI rendering remains a manual Home Assistant check; the full
  pytest suite passes.

## Files / areas

- `custom_components/home_stock_tracker/services.yaml` - Home Assistant service
  descriptions and field metadata for the two inventory mutations.
- `README.md` - consolidated safe-operation and failure guidance.
- `tests/` - a narrow metadata-contract test for declared names and required
  field/operation choices.

## Data / contracts

**Load-bearing public service contract**

| Service | Exact target | Confirmation | Allowed mutation fields |
| --- | --- | --- | --- |
| `home_stock_tracker.complete_grocery_purchase` | one `product_id` UUID and one or more pending `grocery_item_ids` UUIDs | `confirm: true` | optional finite `quantity >= 0`, optional non-empty `unit` |
| `home_stock_tracker.adjust_inventory_stock` | one `product_id` UUID | `confirm: true` | `set` or `decrement` with finite positive `quantity` and optional unit; `mark_out` alone |

`confirm` is local-only. Neither service matches names, infers IDs/units, sends
unsupported fields, retries an uncertain write, or exposes a source receipt.
Only a validated source receipt causes one coordinator refresh; transport,
authorization, HTTP, malformed-payload, conflict, and receipt failures leave
data unavailable and cause no refresh or fallback mutation.

Service metadata must describe the existing schemas exactly; it must not claim
an additive increment, partial purchase, batch adjustment, or any new service
response. This contract is load-bearing for Home Assistant Developer Tools and
future documentation.

## Testing

- Run `.venv/bin/python -m pytest -q tests` when `.venv` exists; otherwise run
  `python3 -m pytest -q tests` after installing `requirements-test.txt`.
- Add a focused test that parses `services.yaml` and checks the two registered
  service names, required confirmation and target fields, and the three stock
  operations.
- Do not add a browser runner: none is configured. Manual Home Assistant check:
  reload the integration, open Developer Tools → Actions, select each service,
  and confirm the field help makes invalid combinations visibly avoidable before
  submitting a call.

## Notes for the AI

- This is documentation and declared-service metadata only; preserve all
  runtime behavior and keep source-service mutation logic untouched.
- Do not put tokens, authorization headers, raw errors, inventory records, or
  source receipts in service descriptions, examples, tests, or logs.
- Use Home Assistant's conventional `services.yaml` format and keep its field
  names/types aligned with the existing Voluptuous schemas.
- Be precise about uncertainty: a user who does not know an ID, quantity, unit,
  or current stock state must resolve it before making a write.
