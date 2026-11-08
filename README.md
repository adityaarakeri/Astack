# Astack - Adi's Skill Stack

One place to find and install every agent skill I maintain. Some live in this repo; the bigger
ones keep their own repos, history, and CI, and this catalog points at them.

Browse them with examples at [adityaarakeri.me/skills](https://adityaarakeri.me/skills/).

## Install

### Claude Code

Install any plugin in one step (Claude Code 2.1.275 or later):

```text
/plugin install humanize-content --marketplace adityaarakeri/skills
```

On older versions, add the marketplace once and install by `name@adityaarakeri`:

```text
/plugin marketplace add adityaarakeri/skills
/plugin install humanize-content@adityaarakeri
```

Once the marketplace is added, `/plugin` with no arguments lets you browse everything in it.

### Codex, Cursor, OpenCode, Copilot, and other agents

Use the [`skills` CLI](https://github.com/vercel-labs/skills) (Node 22.20+). It detects which
agents you have and asks where to install:

```bash
npx skills add adityaarakeri/senior-agent-skills
npx skills add adityaarakeri/skills --skill judgment-coach
```

Add `-g` to install for your user instead of the current project.

## Catalog

### State machine auditing

[`state-machine-audit`](https://github.com/adityaarakeri/state-machine-audit) audits
state modeling, async races, side-effect boundaries, and persistence hydration.
It writes an evidence-backed `REPORT.md` without editing application code.
The skill, installer, and evaluation suite live in their own repository.

```bash
npx skills add adityaarakeri/state-machine-audit --global
```

<!-- catalog:start -->
### Engineering discipline

| Plugin | What it does | Skills | Source | Claude Code install |
|---|---|---|---|---|
| `senior-agent-skills` | Makes a coding agent plan, test, and verify before shipping. | 10 | [adityaarakeri/senior-agent-skills](https://github.com/adityaarakeri/senior-agent-skills) | `/plugin install senior-agent-skills --marketplace adityaarakeri/skills` |
| `yolo` | Hands an agent one goal and stays out of the way. | 1 | [adityaarakeri/yolo](https://github.com/adityaarakeri/yolo) | `/plugin install yolo --marketplace adityaarakeri/skills` |
| `context-relay-tdd` | Audits a repo, then fixes it one test-first item at a time, across context resets. | 1 | [this repo](https://github.com/adityaarakeri/skills/tree/main/skills/context-relay-tdd) | `/plugin install context-relay-tdd --marketplace adityaarakeri/skills` |

### Writing and design

| Plugin | What it does | Skills | Source | Claude Code install |
|---|---|---|---|---|
| `humanize-content` | Strips AI tells from text without adding new ones. | 1 | [adityaarakeri/humanize-content](https://github.com/adityaarakeri/humanize-content) | `/plugin install humanize-content --marketplace adityaarakeri/skills` |
| `handcraft-html` | Builds HTML pages that do not read as generated. | 1 | [adityaarakeri/handcraft-html](https://github.com/adityaarakeri/handcraft-html) | `/plugin install handcraft-html --marketplace adityaarakeri/skills` |
| `frontend-engineering` | Senior frontend judgment for framework apps. | 1 | [this repo](https://github.com/adityaarakeri/skills/tree/main/skills/claude-code-frontend-design) | `/plugin install frontend-engineering --marketplace adityaarakeri/skills` |

### Judgment

| Plugin | What it does | Skills | Source | Claude Code install |
|---|---|---|---|---|
| `judgment-coach` | Coaches a decision instead of making it for you. | 1 | [this repo](https://github.com/adityaarakeri/skills/tree/main/skills/judgment-coach) | `/plugin install judgment-coach --marketplace adityaarakeri/skills` |
<!-- catalog:end -->

## How this repo works

`catalog.json` is the source of truth. `scripts/build_catalog.py` validates it and generates:

- `.claude-plugin/marketplace.json`, the Claude Code marketplace
- the catalog table in this README
- the skills page on the website, when given `--site`

```bash
python scripts/build_catalog.py            # regenerate
python scripts/build_catalog.py --check    # what CI runs; fails if anything is stale
python scripts/build_catalog.py --site ../portfolio/skills/index.html
python -m unittest discover -s tests -v
```

Only Python 3.10+ is needed. No third-party packages.

### Adding a skill

1. Small skill: put it in `skills/<name>/SKILL.md`. The folder name must match the `name:` in
   its frontmatter. Big skill with its own tooling: keep it in its own repo.
2. Add an entry to `catalog.json`: a tagline (one line, what it does for you), a description,
   the category, which agents it works with, and the path to each `SKILL.md` folder inside the
   repo. `proof` (a short terminal excerpt) and `demo` (a live page) are optional but they are
   what makes the website entry worth reading.
3. Run the build with `--site` pointed at your website checkout, then commit both repos.

Entries hosted elsewhere are validated by their own repos' CI. This repo checks only that the
catalog is well-formed and that local skills match their declared names.

## License

MIT for everything in this repo. Skills hosted in other repos carry their own licenses.
