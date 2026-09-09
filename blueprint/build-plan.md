# Build plan: Home Stock Tracker HA

## Completed

- [x] 1. Read-only Home Assistant custom integration
  - Config flow, authentication validation and reauthentication.
  - Coordinated polling of groceries, inventory, and low-stock recommendations.
  - Three availability-aware count sensors with record attributes.
  - HACS custom-repository metadata, documentation, and automated tests.

## Next feature — requires product confirmation

- [ ] 2. HACS release-quality readiness
  - Candidate scope: release/versioning policy, HACS validation automation,
    brand assets, and installation/support documentation.
  - Do not start until the desired HACS publication level is confirmed.

## Deferred — requires explicit approval

- [ ] 3. Any write action from Home Assistant
  - This is deliberately outside the integration's current safety boundary and
    needs a separate spec for confirmation, retries, and concurrency behavior.
