# GitHub Repository Setup Guide

**Repository:** elkins/analysis
**Date:** 2025-12-08
**Purpose:** Configure branch protection and permissions for proper PR workflow

---

## Issue: Cannot Approve Own Pull Request

**Problem:** GitHub prevents you from approving your own PR by default when branch protection is enabled.

**Why this happens:**
- GitHub's branch protection rules require approval from reviewers
- The PR author cannot approve their own PR (security/quality control)
- You need either: (1) another reviewer, OR (2) adjust protection settings for solo development

---

## Solutions

### Option A: Solo Developer Workflow (Recommended for Your Case)

Since you're the primary/solo developer, configure branch protection to allow self-merge:

#### Steps to Configure:

1. **Go to Repository Settings**
   - Navigate to: https://github.com/elkins/analysis/settings
   - Click "Branches" in left sidebar

2. **Add Branch Protection Rule for `main`**
   - Click "Add branch protection rule"
   - Branch name pattern: `main`

3. **Configure Protection Settings**

   **Recommended settings for solo development:**

   - [x] **Require a pull request before merging**
     - [x] Require approvals: `0` ← **Key setting for solo work**
     - [ ] Dismiss stale pull request approvals when new commits are pushed
     - [ ] Require review from Code Owners

   - [x] **Require status checks to pass before merging** (optional)
     - Search for and select any CI checks (if you have them)
     - [ ] Require branches to be up to date before merging

   - [ ] **Require conversation resolution before merging** (optional)

   - [x] **Require signed commits** (optional, recommended)

   - [x] **Require linear history** (optional, keeps history clean)

   - [ ] **Require deployments to succeed before merging** (skip)

   - [x] **Do not allow bypassing the above settings** (recommended)

   - **Rules applied to everyone including administrators:**
     - [ ] Allow force pushes (keep unchecked)
     - [ ] Allow deletions (keep unchecked)

4. **Save Changes**
   - Click "Create" or "Save changes"

#### After Setup:

You can now merge your own PRs without external approval:

```bash
# Navigate to your PR
# https://github.com/elkins/analysis/pull/1

# Click "Merge pull request" button
# Confirm merge
```

---

### Option B: Add Collaborators (For Team Development)

If you want proper code review from others:

#### Steps:

1. **Add Collaborators**
   - Go to: https://github.com/elkins/analysis/settings/access
   - Click "Add people"
   - Enter GitHub username or email
   - Choose role: "Write" (can approve PRs) or "Admin" (full access)

2. **Configure Branch Protection**
   - Same as Option A, but set:
   - Required approvals: `1` (or `2` for critical changes)

3. **PR Workflow**
   - You create PR
   - Collaborator reviews and approves
   - You merge after approval

---

### Option C: Bypass Protection (Not Recommended)

You can give yourself bypass permissions, but this defeats the purpose of PRs:

**Settings:**
- In branch protection rule:
  - Check "Do not allow bypassing the above settings"
  - **Uncheck** "Include administrators" under restrictions

**Why not recommended:**
- Removes safety checks
- Defeats purpose of PR workflow
- Easy to accidentally merge bad code

---

## Current Situation Analysis

Based on your repository, you likely have one of these scenarios:

### Scenario 1: No Branch Protection Set Up Yet

**Symptoms:**
- You can push directly to `main`
- No PR approval required

**Solution:**
- Set up Option A (solo developer workflow)
- This adds PR discipline without blocking yourself

### Scenario 2: Branch Protection Enabled, Requires Approval

**Symptoms:**
- PR shows "Review required"
- "Merge pull request" button is disabled
- Message: "This pull request requires approvals before it can be merged"

**Solution:**
- Either:
  - Add collaborator (Option B)
  - Change required approvals to `0` (Option A)
  - Use repository admin override (if you're admin)

### Scenario 3: CODEOWNERS File Exists

**Symptoms:**
- PR requires review from specific people
- CODEOWNERS file exists in repo

**Solution:**
- Check for `.github/CODEOWNERS` file
- Remove it or add yourself as owner

---

## Quick Fix Commands

### Check Current Protection Status

Using GitHub CLI:

```bash
# Install GitHub CLI if needed
brew install gh  # macOS
# or: https://cli.github.com/

# Authenticate
gh auth login

# Check branch protection
gh api repos/elkins/analysis/branches/main/protection

# If it returns 404, no protection is set up
# If it returns JSON, protection exists
```

### Set Branch Protection (via GitHub CLI)

```bash
# Enable basic protection (solo developer)
gh api repos/elkins/analysis/branches/main/protection \
  -X PUT \
  -F required_pull_request_reviews[required_approving_review_count]=0 \
  -F required_pull_request_reviews[dismiss_stale_reviews]=false \
  -F enforce_admins=false \
  -F required_linear_history=true \
  -F allow_force_pushes=false \
  -F allow_deletions=false

# Note: GitHub CLI for branch protection has limitations
# Web UI is recommended for full control
```

---

## Step-by-Step: Merge Your Current PR

Assuming you're the only developer and want to merge PR #1:

### Method 1: Via GitHub Web UI

1. **Navigate to PR**
   - Go to: https://github.com/elkins/analysis/pull/1

2. **Check Status**
   - If button says "Merge pull request" - click it!
   - If button is disabled - follow steps below

3. **If Disabled - Adjust Settings**
   - Go to Settings → Branches → Branch protection rules for `main`
   - Change "Required approving reviews" to `0`
   - Save changes
   - Go back to PR
   - Click "Merge pull request"

4. **Choose Merge Strategy**
   - **Squash and merge** (recommended - clean history)
   - Merge commit (preserves all commits)
   - Rebase and merge (linear history)

5. **Confirm**
   - Click "Confirm squash and merge" (or chosen option)
   - Delete branch when prompted (optional)

### Method 2: Via GitHub CLI

```bash
# Check if you can merge
gh pr view 1

# If mergeable, merge it
gh pr merge 1 --squash --delete-branch

# Options:
#   --squash    Squash commits (recommended)
#   --merge     Regular merge commit
#   --rebase    Rebase and merge
#   --delete-branch  Delete feature branch after merge
```

### Method 3: Via Command Line (Bypass GitHub Checks)

**Warning:** Only use if GitHub is blocking you incorrectly.

```bash
# Fetch latest
git fetch origin

# Checkout main
git checkout main
git pull origin main

# Merge feature branch
git merge --squash feature/c-extension-elimination-tdd

# Commit with descriptive message
git commit -m "Merge: TDD C Extension Elimination - Contour Module

Complete implementation of contour module conversion from C to Python
with comprehensive testing and zero-risk deployment strategy.

- 45 tests passing (26 TDD + 7 Numba + 12 integration)
- Performance: 0.17-0.22s for 512×512 (meets <1s target)
- Automatic fallback to C extension
- 4,011 lines added (implementation + tests + docs)

Closes #1"

# Push to main
git push origin main

# Delete feature branch
git branch -d feature/c-extension-elimination-tdd
git push origin --delete feature/c-extension-elimination-tdd
```

---

## Recommended Setup for Your Repository

Based on you being the primary developer:

### Initial Setup (Do Once)

```yaml
Branch Protection for 'main':
  ✓ Require pull request before merging
    - Required approvals: 0
  ✓ Require linear history
  ✓ Do not allow force pushes
  ✓ Do not allow deletions
  ✗ Do not bypass settings for admins (allow yourself to override if needed)
```

### Benefits

- ✅ Maintains PR discipline (all changes go through PRs)
- ✅ Clean Git history with PR references
- ✅ Can merge your own PRs without waiting
- ✅ Can add reviewers later when team grows
- ✅ Easy rollback (revert PR merges)

### Future Growth

When you add collaborators:

1. Update required approvals from `0` to `1`
2. Add CODEOWNERS file (optional)
3. Enable status checks (CI/CD)
4. Require conversation resolution

---

## Troubleshooting

### "Review required" but I'm the only developer

**Fix:** Set required approvals to `0` in branch protection settings.

### "This branch has not been deployed" blocking merge

**Fix:** Disable "Require deployments to succeed" in branch protection.

### Cannot find branch protection settings

**Check:**
- You must be repository owner or admin
- Go to: Settings → Branches (not Settings → General)
- Make sure you're on the correct repository

### Changes not taking effect

**Try:**
- Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
- Wait 1-2 minutes (GitHub caching)
- Check protection rule is for exact branch name `main`

---

## Security Best Practices

Even as solo developer:

1. **Always use PRs** - Never push directly to `main`
2. **Review your own code** - Read the diff before merging
3. **Run tests locally** - Verify before creating PR
4. **Write good PR descriptions** - Future you will thank you
5. **Keep branches short-lived** - Merge within 1-2 weeks
6. **Delete merged branches** - Keep repository clean

---

## Quick Reference Table

| Scenario | Required Approvals | Allow Admin Bypass |
|----------|-------------------|-------------------|
| Solo development | 0 | Yes (unchecked) |
| Small team (2-3) | 1 | No (checked) |
| Large team | 2 | No (checked) |
| Critical project | 2+ | No (checked) |
| Public OSS | 1+ | No (checked) |

---

## Next Steps

1. **Configure branch protection** (Option A recommended)
2. **Merge PR #1** using one of the methods above
3. **Set up CI/CD** (optional - run tests automatically)
4. **Document workflow** in CONTRIBUTING.md
5. **Add collaborators** when team grows

---

## Additional Resources

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub PR Review Documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests)
- [CCPN Analysis Git Branch Strategy](Git_Branch_Strategy.md)

---

**Questions?** Open an issue or check GitHub documentation.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
