# Build plan: Home Stock Tracker HA

## Completed

- [x] 1. Read-only Home Assistant custom integration
  - Config flow, authentication validation and reauthentication.
  - Coordinated polling of groceries, inventory, and low-stock recommendations.
  - Three availability-aware count sensors with record attributes.
  - HACS custom-repository metadata, documentation, and automated tests.

## Next feature — requires product confirmation

- [ ] 2. HACS release-quality readiness
  - Confirmed as the next product direction.
  - [x] 2a. Release and versioning policy
  - [x] 2b. Automated HACS validation
  - [ ] 2c. HACS brand assets
  - [ ] 2d. Installation and support documentation

## Deferred — requires explicit approval

- [ ] 3. Any write action from Home Assistant
  - This is deliberately outside the integration's current safety boundary and
    needs a separate spec for confirmation, retries, and concurrency behavior.
