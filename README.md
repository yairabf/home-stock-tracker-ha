# Home Stock Tracker HA

A read-only Home Assistant custom integration for Home Stock Tracker. It
exposes pending groceries, tracked inventory, and actionable low-stock
recommendations as Home Assistant sensors.

## Prerequisites

- A running Home Assistant instance with [HACS](https://hacs.xyz/) installed.
- A running, reachable [Home Stock Tracker service](https://github.com/yairabf/home-stock-tracker)
  and its bearer token. Install and start this base service before configuring
  the integration; Home Assistant must be able to reach it over its network.
- The service's HTTP or HTTPS origin, for example
  `http://inventory.local:3000`. Do not include an API path, query string, or
  fragment. Use `localhost` only when Home Assistant and the service share the
  same network namespace.

Keep the bearer token private. Do not put it in YAML, dashboards, automation
traces, issue reports, or screenshots.

## Prepare the Home Stock Tracker connection

This integration connects to the already-running Home Stock Tracker server. It
needs two values from that server:

- **Home Stock Tracker URL**: the server origin Home Assistant can reach, such
  as `http://inventory.local:3000`. This is not an API route: do not append
  `/api/v1`, `/health`, or a trailing path.
- **API token**: the Home Stock Tracker server's `API_AUTH_TOKEN` value. This
  is a bearer token for the server's protected REST API; it is not a Home
  Assistant long-lived access token, a HACS token, or an OpenAI API key.

### 1. Install and run the base service

Follow the [Home Stock Tracker setup and deployment
guide](https://github.com/yairabf/home-stock-tracker#quickstart) on the machine
that will host the service. Configure it so that Home Assistant can reach its
HTTP or HTTPS origin over the network, then confirm that its `/health` and
`/ready` endpoints are successful.

### 2. Create the server API token

On the machine hosting Home Stock Tracker, generate a long random token:

```bash
openssl rand -hex 32
```

Set the generated value as `API_AUTH_TOKEN` in the base service's `.env` file
(or the equivalent environment configuration used for its deployment), then
restart the base service. For example:

```dotenv
API_AUTH_TOKEN="paste-the-generated-token-here"
```

`API_AUTH_TOKEN` is the exact secret the server checks for every protected API
request. The same value—without `Bearer `—is what you enter into the Home
Assistant integration's **API token** field. Keep it in the server's secret
store or `.env` file and do not commit it.

### 3. Verify the URL and token before adding the integration

From a machine that can reach the service (ideally the Home Assistant host),
test the authenticated endpoint using the same origin and token:

```bash
curl -sS \
  -H "Authorization: Bearer YOUR_API_AUTH_TOKEN" \
  http://inventory.local:3000/api/v1/grocery/items
```

A successful JSON response confirms both values. A `401` means the token does
not match the server's current `API_AUTH_TOKEN`; a connection error means Home
Assistant will not be able to reach the supplied URL. The integration performs
this same authenticated check during setup.

## Install with HACS

1. In Home Assistant, open HACS, select **Integrations**, then select the
   three-dot menu and **Custom repositories**.
2. Add `https://github.com/yairabf/home-stock-tracker-ha` with category
   **Integration**.
3. Download **Home Stock Tracker HA** from HACS and restart Home Assistant.
4. Open **Settings > Devices & services > Add integration**, then select
   **Home Stock Tracker**.
5. Enter the verified Home Stock Tracker service origin and its `API_AUTH_TOKEN`
   value in the **API token** field.

The integration validates both values during setup. It supports one configured
Home Stock Tracker service; adding an origin already configured is rejected.

## What the integration provides

## Entities

| Entity | State | Attributes |
| --- | --- | --- |
| `sensor.pending_groceries` | Pending grocery count | `items` |
| `sensor.tracked_inventory` | Current plus uncertain inventory count | `current`, `uncertain` |
| `sensor.low_stock_recommendations` | Actionable recommendation count | `recommendations` |

The integration polls the authenticated service every five minutes. A successful
empty result appears as `0`. Authentication, connectivity, non-success, or
invalid-response failures make all entities unavailable rather than showing
stale data as current.

It uses authenticated `GET` requests for polling. Its only source-data writes
are the explicit, confirmed grocery, catalog, and purchase services documented
below; it does not call MCP.

## Add a grocery item

The integration provides one explicit, opt-in write service:
`home_stock_tracker.add_grocery_item`. It adds a named item only when the call
sets `confirm: true`; it never runs during polling or automatically from a
low-stock recommendation.

```yaml
action: home_stock_tracker.add_grocery_item
data:
  product_name: Milk
  confirm: true
  requested_quantity: 2
  unit: carton
  note: Weekly shop
```

`requested_quantity`, `unit`, and `note` are optional. The integration does not
retry an uncertain write.

## Resolve a catalog choice

If an item name needs a catalog decision, first call the response-only search
service from Developer Tools. It is read-only and returns candidates in the
source service's authoritative order.

```yaml
action: home_stock_tracker.search_products
data:
  query: Three Percent Milk
  limit: 5
response_variable: catalog_search
```

Choose a returned exact `id` yourself; the integration never selects a
candidate. To approve an alias relationship and add the grocery item, call:

```yaml
action: home_stock_tracker.confirm_grocery_product_alias
data:
  confirm: true
  target_product_id: <exact id from catalog_search>
  alias: Three Percent Milk
  grocery_item:
    requested_quantity: 2
    unit: cartons
```

To create a new catalog product instead, supply complete final facts—never a
proposal or inferred values:

```yaml
action: home_stock_tracker.confirm_grocery_new_product
data:
  confirm: true
  product:
    canonical_name: 3% Milk
    aliases:
      - Three Percent Milk
    category: dairy
    typical_unit: carton
    product_type: fast_consumable
    is_perishable: true
  grocery_item:
    requested_quantity: 2
    unit: cartons
```

Both confirmation services make one request only. A pending-duplicate result
does not refresh or change the existing grocery line; it may mean the catalog
decision succeeded but the grocery quantity still needs a separate explicit
decision. Do not retry it.

## Add a separate duplicate line

After reviewing a pending-duplicate result, a household member can deliberately
create one additional line with
`home_stock_tracker.confirm_grocery_duplicate_as_separate`. This service never
changes the existing line and must not be used to increment or merge its
quantity.

```yaml
action: home_stock_tracker.confirm_grocery_duplicate_as_separate
data:
  product_name: Three Percent Milk
  confirm: true
  requested_quantity: 2
  unit: cartons
  note: for the children
```

All line details other than `product_name` and `confirm` are optional. The
integration sends a single request with its fixed `create_separate` policy, then
refreshes its sensors only after the source confirms creation. It does not retry
or fall back to a quantity change if the source still requires a decision or
product resolution.

## Inventory write safety

All inventory writes are deliberate Developer Tools actions. Before submitting
one, copy the exact IDs from a fresh Home Stock Tracker sensor attribute; never
replace an ID with a product name or an inferred value.

| If you need to… | Use | Exact selection |
| --- | --- | --- |
| Mark pending grocery lines as bought | `complete_grocery_purchase` | One pending line's `productId` and one or more pending line `id` values from `sensor.pending_groceries` |
| Correct a known stock total, record consumption, or report none remaining | `adjust_inventory_stock` | One `productId` from an existing Home Stock Tracker inventory sensor record |

Every call requires `confirm: true`, makes one source request, and refreshes
sensors only after a validated receipt. If a call returns an error, entities
become unavailable, or the result is uncertain, stop: do not retry, repeat,
fall back to another mutation, or automate the call. Re-read the source data
and resolve the failure before making a new, explicit decision.

## Complete a grocery purchase

To mark pending grocery items as purchased, inspect the `items` attribute of
`sensor.pending_groceries` and copy the exact `productId` and pending item `id`
values. Then call the explicit confirmation service from Developer Tools:

```yaml
action: home_stock_tracker.complete_grocery_purchase
data:
  confirm: true
  product_id: <exact productId from sensor.pending_groceries>
  grocery_item_ids:
    - <exact pending item id from sensor.pending_groceries>
  quantity: 2
  unit: cartons
```

`quantity` and `unit` are optional; omit both to preserve the source service's
requested measurement. Each call accepts one product and one or more exact
pending item IDs for that product. It makes one request only, refreshes the
sensors only after a validated purchase receipt. Use it only for selected
pending lines—not stock corrections or partial purchases.

## Adjust inventory stock

To correct one product's stock, copy its exact `productId` from an existing
sensor attribute and make an explicit confirmed call from Developer Tools. The
service does not resolve names or infer quantities or units.

```yaml
action: home_stock_tracker.adjust_inventory_stock
data:
  confirm: true
  product_id: <exact productId from a Home Stock Tracker sensor>
  operation: set
  quantity: 3
  unit: liters
```

Use `set` to record the new total, or `decrement` with a positive `quantity` to
record consumption. There is no additive “increase by” operation. Use
`mark_out` only when none remains; it accepts neither `quantity` nor `unit`:

```yaml
action: home_stock_tracker.adjust_inventory_stock
data:
  confirm: true
  product_id: <exact productId from a Home Stock Tracker sensor>
  operation: mark_out
```

Use this service only when the stock fact is known. Do not use it automatically,
retry a failed call, invent an additive operation, or substitute a product name
for the exact ID.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m pytest -q tests
```

## Troubleshooting and support

| Symptom | What to do |
| --- | --- |
| The setup form says the service URL is invalid | Enter only the service's HTTP or HTTPS origin, such as `http://inventory.local:3000`. Remove any API path, query string, or fragment. |
| Setup cannot connect | Confirm that Home Assistant can reach the service URL over its own network and that the service is running. Recheck the host, port, scheme, and any local firewall or proxy configuration. |
| Setup rejects authentication, or Home Assistant asks to reauthenticate | Obtain a valid Home Stock Tracker bearer token and complete the reauthentication form. The configured service URL is retained; only the replacement token is requested. |
| Entities are unavailable | Check service reachability and the token first. Entities become unavailable for authentication, connectivity, non-success, or invalid-response failures rather than showing stale data. |
| A second setup is rejected | The integration supports one Home Stock Tracker configuration. Use the existing integration instead of adding the same service again. |

Report reproducible integration problems at
<https://github.com/yairabf/home-stock-tracker-ha/issues>. Include the Home
Assistant and integration versions, the steps that reproduce the problem, the
visible error or unavailable state, and confirmation of whether the service is
reachable from Home Assistant. **Never include** a bearer token, authorization
header, credentialed URL, raw source records, screenshots containing those
values, or a full diagnostic that exposes them.

See the [release policy](RELEASE.md) for versioning and publication details, and
the [Apache-2.0 license](LICENSE) for license terms.

## License

Copyright 2026 Yair Abramovitch.

Licensed under the [Apache License, Version 2.0](LICENSE).
