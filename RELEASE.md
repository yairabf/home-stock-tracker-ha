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
4. Push the release candidate branch and open its **Validate** workflow run in
   GitHub Actions. Require both **Hassfest** and **HACS** to pass for the
   candidate commit. Confirm the run's commit and the source/ref selected in
   each job's logs; a passing check for another revision is insufficient.
   Do not publish while a check is failed, cancelled, skipped, or pending.
5. Create tag `vX.Y.Z` from the verified release commit and publish a GitHub
   Release for that exact tag. Do not publish credentials, tokens, or URLs that
   contain credentials.

## Validation workflow

[Validate](.github/workflows/validate.yml) runs on all branch pushes, pull
requests, manual requests, and Mondays at 04:17 UTC. Its two jobs run
independently:

| Check | Validates |
| --- | --- |
| Hassfest | Integration metadata in the workflow's checkout using Home Assistant's official validator |
| HACS | HACS repository requirements using the event's repository and the official HACS action |

The repository must be public and unarchived, have a description and topics,
and have issues enabled. Use the topics `home-assistant`, `hacs`, and
`custom-integration`, preserving any other existing topics. Missing topics or
other unmet requirements must be corrected before expecting HACS to pass.

The sole temporary exception is HACS's `brands` check. Feature 2c supplies the
brand assets and removes `ignore: brands` from the workflow once validation
accepts them. Do not add other ignores to bypass failures. Success with this
exception does not qualify the repository for HACS default-list inclusion.

To inspect a result, open the repository's **Actions > Validate**, select the
run for the candidate branch and commit, then open **Hassfest** and **HACS** and
their validation-step logs. Correct metadata or repository-setting failures
and push a new candidate commit when files change. For a transient download,
GitHub API, or runner failure, use **Re-run failed jobs** after the cause clears.
Confirm both jobs pass for the final candidate before tagging it. Do not move
the candidate branch during validation: HACS resolves branch content through
GitHub, so a later branch head can differ from the workflow's checkout.

Use **Run workflow** on the Actions page for an on-demand maintenance check
once the workflow is present on the default branch. Scheduled and manual HACS
runs can select the latest published release, or the default branch when no
release exists. Their green results do not prove an unreleased candidate
passed. Pull-request HACS runs check the contributor branch; Hassfest uses
GitHub's event checkout. Use the final candidate's branch-push run as the
release evidence.

Validator references follow their upstream branches, so later maintenance runs
may expose changed requirements. Validation requires no Home Stock Tracker
token, live service, or custom GitHub secret. Jobs use read-only permissions,
do not post PR comments, and do not publish a release or modify the repository.
The local JSON checks and pytest suite above remain part of the release gate;
passing them does not replace the hosted validators.

See the [HACS action documentation](https://hacs.xyz/docs/publish/action/) and
[Hassfest guidance](https://developers.home-assistant.io/blog/2020/04/16/hassfest/)
for the upstream validation behavior.

## Release notes

Each GitHub Release summarizes user-visible additions, fixes, and any breaking
changes. It links or restates required upgrade steps, names the integration
version, and is consistent with the matching changelog entry. Do not include
API tokens, authorization headers, raw diagnostics, or other secrets.
