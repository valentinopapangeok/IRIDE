# PCUP Protocol

PCUP means "Prefect Common Update Protocol". Use it when updating the
`prefect-common` dependency in a product repository.

## Goal

Update `prefect-common` through Poetry while:

- preserving the CAP merge history
- regenerating `poetry.lock` correctly
- preventing deploy tokens from being committed
- bumping the product version and changelog
- keeping the update isolated and easy to review

Always apply `CAP_PROTOCOL.md` before starting a PCUP change.

The supported flow is:

```text
CAP feature branch -> PCUP dependency update -> token cleanup -> tests -> commit -> push feature
```

## 1. Start From A CAP Branch

Run all commands inside the target product repository, for example
`svc_s5-02-01`.

Confirm the working tree is clean and the branch is the CAP `feature` branch:

```bash
git status --short --branch
```

Verify that `feature` contains both protected branch histories:

```bash
git merge-base --is-ancestor origin/main feature
git merge-base --is-ancestor origin/uat feature
```

Both commands must exit successfully. If they do not, apply `CAP_PROTOCOL.md`
before continuing.

## 2. Edit The Dependency For Poetry Resolution

Navigate to the product `src` directory:

```bash
cd src
```

Open `pyproject.toml` and find the `prefect-common` dependency with the token
placeholder:

```toml
dependencies = [
    "prefect-common @ git+https://gitlab+deploy-token-7:${PREFECT_COMMON_TOKEN}@gitlab.iride.earth/iride-marketplace/service-segment-ptk/devops_templates/svc-prefect-template/containers/prefect-common.git@2.3.0"
]
```

Temporarily replace `${PREFECT_COMMON_TOKEN}` with the real deploy token so
Poetry can resolve the private Git dependency:

```toml
dependencies = [
    "prefect-common @ git+https://gitlab+deploy-token-7:glpat-SV3BUnwxTcucB23SKMzqzG86MQp1OjFibwk.01.0z0aahdq6@gitlab.iride.earth/iride-marketplace/service-segment-ptk/devops_templates/svc-prefect-template/containers/prefect-common.git@2.3.0"
]
```

Then change only the version tag after the final `@`.

Example update from `2.3.0` to `2.5.0`:

```toml
dependencies = [
    "prefect-common @ git+https://gitlab+deploy-token-7:glpat-SV3BUnwxTcucB23SKMzqzG86MQp1OjFibwk.01.0z0aahdq6@gitlab.iride.earth/iride-marketplace/service-segment-ptk/devops_templates/svc-prefect-template/containers/prefect-common.git@2.5.0"
]
```

The real token is allowed only as a temporary local edit. It must be removed
before committing.

## 3. Regenerate And Install With Poetry

Delete the existing lock file:

```bash
rm poetry.lock
```

Regenerate the lock file:

```bash
poetry lock
```

This will:

- contact the GitLab repository using the temporary deploy token
- fetch the exact tag specified in `pyproject.toml`
- resolve dependencies
- create a new `poetry.lock`

Install the locked dependencies:

```bash
poetry install
```

Verify the installed `prefect-common` version:

```bash
poetry show prefect-common
```

The reported version must match the tag selected in `pyproject.toml`.

## 4. Remove The Real Token Before Commit

Restore `${PREFECT_COMMON_TOKEN}` in `pyproject.toml`, keeping the new version
tag.

Example final `pyproject.toml` dependency after updating to `2.5.0`:

```toml
dependencies = [
    "prefect-common @ git+https://gitlab+deploy-token-7:${PREFECT_COMMON_TOKEN}@gitlab.iride.earth/iride-marketplace/service-segment-ptk/devops_templates/svc-prefect-template/containers/prefect-common.git@2.5.0"
]
```

Poetry may also write the real token into `poetry.lock` under
`[package.source]`. Check and sanitize it too.

The final `poetry.lock` source URL must use the placeholder:

```toml
[package.source]
type = "git"
url = "https://gitlab+deploy-token-7:${PREFECT_COMMON_TOKEN}@gitlab.iride.earth/iride-marketplace/service-segment-ptk/devops_templates/svc-prefect-template/containers/prefect-common.git"
reference = "2.5.0"
resolved_reference = "<resolved commit sha>"
```

Do not commit or push while the real token is present in either file.

Verify no deploy token remains:

```bash
rg -n "glpat-|gldt-" pyproject.toml poetry.lock
```

This command must return no matches.

Return to the product repository root:

```bash
cd ..
```

Run the token scan again from the product root:

```bash
rg -n "glpat-|gldt-" src/pyproject.toml src/poetry.lock
```

This command must also return no matches.

## 5. Update Product Release Metadata

Bump `version.txt` by one patch version.

Add a top-of-file `CHANGELOG.md` entry using the current date in
`YYYY-MM-DD` format. Mention the exact `prefect-common` target version.

Example:

```markdown
## [0.0.330] - 2026-05-12
- Updated prefect-common to 2.5.0.
```

## 6. Run Checks

From the product repository root:

```bash
git status --short --branch
git diff --check
rg -n "glpat-|gldt-" src/pyproject.toml src/poetry.lock
# run the product-specific unit test command
```

The token scan must return no matches.

If the update is paired with code changes that use new `prefect-common` APIs,
also update and run direct unit tests for the changed or mocked functions.

## 7. Commit

For a dependency-only PCUP, stage only these files:

```bash
git add CHANGELOG.md version.txt src/pyproject.toml src/poetry.lock
```

Commit with the target version in the message:

```bash
git commit -m "Update prefect-common to <version>"
```

If product code changed because the new `prefect-common` API requires it, include
those code files only when they are inseparable from the dependency update.
Otherwise, prefer a second focused commit.

## 8. Verify CAP And Push

Verify CAP ancestry again:

```bash
git merge-base --is-ancestor origin/main feature
git merge-base --is-ancestor origin/uat feature
```

Both commands must exit successfully.

Push the CAP `feature` branch:

```bash
git push origin feature:feature
```

Open or update the `feature -> main` merge request. Merge it with a normal merge
commit:

```text
Squash commits: OFF
Rebase: OFF
Merge method: normal merge commit
```

## Notes

- Network or VPN access to GitLab and PyPI may be required.
- Use the real deploy token only as a temporary local edit.
- Restore `${PREFECT_COMMON_TOKEN}` in both `pyproject.toml` and `poetry.lock`
  before committing.
- Never commit, push, paste into changelogs, or include in merge requests the
  real deploy token.
- `poetry.lock` is tracked in product repositories, so token cleanup there is
  mandatory.
- Do not edit dependency versions directly in `poetry.lock`.
- Do not update multiple products in one product repository commit.
- Do not squash the CAP merge request after a PCUP change.

## Troubleshooting

If authentication fails:

- check that the temporary deploy token is valid
- verify VPN and network access to the GitLab instance

If Poetry cannot resolve the GitLab host:

- connect to the required VPN
- retry `git ls-remote <prefect-common-repo-url>`
- retry `poetry lock`

If `poetry lock` fails:

- check that the requested tag exists
- check that the repository URL in `pyproject.toml` is correct
- try `poetry lock --no-update` only when the goal is to lock without dependency
  updates

If `poetry install` cannot reach PyPI:

- verify internet access
- retry with VPN connected if required

If you need to inspect what is installed:

```bash
poetry show
poetry show prefect-common
```

If a runtime failure appears after the update:

- confirm that the deployed image includes the updated `pyproject.toml` and
  `poetry.lock`
- inspect flow logs for the exact `prefect-common` API call and assumptions
- rollback by reverting the PCUP commit on the CAP `feature` branch, preserving
  merge history rather than resetting shared history
