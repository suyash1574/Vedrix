# Safe recurring GitHub synchronization

Autergo uses `scripts/sync-github.sh` for recurring synchronization. The script is deliberately conservative: it updates only `autergo/production-hardening`, fast-forwards from `origin`, scans tracked files for common credential patterns, runs `git diff --check`, runs the production-file validator when available, commits validated changes, and pushes only that feature branch. It never pushes directly to `main`.

## Recommended operating model

Run the script from a persistent deployment or development runner with GitHub credentials already configured. A daily or six-hour cadence is appropriate for a low-frequency synchronization process; do not use it for minute-level polling. Review the feature branch and merge through a pull request after CI passes.

```cron
# Every day at 02:15 in the runner's local timezone
15 2 * * * cd /opt/vedrix && REPO_DIR=/opt/vedrix SYNC_BRANCH=autergo/production-hardening ./Vedrix/scripts/sync-github.sh >> /var/log/vedrix-github-sync.log 2>&1
```

The runner must never store `backend/.env` in Git. Production credentials belong in the host secret manager or deployment environment. If the script finds a credential pattern in tracked files, it exits without committing or pushing.

## Rollback

To roll back a bad branch commit, revert the commit in a pull request rather than force-pushing. For an emergency local rollback:

```bash
git fetch origin autergo/production-hardening
git switch autergo/production-hardening
git revert <commit-sha>
git push origin autergo/production-hardening
```

The current implementation has been pushed to:

`https://github.com/suyash1574/Vedrix/tree/autergo/production-hardening`

A scheduled Manus task was not created because the schedule service returned a permission error in this session. The repository script and cron procedure provide the same recurring behavior on a persistent runner without requiring a full AI session for every run.
