# Release policy

This repository publishes stable Home Stock Tracker HA custom-integration
releases through GitHub Releases. Publishing a release is a maintainer action;
this document does not create tags or releases automatically.

## Version contract

The installed integration version is the plain Semantic Versioning value in
`custom_components/home_stock_tracker/manifest.json`:

| Surface | Format | Example |
| --- | --- | --- |
| Integration manifest | `X.Y.Z` | `0.1.0` |
| Git tag | `vX.Y.Z` | `v0.1.0` |
| GitHub Release | Published release for the matching tag | `v0.1.0` |
| Changelog heading | `X.Y.Z` | `0.1.0` |

All four values must describe the same release. A Git tag alone is not a
release: publish a GitHub Release using the matching tag after the pre-release
checks pass. HACS can then select the published release for installation or
upgrade.

## Choosing the next version

Before `1.0.0`:

- Increment PATCH for a backward-compatible fix.
- Increment MINOR for any user-visible capability or a breaking configuration
  or entity contract.

From `1.0.0` onward:

- Increment PATCH for a backward-compatible fix.
- Increment MINOR for a backward-compatible user-visible capability.
- Increment MAJOR for a breaking user-facing, configuration, entity, or
  integration contract.

If users need to change configuration, automations, entity references, or
installation steps, call that out as a breaking change and provide the required
upgrade action in the changelog and release notes.

## Pre-release checklist

1. Choose the next version under this policy and update the `version` value in
   `custom_components/home_stock_tracker/manifest.json`.
2. Move the relevant user-visible entries from `Unreleased` into the matching
   version heading in `CHANGELOG.md`.
3. Validate JSON metadata and run the documented Home Assistant test suite:

   ```bash
   python3 -m json.tool custom_components/home_stock_tracker/manifest.json
   python3 -m json.tool hacs.json
   .venv/bin/python -m pytest -q tests
   ```

   When `.venv` is unavailable, use a prepared environment with
   `requirements-test.txt` installed and run `python3 -m pytest -q tests`.
4. Run the HACS and Home Assistant validation automation once it is introduced
   by Feature 2b; do not publish when those required checks fail.
5. Create tag `vX.Y.Z` from the verified release commit and publish a GitHub
   Release for that exact tag. Do not publish credentials, tokens, or URLs that
   contain credentials.

## Release notes

Each GitHub Release summarizes user-visible additions, fixes, and any breaking
changes. It links or restates required upgrade steps, names the integration
version, and is consistent with the matching changelog entry. Do not include
API tokens, authorization headers, raw diagnostics, or other secrets.
