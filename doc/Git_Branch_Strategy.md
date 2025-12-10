# Git Branch Strategy for CCPN Analysis Repository

**Version:** 1.0
**Date:** 2025-12-08
**Status:** Active

---

## Overview

This document establishes the Git branching strategy, naming conventions, pull request workflow, and merge policies for the CCPN Analysis repository modernization project.

**Key Principles:**
1. All changes must go through feature branches
2. All branches require Pull Request (PR) review before merging to `main`
3. Main branch is protected and always deployable
4. Feature branches enable parallel development with minimal conflicts

---

## Branch Structure

### Main Branch

**Branch:** `main`
**Purpose:** Production-ready code
**Protection:**
- ✅ Require PR reviews before merging
- ✅ All tests must pass
- ✅ No direct commits (except emergencies)
- ✅ Linear history preferred

### Feature Branches

All development work happens in feature branches following the naming convention below.

---

## Development Streams

The modernization project follows four parallel development streams:

### Stream 1: Python 3 Compatibility
**Focus:** Modernizing Python 2 code to Python 3
**Branch prefix:** `fix/` or `refactor/`
**Sequential:** Yes (tasks depend on each other)

**Example branches:**
- `fix/standarderror-exceptions` - Replace StandardError with Exception
- `refactor/unicode-strings` - Update string handling for Python 3
- `test/python3-smoke-tests` - Add Python 3 compatibility tests

**Merge order:** Sequential (maintain dependency chain)

### Stream 2: C Extension Elimination
**Focus:** Converting C extensions to Python + NumPy + Numba
**Branch prefix:** `feature/`
**Sequential:** No (each module independent)

**Example branches:**
- `feature/c-extension-elimination-tdd` - Contour module conversion
- `feature/peak-module-conversion` - Peak finding/fitting module
- `feature/library-module-conversion` - Utility functions module

**Merge order:** Independent (can merge in any order)

### Stream 3: Performance Optimization
**Focus:** Profiling and optimizing critical paths
**Branch prefix:** `perf/`
**Sequential:** Mostly (some parallelism possible)

**Example branches:**
- `perf/testing-infrastructure` - Set up benchmarking framework
- `perf/contour-profiling` - Profile contour generation
- `perf/numba-optimization` - JIT compilation optimization

**Merge order:** Sequential with some parallel work

### Stream 4: Validation & Documentation
**Focus:** Scientific validation and documentation
**Branch prefix:** `docs/` or `validation/`
**Sequential:** Yes

**Example branches:**
- `validation/test-datasets` - Prepare validation datasets
- `validation/scientific-results` - Verify numerical accuracy
- `docs/user-guide-python3` - Update documentation for Python 3

**Merge order:** Sequential

---

## Branch Naming Convention

### Format

```
<type>/<scope>-<description>
```

### Types

| Type | Purpose | Examples |
|------|---------|----------|
| `feature/` | New features or major changes | `feature/contour-module` |
| `fix/` | Bug fixes | `fix/memory-leak-spectrum` |
| `refactor/` | Code refactoring (no behavior change) | `refactor/spectrum-class` |
| `perf/` | Performance improvements | `perf/contour-optimization` |
| `test/` | Test additions or modifications | `test/integration-suite` |
| `docs/` | Documentation only | `docs/api-reference` |
| `validation/` | Scientific validation work | `validation/numerical-accuracy` |
| `hotfix/` | Emergency production fixes | `hotfix/critical-crash` |

### Scope

Brief descriptor of the area being changed:
- Module name: `contour`, `peak`, `spectrum`
- Component: `gui`, `core`, `api`
- Feature: `tdd-infrastructure`, `numba-optimization`

### Description

Concise description using kebab-case (lowercase with hyphens):
- `c-extension-elimination`
- `python3-compatibility`
- `memory-leak-fix`

### Examples

✅ **Good:**
- `feature/c-extension-elimination-tdd`
- `fix/spectrum-display-crash`
- `perf/contour-numba-optimization`
- `docs/integration-guide`

❌ **Bad:**
- `my-changes` (no type or scope)
- `Feature/Contour` (wrong capitalization)
- `fix-stuff` (too vague)
- `georgework` (not descriptive)

---

## Pull Request Workflow

### Creating a Feature Branch

```bash
# Start from up-to-date main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name

# Work on your changes...
git add .
git commit -m "Your commit message"

# Push to remote
git push origin feature/your-feature-name
```

### Creating a Pull Request

1. **Push your branch** to the remote repository
2. **Create PR** on GitHub:
   - Base branch: `main`
   - Compare branch: `feature/your-feature-name`
3. **Fill out PR template** with:
   - Summary of changes
   - Testing performed
   - Documentation updates
   - Related issues

### PR Review Requirements

**Before requesting review:**
- ✅ All tests pass locally
- ✅ Code follows project style guidelines
- ✅ Documentation updated (if needed)
- ✅ No merge conflicts with `main`

**Review checklist:**
- [ ] Code quality and readability
- [ ] Test coverage adequate
- [ ] No security vulnerabilities introduced
- [ ] Performance impact considered
- [ ] Documentation clear and accurate

**Approval requirements:**
- **Minor changes** (docs, small fixes): 1 reviewer
- **Major changes** (new features, refactors): 2 reviewers
- **Critical changes** (performance, C conversions): 2+ reviewers + validation

### Merging Strategy

**Preferred method:** Squash and merge (for clean history)

```bash
# After PR approval
git checkout main
git pull origin main
git merge --squash feature/your-feature-name
git commit -m "Descriptive commit message summarizing PR"
git push origin main
```

**Alternative:** Merge commit with `--no-ff` (preserves branch history)

```bash
git checkout main
git pull origin main
git merge --no-ff feature/your-feature-name
git push origin main
```

**When to use each:**
- **Squash merge:** Feature has many small commits, want clean history
- **Merge commit:** Want to preserve detailed commit history for complex features

### After Merge

```bash
# Delete local branch
git branch -d feature/your-feature-name

# Delete remote branch
git push origin --delete feature/your-feature-name
```

---

## Conflict Prevention

### File Ownership by Stream

| Stream | Primary Files | Conflict Risk |
|--------|---------------|---------------|
| Stream 1 (Python 3) | All `.py` files (syntax) | Medium |
| Stream 2 (C→Python) | New files in `c_replacement/` | Low |
| Stream 3 (Performance) | Benchmark scripts, optimization | Low |
| Stream 4 (Validation) | Test files, documentation | Low |

### Priority Order (if conflicts occur)

1. **Stream 1** (Python 3 compatibility) - Highest priority
2. **Stream 3** (Performance optimization)
3. **Stream 4** (Validation & docs)
4. **Stream 2** (C conversions) - Lowest conflict risk

### Conflict Resolution

If your PR has conflicts:

```bash
# Update your branch with latest main
git checkout your-feature-branch
git fetch origin
git rebase origin/main

# Resolve conflicts
# ... edit files ...
git add resolved-files
git rebase --continue

# Force push (rebase rewrites history)
git push origin your-feature-branch --force-with-lease
```

**Note:** Always use `--force-with-lease` instead of `--force` for safety.

---

## Multi-Developer Workflows

### Solo Developer

**Workflow:**
1. Work on feature branches
2. Create PR (self-review or get optional peer review)
3. Merge after tests pass
4. Delete branch

**Benefits:** Maintains PR history, enables easy rollback

### Small Team (2-3 Developers)

**Recommended assignment:**
- **Developer A:** Stream 1 (Python 3 compatibility)
- **Developer B:** Stream 2 (C extension conversions)
- **Developer C:** Stream 3 & 4 (Performance + Validation)

**Coordination:**
- Daily standups or async updates
- PR reviews for cross-stream changes
- Shared testing infrastructure

### Remote Contributors

**Workflow:**
1. Fork repository
2. Create feature branch in fork
3. Submit PR from fork to main repository
4. Wait for review and approval
5. Maintainer merges after approval

**Review requirements:**
- At least 1 maintainer approval required
- All CI tests must pass
- Documentation must be updated

---

## Pull Request Guidelines

### PR Size

**Ideal:** 200-400 lines changed
**Maximum:** 1000 lines (split if larger)

**Why:** Smaller PRs are easier to review and less likely to introduce bugs.

### PR Title Format

```
<type>: <brief description>
```

**Examples:**
- `feature: Add Numba-optimized contour module`
- `fix: Resolve memory leak in spectrum display`
- `perf: Optimize peak finding with Numba`
- `docs: Add integration guide for C replacements`

### PR Description Template

```markdown
## Summary
Brief description of what this PR does.

## Changes
- List of key changes
- Another change
- etc.

## Testing
- [ ] All existing tests pass
- [ ] New tests added (if applicable)
- [ ] Manual testing performed

## Documentation
- [ ] Code comments updated
- [ ] User documentation updated (if needed)
- [ ] API documentation updated (if needed)

## Performance Impact
Describe any performance implications (positive or negative).

## Related Issues
Closes #123
Relates to #456
```

---

## Special Cases

### Emergency Hotfixes

For critical production bugs:

```bash
# Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-issue-description

# Fix the issue
git commit -am "Hotfix: description"

# Create PR with "HOTFIX" label
# Request immediate review
# Merge after single approval
```

**Hotfix criteria:**
- Production is broken
- Data loss risk
- Security vulnerability

### Documentation-Only Branches

Documentation can have a longer-lived branch:

```bash
git checkout -b documentation/ongoing-updates

# Multiple commits over time
# No PR required until ready for review
# Merge when documentation milestone reached
```

---

## Branch Lifecycle

### Active Development

```
main (protected)
  ├── feature/contour-module (in progress)
  ├── feature/peak-module (in progress)
  └── fix/spectrum-crash (in review)
```

### Post-Merge Cleanup

```
main (updated)
  └── feature/contour-module (deleted after merge)
```

### Stale Branch Policy

- **Inactive > 30 days:** Comment on PR asking for status
- **Inactive > 60 days:** Close PR with explanation (can reopen later)
- **Abandoned:** Delete branch after confirmation

---

## Code Review Best Practices

### For Authors

- ✅ Keep PRs focused and small
- ✅ Write clear commit messages
- ✅ Add tests for new functionality
- ✅ Update documentation
- ✅ Respond to review comments promptly
- ✅ Use draft PRs for work-in-progress

### For Reviewers

- ✅ Review within 24-48 hours
- ✅ Be constructive and specific
- ✅ Ask questions if unclear
- ✅ Test changes locally (if needed)
- ✅ Approve only when confident
- ✅ Suggest improvements, don't demand perfection

---

## GitHub Branch Protection Rules

Configure on GitHub for `main` branch:

### Required Settings

- [x] Require pull request reviews before merging
  - Required approvals: 1 (minor) or 2 (major changes)
- [x] Require status checks to pass before merging
  - All tests must pass
- [x] Require branches to be up to date before merging
- [x] Require linear history (optional, recommended)
- [x] Do not allow force pushes
- [x] Do not allow deletions

---

## Continuous Integration (CI)

### Automated Checks (if configured)

- ✅ Run all tests
- ✅ Check code style (flake8, black)
- ✅ Security scanning
- ✅ Documentation builds
- ✅ Performance benchmarks (for perf/ branches)

### Manual Checks

- Code review by at least 1 reviewer
- Manual testing for UI changes
- Scientific validation for algorithm changes

---

## Quick Reference

### Common Commands

```bash
# Create feature branch
git checkout -b feature/my-feature

# Update branch with latest main
git fetch origin
git rebase origin/main

# Push branch
git push origin feature/my-feature

# Create PR (using GitHub CLI)
gh pr create --base main --head feature/my-feature

# After merge, cleanup
git checkout main
git pull origin main
git branch -d feature/my-feature
git push origin --delete feature/my-feature
```

### GitHub CLI PR Commands

```bash
# Install GitHub CLI
brew install gh  # macOS
# or download from https://cli.github.com/

# Authenticate
gh auth login

# Create PR
gh pr create --title "Your PR title" --body "Description"

# List PRs
gh pr list

# Check PR status
gh pr status

# Merge PR
gh pr merge --squash  # or --merge or --rebase
```

---

## Examples from Current Project

### Example 1: Contour Module Conversion

```bash
# Create feature branch
git checkout -b feature/c-extension-elimination-tdd

# Implement TDD cycle (RED → GREEN → REFACTOR)
git commit -am "feat: Add comprehensive TDD infrastructure"
git commit -am "feat: Implement contour.py (TDD GREEN)"
git commit -am "feat: Add Numba optimization (TDD REFACTOR)"
git commit -am "feat: Add integration infrastructure"

# Push and create PR
git push origin feature/c-extension-elimination-tdd
gh pr create --base main --title "TDD C Extension Elimination: Contour Module"

# After review and approval
gh pr merge --squash
```

### Example 2: Documentation Update

```bash
# Create documentation branch (can be long-lived)
git checkout -b documentation/git-workflow

# Add documentation over time
git commit -am "docs: Add Git branching strategy"
git commit -am "docs: Add integration guide"
git commit -am "docs: Add API reference"

# When ready, create PR
git push origin documentation/git-workflow
gh pr create --base main

# After review
gh pr merge --squash
```

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-08 | Initial version with PR workflow | Claude + George Elkins |

---

## References

- Based on: [ccpnmr2.4 Git Branch Strategy](https://github.com/elkins/ccpnmr2.4/blob/development/Git_Branch_Strategy.md)
- GitHub Flow: https://docs.github.com/en/get-started/quickstart/github-flow
- Git Branching Model: https://nvie.com/posts/a-successful-git-branching-model/

---

**Questions or suggestions?** Open an issue or submit a PR to update this document!

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
