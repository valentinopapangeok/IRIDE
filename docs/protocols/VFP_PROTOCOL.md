# VFP Protocol

Use this protocol when a product reaches a named version milestone and the code must be copied to the corresponding frozen fork.

For product 09 V0, the frozen fork is:

```text
https://gitlab.iride.earth/iride-marketplace/service-segment-ptk/servicesegment-lot1/service-value-chains/s5-02/containers/svc_s5-02-09-v0.git
```

## Goal

Keep the normal product repository as the active development source, and update the version fork only when the product is ready to freeze or refresh that milestone.

For V0, the fork name follows this pattern:

```text
<product-repository>-v0
```

Example:

```text
svc_s5-02-09 -> svc_s5-02-09-v0
```

## Standard Flow

Run these commands from the active product repository.

For product 09:

```bash
cd /Volumes/Extreme/IRIDE/MKPL/svc_s5-02-09
```

Start with a clean working tree:

```bash
git status --short --branch
```

If there are uncommitted changes, either commit them to the normal product repo first or stop and decide whether they belong in the freeze.

Fetch the normal product repository:

```bash
git fetch origin
```

Checkout the exact branch or commit that should become the frozen version. Usually this is the latest `main` after the product merge request has been accepted:

```bash
git checkout main
git pull --ff-only origin main
```

If the frozen version should be created from a specific commit instead, checkout that commit explicitly:

```bash
git checkout <commit-sha>
```

## Configure The Version Remote

Add the frozen fork as a separate remote. Use a clear remote name for the target milestone, such as `v0`.

For product 09 V0:

```bash
git remote add v0 https://gitlab.iride.earth/iride-marketplace/service-segment-ptk/servicesegment-lot1/service-value-chains/s5-02/containers/svc_s5-02-09-v0.git
```

If the remote already exists, update its URL instead:

```bash
git remote set-url v0 https://gitlab.iride.earth/iride-marketplace/service-segment-ptk/servicesegment-lot1/service-value-chains/s5-02/containers/svc_s5-02-09-v0.git
```

Verify the remotes:

```bash
git remote -v
```

Expected result:

```text
origin  https://gitlab.iride.earth/.../svc_s5-02-09.git (fetch)
origin  https://gitlab.iride.earth/.../svc_s5-02-09.git (push)
v0      https://gitlab.iride.earth/.../svc_s5-02-09-v0.git (fetch)
v0      https://gitlab.iride.earth/.../svc_s5-02-09-v0.git (push)
```

## Update The Frozen Fork

Push the currently checked-out commit to the frozen fork's `main` branch:

```bash
git push v0 HEAD:main
```

If `main` is protected, GitLab rejects the push with a message like:

```text
GitLab: You are not allowed to push code to protected branches on this project.
```

In that case, push a `feature` branch to the version fork and open a merge request from that branch to `main` in the version fork:

```bash
git push --force-with-lease v0 HEAD:feature
```

For product 09 V0 at commit `3c2cad8`, the command is:

```bash
git push --force-with-lease v0 HEAD:feature
```

After the push, GitLab prints a merge-request URL. Open it and create the merge request manually.

Use these fields:

- Source branch: `feature`
- Target branch: `main`
- Target project: the version fork, for example `svc_s5-02-09-v0`
- Title: `VFP: freeze product 09 V0 at <short-sha>`
- Description: `Update the V0 frozen fork for product 09 to commit <full-sha> from the active product repository.`
- Delete source branch after merge: enabled

Open the merge request, confirm that the target branch is `main` in the V0 fork, then merge it after the usual checks pass.

If GitLab rejects the push because the fork already has different commits, inspect the difference before deciding how to proceed:

```bash
git fetch v0
git log --oneline --graph --decorate HEAD..v0/main
```

If the fork must become an exact freeze of the currently checked-out product state, use:

```bash
git push --force-with-lease v0 HEAD:main
```

Do not use plain `--force`.

## Verification

After pushing, fetch the frozen fork and verify that `v0/main` points to the same commit you intended to freeze:

```bash
git fetch v0 main
git rev-parse HEAD
git rev-parse v0/main
```

The two SHAs must match.

If `main` is protected and the update went through a merge request, run this verification after the merge request has been merged.

Then verify the fork in GitLab:

- Open the version fork page.
- Confirm the latest commit SHA matches the local `git rev-parse HEAD` output.
- Confirm the branch shown is `main`.
- Confirm the fork contains the expected version, changelog, and product files.

## Product 09 V0 Quick Command Set

Use this only after the product 09 `main` branch is already the exact state that should be frozen.

```bash
cd /Volumes/Extreme/IRIDE/MKPL/svc_s5-02-09
git status --short --branch
git fetch origin
git checkout main
git pull --ff-only origin main
git remote add v0 https://gitlab.iride.earth/iride-marketplace/service-segment-ptk/servicesegment-lot1/service-value-chains/s5-02/containers/svc_s5-02-09-v0.git
git push v0 HEAD:main
git fetch v0 main
git rev-parse HEAD
git rev-parse v0/main
```

If `v0` already exists locally, replace the `git remote add v0 ...` line with:

```bash
git remote set-url v0 https://gitlab.iride.earth/iride-marketplace/service-segment-ptk/servicesegment-lot1/service-value-chains/s5-02/containers/svc_s5-02-09-v0.git
```

If the direct push to `main` is rejected because `main` is protected, use:

```bash
git push --force-with-lease v0 HEAD:feature
```

Then open the merge-request URL printed by GitLab and merge that branch into `main` in the V0 fork.

## Rules

- Freeze from a clean working tree.
- Freeze from `main` unless a specific commit SHA has been intentionally selected.
- Treat the frozen fork as a version snapshot, not as the active development repository.
- Push to the version fork through a named remote such as `v0`.
- Use `git push v0 HEAD:main` for the normal update.
- If `main` is protected, always push the selected freeze commit to the version fork's `feature` branch and merge it to `main` through GitLab.
- Use `git push --force-with-lease v0 HEAD:main` only when the fork must be overwritten to match the selected product state.
- Verify the local frozen commit SHA against `v0/main` after every update.
