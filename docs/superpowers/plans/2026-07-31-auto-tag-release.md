# Automatic Tag and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create one incrementing semantic-version tag and one GitHub Release whenever a pull request is merged into `master`, then publish the existing versioned container image.

**Architecture:** A new GitHub Actions workflow listens for merged pull requests and optional manual dispatches. It tags the exact merge commit, retries tag allocation if concurrent merges race, reuses an existing tag on reruns, creates idempotent GitHub Releases with generated notes, and explicitly dispatches the existing tag-aware CI/image workflow.

**Tech Stack:** GitHub Actions, Bash, Python 3, GitHub CLI

---

### Task 1: Add the release workflow

**Files:**
- Create: `.github/workflows/auto-release.yml`

- [x] **Step 1: Define the release behavior**

Create a workflow that:

- handles `pull_request_target.closed` for `master` and checks `merged == true`;
- increments the patch component of the highest `vMAJOR.MINOR.PATCH` tag;
- tags the merge commit, retries remote tag collisions, and reuses a tag already pointing at that commit;
- creates a GitHub Release with generated notes, skipping creation when that Release already exists;
- dispatches `.github/workflows/reminder-deploy.yml` at the resulting tag so its existing image-publishing job runs despite `GITHUB_TOKEN` recursion protection.

- [x] **Step 2: Validate the workflow**

Run:

```powershell
python -c "from pathlib import Path; import yaml; yaml.safe_load(Path('.github/workflows/auto-release.yml').read_text(encoding='utf-8'))"
```

Expected: exit code `0`.

- [x] **Step 3: Validate repository behavior**

Run:

```powershell
git diff --check
git diff -- .github/workflows/auto-release.yml
```

Expected: no whitespace errors; the diff contains only the requested workflow behavior and the explicit dispatch of the existing image workflow.
