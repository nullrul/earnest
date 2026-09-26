---
name: pre-pr-review
description: Run before opening or readying a PR (gh pr create / gh pr ready); runs code review, ponytail review, simplify and security review on the branch diff, then unlocks the PR gate.
---

# Pre-PR Review

1. Preflight: run `git fetch origin`. Confirm `git diff --stat origin/main...HEAD`
   is non-empty; if it is empty, stop and report it. Confirm `git status` is
   clean.

2. Run, in order, via the Skill tool, each against the branch diff
   `origin/main...HEAD`:
   - `code-review`
   - `ponytail:ponytail-review`
   - `simplify`
   - `security-review`: its built-in diff compares against the branch
     upstream, which is the branch itself once pushed. Pass the range
     explicitly: review `git diff origin/main...HEAD`.

3. For every finding: fix it or record why it is declined. Commit fixes (the
   pre-commit hook runs). If fixes were committed, re-run the reviews whose
   scope the fix touched.

4. Only when all four are clean or answered: record the reviewed HEAD with

   ```bash
   git rev-parse HEAD > "$(git rev-parse --git-dir)/pre-pr-review"
   ```

   Then report a table of review | findings | fixed | declined, and tell the
   user the PR can now be created.

Note: any new commit invalidates the marker; re-run this skill.
