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

It uses authenticated `GET` requests for polling. Its only source-data mutation
is the explicit, confirmed grocery-add service documented below; it does not
call MCP.

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

`requested_quantity`, `unit`, and `note` are optional. Product names that need
resolution, or an item that is already pending, are rejected without creating
or changing a record. The integration does not retry an uncertain write. Use
the source service to resolve a product or decide how to handle a duplicate.

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
