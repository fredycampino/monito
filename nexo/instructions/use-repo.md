## Repository workflows

Follow `docs/workflows.md` and the applicable CI checks for feature, PR, release,
publish and deploy work.

### Pull requests

Normally use the Skiller `@pr` agent/flow to prepare and open pull requests,
rather than reproducing its procedure manually with Git and `gh`.

- Inspect the working tree and preserve existing changes.
- Read the current `@pr` contract and declared inputs before invoking it; do not
  guess arguments or assume it is available.
- Pass the repository, branches and requested scope explicitly as supported.
- Feature PRs target `main`, contain exactly one commit directly on top of the
  current `origin/main`, and add a meaningful `Unreleased` changelog entry.
- A request to prepare a PR authorizes the preparation required by the documented
  procedure, not an unrelated merge, release or deployment.
- Verify the flow result and report the PR URL, checks and remaining blockers.

If `@pr` is unavailable or blocked, report the specific issue and agree on a
manual fallback before substituting another procedure. Never change accounts,
credentials or permissions without authorization.
