# Build plan: Home Stock Tracker HA

## Completed

- [x] 1. Read-only Home Assistant custom integration
  - Config flow, authentication validation and reauthentication.
  - Coordinated polling of groceries, inventory, and low-stock recommendations.
  - Three availability-aware count sensors with record attributes.
  - HACS custom-repository metadata, documentation, and automated tests.

## Next feature — requires product confirmation

- [x] 2. HACS release-quality readiness
  - Confirmed as the next product direction.
  - [x] 2a. Release and versioning policy
  - [x] 2b. Automated HACS validation
  - [x] 2c. HACS brand assets
  - [x] 2d. Installation and support documentation

## Approved write-action rollout

- [ ] 3. Write actions from Home Assistant
  - [x] 3a. Confirmed grocery-list addition
  - [x] 3b. Explicit catalog resolution and duplicate-item decisions
    - [x] 3b1. Explicit catalog-candidate selection
    - [x] 3b2. Explicit pending-duplicate decision
  - [ ] 3c. Purchase and inventory mutations
    - [x] 3c1. Confirmed grocery purchase
    - [x] 3c2. Confirmed inventory stock adjustment
    - [ ] 3c3. Inventory mutation documentation and safeguards
