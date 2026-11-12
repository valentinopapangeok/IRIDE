# TBP - TFS Backup Push Protocol

## Goal

TBP copies the authoritative GitLab `main` branch of every S5-02 repository to
the corresponding TFS `main` branch.

GitLab is always the source of truth. TFS is a backup destination. Never merge
TFS file changes into GitLab as part of TBP.

The GitLab and TFS servers require different OpenVPN connections. Refresh all
GitLab references first, disconnect the GitLab OpenVPN profile, connect the TFS
OpenVPN profile, and then perform the backup. Confirm that only the intended
profile is active before each network phase.

## Legal Purpose and Proprietary Ownership

TBP creates an authorized legal backup of the S5-02 source code for the client
that owns the proprietary rights to the code. The TFS repositories are the
client-controlled archival destination. GitLab remains the operational source
of truth, while TFS provides an independently hosted copy that supports
ownership protection, continuity, recovery, and evidentiary traceability.

The backup does not transfer, assign, license, or alter ownership of the source
code. Creating a TFS copy does not authorize reuse, disclosure, publication,
distribution, or modification outside the applicable contract and the
client's written instructions.

Every TBP execution must comply with these controls:

1. The operator must be authorized to access both the GitLab source and the
   client TFS destination.
2. The source and destination repository mapping must be confirmed before any
   push. Code must never be copied to a personal, public, or unapproved
   repository.
3. Only the approved `main` branch is backed up. Other branches, tags, build
   artifacts, credentials, local files, and unrelated repositories are outside
   scope unless the client explicitly authorizes them.
4. Access must use the approved OpenVPN profiles and authenticated client or
   project accounts. Credentials and access tokens must not be written into
   this protocol, shell history, source files, or backup records.
5. TFS access permissions must follow least privilege. Backup repositories
   must remain private and accessible only to authorized client and project
   personnel.
6. The backup must preserve the exact GitLab file tree. The mandatory tree-hash
   verification provides integrity evidence even when the TFS bridge commit has
   a different commit SHA.
7. Every execution must produce an audit record containing the operator,
   timestamp, authorization or ticket reference, source and destination
   repositories, source and destination commits, common tree hash, result, and
   any exception.
8. Backup records and TFS history must be retained and disposed of according to
   the client's contractual retention, confidentiality, security, and
   incident-response requirements.
9. A failed or partial backup must be recorded accurately. It must never be
   reported as a completed legal backup.

TBP is a technical control supporting the client's proprietary ownership and
backup obligations. Contractual or regulatory questions outside this procedure
must be referred to the responsible client, contract, security, or legal
authority.

## Repository Mapping

| Local repository | TFS repository |
| --- | --- |
| `svc_S5-02` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02` |
| `svc_s5-02-01` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-01` |
| `svc_s5-02-02` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-02` |
| `svc_s5-02-03` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-03` |
| `svc_s5-02-04` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-04` |
| `svc_s5-02-05` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-05` |
| `svc_s5-02-06` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-06` |
| `svc_s5-02-07` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-07` |
| `svc_s5-02-08` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-08` |
| `svc_s5-02-09` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-09` |
| `svc_s5-02-10` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-10` |
| `svc_s5-02-11` | `https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-11` |

## Safety Rules

1. Push only `main`. Do not use `git push --mirror` or `git push --all`.
2. Push `origin/main`, not the local `main` branch. Local branches may be stale.
3. Refresh `origin/main` while connected to the GitLab OpenVPN profile before
   switching to the TFS OpenVPN profile.
4. Do not change the `origin` URL or upstream tracking configuration.
5. Do not force-push. TFS does not grant the required `ForcePush` permission.
   Use the verified bridge merge procedure.
6. After every push, prove that the TFS and GitLab trees are identical.
7. The bridge commit gives TFS a different commit SHA while preserving exactly
   the same files as GitLab. Tree equality, not commit equality, is the
   required backup check.

## Phase 1: Refresh GitLab

Connect to the GitLab OpenVPN profile. From the MKPL directory, fetch `main`
for every repository:

```bash
for d in svc_S5-02 svc_s5-02-{01,02,03,04,05,06,07,08,09,10,11}; do
  git -C "$d" fetch origin main || exit 1
done
```

Record the source commits used for the backup:

```bash
for d in svc_S5-02 svc_s5-02-{01,02,03,04,05,06,07,08,09,10,11}; do
  printf '%s ' "$d"
  git -C "$d" show -s --format='%H %cI %s' origin/main
done
```

If any fetch fails, stop. Do not back up a mixture of fresh and stale GitLab
references unless that partial scope is explicitly intended and recorded.

## Phase 2: Connect to TFS and Configure Remotes

Disconnect the GitLab OpenVPN profile and connect the TFS OpenVPN profile.
Each repository uses a second remote named `tfs`. Configure it once:

```bash
git -C svc_S5-02 remote add tfs \
  https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02

for n in 01 02 03 04 05 06 07 08 09 10 11; do
  git -C "svc_s5-02-$n" remote add tfs \
    "https://tfs.irideservices.earth/SBU-GS/P22G226x_IRIDE_Service/_git/SVC_S5-02-$n"
done
```

If `tfs` already exists, verify it instead of adding it:

```bash
git -C <repository> remote get-url tfs
git -C <repository> remote -v
```

Use `git remote set-url tfs <expected-url>` only when correcting a confirmed
mistake.

## Phase 3: Refresh the TFS Branch

For each repository:

```bash
git -C <repository> fetch tfs main
```

This fetch is mandatory immediately before creating the bridge. It ensures the
bridge uses the current TFS `main` as its second parent. If TFS has no `main`
branch because the repository is empty, perform a one-time normal push of
`origin/main`; all later backups use the bridge procedure.

## Phase 4: Create and Push the Verified Bridge

The verified bridge is the only standard TBP synchronization method.

The bridge commit has two parents—GitLab `origin/main` and TFS `main`—but its
tree is taken directly from GitLab. This makes the update a normal
fast-forward without allowing old TFS file content into the backup.

```bash
repo=<repository>

bridge=$(git -C "$repo" commit-tree 'origin/main^{tree}' \
  -p origin/main \
  -p tfs/main \
  -m 'Bridge TFS history to authoritative GitLab main') || exit 1

git -C "$repo" diff --exit-code origin/main "$bridge" || exit 1
git -C "$repo" merge-base --is-ancestor tfs/main "$bridge" || exit 1

git -C "$repo" push tfs "${bridge}:refs/heads/main"
```

The first check proves that the bridge files exactly match GitLab. The second
proves that the push contains the current TFS history and can be a
fast-forward.

Do not use a normal content merge for TBP. Choosing GitLab during visible
conflicts does not prevent non-conflicting, obsolete TFS changes from entering
the result. `commit-tree` with `origin/main^{tree}` guarantees GitLab content.

The bridge commit exists only in TFS history and the local object database. It
does not update any local branch or GitLab. Create a new bridge commit for every
future backup.

## Phase 5: Mandatory Verification

Fetch the result and compare complete trees:

```bash
git -C <repository> fetch tfs main
git -C <repository> diff --exit-code origin/main tfs/main
```

No output and exit code `0` means the file trees match.

For an auditable hash comparison:

```bash
git -C <repository> rev-parse 'origin/main^{tree}' 'tfs/main^{tree}'
```

Both tree hashes must be identical. Record:

- operator identity;
- authorization, change, or ticket reference;
- repository name;
- GitLab `origin/main` commit;
- TFS `main` commit;
- common tree hash;
- timestamp;
- method: verified bridge;
- result and any exception or failed repository.

## Failure Handling

### `Could not resolve host`

Confirm the correct OpenVPN profile is active. GitLab and TFS require different
OpenVPN profiles.

### `TF401027: You need the Git 'ForcePush' permission`

The wrong command was used. TBP must not force-push. Fetch `tfs/main`, create a
new verified bridge, and push the bridge normally.

### Non-fast-forward rejection during bridge push

TFS changed after the bridge was created. Fetch `tfs/main`, discard the
unreferenced bridge commit, create a new bridge with the refreshed TFS parent,
verify it, and retry.

### Tree verification fails

Treat the backup as invalid. Do not continue to the next repository until the
source ref, pushed ref, and bridge construction are understood.

## Completion Criteria

TBP is complete only when:

1. every intended GitLab `origin/main` was freshly fetched;
2. every intended TFS `main` was updated;
3. every TFS tree hash equals its GitLab tree hash; and
4. the audit record identifies the operator, authorization reference, source
   and destination repositories, source and destination commits, common tree
   hash, method, result, exceptions, and time for every repository.
