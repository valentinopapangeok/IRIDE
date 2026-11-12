# CAP Protocol

CAP means "Conflict Avoidance Protocol". Use it before starting or reapplying work on any product branch.

## Goal

Avoid repeated `main -> uat` conflicts by making every product change on a fresh local branch named exactly `feature` that already contains both `origin/main` and `origin/uat` history.

The only supported branch name and flow is:

```text
origin/main + origin/uat -> feature -> main -> uat
```

Do not use task-specific branch names such as `fix/...`, `docs/...`, or
`feature/<name>` for CAP product changes. The branch must be named exactly
`feature`.

Do not squash or rebase the merge requests in this flow. The merge commits are required because Git must preserve the `uat` parent history. If the `feature -> main` MR is squashed, the files may look correct on `main`, but `main -> uat` can report the same conflicts again.

## Commands

Run all commands inside the target product repository, for example `svc_s5-02-10`.

Start from a clean working tree:

```bash
git status --short --branch
```

If there are unrelated local changes, stop and preserve them before continuing. Do not mix unrelated changes into the CAP branch.

Fetch the current protected branches:

```bash
git fetch origin main
git fetch origin uat
git fetch origin feature || true
```

Always delete any old local feature branch before recreating it. The new product
branch must be named exactly `feature`; do not keep or create task-specific
feature names such as `feature/foo`, `feature-foo`, or `fix/foo`. Preserve only
protected/base branch names such as `main`, `uat`, and `prod`. First leave the
branch if a feature branch is currently checked out, then delete stale feature
branches:

```bash
git checkout --detach origin/main
git branch -D feature || true
# Also delete any local task-specific feature branches, for example:
for b in $(git branch --format='%(refname:short)' --list 'feature*'); do git branch -D "$b"; done
```

If a stale remote `feature` branch exists and is not the branch you intend to keep, delete it before recreating the branch. Do not create or push any remote feature branch name other than exactly `feature`:

```bash
git push origin --delete feature || true
```

Create a fresh `feature` branch from current `origin/main`:

```bash
git checkout -B feature origin/main
git branch --unset-upstream
```

Merge `origin/uat` into `feature` before applying product changes:

```bash
git merge origin/uat
```

If conflicts appear, resolve them locally. Keep the current `main`/feature-side product changes unless `uat` has newer release entries or environment-specific changes that are not already in `main`; preserve those `uat` changes intentionally.

Verify that no real conflict markers remain:

```bash
rg -n "<<<<<<<|>>>>>>>" .
```

Apply your product code changes after the `origin/uat` merge and conflict resolution. Every product change must include:

- a `version.txt` patch bump
- a matching top-of-file `CHANGELOG.md` entry using the current date in `YYYY-MM-DD` format
- direct unit test updates when a changed function is called or mocked by tests

Run the relevant checks:

```bash
git status --short --branch
git diff --check
# run the product-specific unit test command
```

Stage and commit the resolved merge plus your product changes. This can be done from the PyCharm UI, or with the command line:

```bash
git add <changed-files>
git commit -m "<product change summary>"
```

Verify `feature` contains both histories:

```bash
git merge-base --is-ancestor origin/main feature
git merge-base --is-ancestor origin/uat feature
```

Both commands must exit successfully.

Push `feature`:

```bash
git push origin feature:feature
```

If the push is rejected because an old remote `feature` branch exists, use force-with-lease:

```bash
git push --force-with-lease origin feature:feature
```

Open the `feature -> main` merge request. Merge it with a normal merge commit:

```text
Squash commits: OFF
Rebase: OFF
Merge method: normal merge commit
```

After `feature -> main` is merged, verify that `origin/main` contains `origin/uat` history:

```bash
git fetch origin main
git merge-base --is-ancestor origin/uat origin/main
```

This command must exit successfully. If it fails, the MR was likely squashed or rebased, and the conflict-resolution history was lost.

Only after that, open or retry the `main -> uat` merge request. Merge `main -> uat` without squashing commits.

After the `main -> uat` merge succeeds, delete the remote `feature` branch.
