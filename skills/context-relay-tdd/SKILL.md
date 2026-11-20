---
name: context-relay-tdd
description: Audit a repository, write the findings to a durable work queue, then fix them one test-first item at a time in a way that survives context resets and handoffs between sessions or agents. Use when asked to "audit and fix", clean up a codebase over many sessions, work through a backlog of bugs or debt, or resume a relay already started (a RELAY.md exists in the repo root).
---

# Context relay TDD

Long cleanup jobs outlive any single context window. This skill keeps all state in files in the
repo, so any session can stop at any point and the next one (you after a reset, another agent,
or a human) picks up exactly where it left off. Each fix is driven by a failing test first.

## The relay file

All state lives in `RELAY.md` at the repo root. Nothing important stays only in your context.

```markdown
# Relay

Goal: <one line from the user>
Test command: <exact command that runs the suite>
Baseline: <pass/fail counts on first run, date>

## Queue
- [ ] R1 <short title> — <file:line> — <why it's wrong> — <how a test shows it>
- [ ] R2 ...

## In progress
R3 — step: red | green | refactor — notes: <what you just did, what's next>

## Done
- [x] R0 <title> — test: <test name> — commit: <sha>

## Skipped
- R4 — <reason: needs product decision / can't reproduce / out of scope>
```

## Starting or resuming

1. If `RELAY.md` exists, read it first and resume from **In progress**, or take the next
   **Queue** item. Do not re-audit.
2. If it does not exist, run the audit (below), then create it.
3. Always run the test command before touching code and record the result. If the suite is
   already red, write that down as the baseline; never "fix" pre-existing failures silently.

## Audit

Find real defects and risks, not style nits. Look for:

- bugs: wrong conditions, off-by-one, unhandled errors, null paths, races, bad parsing;
- untested critical paths (entry points, money, auth, data writes);
- dead or duplicated code that hides bugs;
- inconsistent behavior across similar functions.

For each finding, write one queue line with a location, why it's wrong, and how a test would
show it. Order the queue by user impact, then by how cheap it is to fix. If a finding can't be
shown by a test, it goes in **Skipped** with the reason, not in the queue.

Show the user the queue before fixing anything if they're present; otherwise proceed.

## Per-item loop

Do one item end to end before starting another.

1. **Move it to In progress** with `step: red` and save the file.
2. **Red.** Write the smallest test that fails because of the defect. Run it; confirm it fails
   for the stated reason, not an import error or typo. Record the test name.
3. **Green.** Make the smallest change that passes it. Run the full suite. Nothing that was
   passing at baseline may fail.
4. **Refactor** only if it removes duplication you touched; rerun the suite.
5. **Commit** test and fix together with a message naming the item (`R3: reject empty ids`).
6. **Move it to Done** with the test name and commit sha. Clear **In progress**. Save.

Update `RELAY.md` at every step change, before doing the step's work. If the context resets
mid-step, the notes must be enough to continue without guessing.

## Rules

- One item, one commit. Never batch fixes.
- If a fix turns out to need a design decision, stop that item, move it to **Skipped** with the
  question, and take the next one.
- If you discover a new defect while fixing, add it to the end of the queue; don't chase it.
- Never weaken or delete an existing test to get green. If an existing test is wrong, that is
  its own queue item.
- When the queue is empty, run the suite one last time and write a short summary at the top of
  `RELAY.md`: items done, skipped and why, final test counts.

## Handoff

When stopping for any reason, make sure `RELAY.md` is saved, then tell the user in two lines:
what got done this session, and what the next item is.
