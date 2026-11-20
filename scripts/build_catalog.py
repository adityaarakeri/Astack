#!/usr/bin/env python3
"""Validate catalog.json and generate everything derived from it.

Outputs:
  .claude-plugin/marketplace.json   the Claude Code marketplace
  README.md (between catalog markers)
  a skills page, when given --site PATH

Usage:
  python scripts/build_catalog.py            regenerate
  python scripts/build_catalog.py --check    fail if anything is stale or invalid
  python scripts/build_catalog.py --site ../portfolio/skills/index.html

Python 3.10+, standard library only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"
BUNDLE_DIR = ROOT / "plugins"

START = "<!-- catalog:start -->"
END = "<!-- catalog:end -->"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KNOWN_AGENTS = {"claude-code", "codex", "cursor", "opencode", "copilot"}


class CatalogError(Exception):
    pass


# ---------------------------------------------------------------- validation


def read_frontmatter_name(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def validate(catalog: dict, root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    mk = catalog.get("marketplace") or {}
    for key in ("name", "repo", "owner", "description"):
        if not mk.get(key):
            errors.append(f"marketplace.{key} is required")
    if mk.get("name") and not NAME_RE.match(mk["name"]):
        errors.append(f"marketplace.name {mk['name']!r} must be kebab-case")

    bundle = catalog.get("bundle") or {}
    for key in ("name", "tagline", "description"):
        if not bundle.get(key):
            errors.append(f"bundle.{key} is required")

    categories = catalog.get("categories") or []
    cat_ids = [c.get("id") for c in categories]
    if not categories:
        errors.append("categories must not be empty")
    if len(cat_ids) != len(set(cat_ids)):
        errors.append("category ids must be unique")

    plugins = catalog.get("plugins") or []
    if not plugins:
        errors.append("plugins must not be empty")
    seen: set[str] = set()
    for i, p in enumerate(plugins):
        where = f"plugins[{i}] ({p.get('name', '?')})"
        name = p.get("name")
        if not name or not NAME_RE.match(name):
            errors.append(f"{where}: name must be kebab-case")
        elif name in seen:
            errors.append(f"{where}: duplicate plugin name")
        elif name == bundle.get("name"):
            errors.append(f"{where}: name collides with the bundle")
        else:
            seen.add(name)
        for key in ("tagline", "description"):
            if not isinstance(p.get(key), str) or not p[key].strip():
                errors.append(f"{where}: {key} is required")
        if isinstance(p.get("tagline"), str) and "\n" in p["tagline"]:
            errors.append(f"{where}: tagline must be one line")
        if p.get("category") not in cat_ids:
            errors.append(f"{where}: unknown category {p.get('category')!r}")
        agents = p.get("agents") or []
        if not agents:
            errors.append(f"{where}: agents must not be empty")
        for a in agents:
            if a not in KNOWN_AGENTS:
                errors.append(f"{where}: unknown agent {a!r}")
        skills = p.get("skills") or []
        if not skills:
            errors.append(f"{where}: skills must list at least one SKILL.md folder")
        for s in skills:
            if not isinstance(s, str) or s.startswith("/") or ".." in Path(s).parts:
                errors.append(f"{where}: skill path {s!r} must be relative, inside the repo")

        repo = p.get("repo")
        if repo is None:
            # Hosted in this repo: check that the files exist and names match.
            if len(skills) != 1:
                errors.append(f"{where}: local plugins hold exactly one skill")
            for s in skills:
                if not isinstance(s, str):
                    continue
                folder = root / s
                skill_md = folder / "SKILL.md"
                if not skill_md.is_file():
                    errors.append(f"{where}: {s}/SKILL.md does not exist")
                    continue
                fm = read_frontmatter_name(skill_md)
                if fm != folder.name:
                    errors.append(
                        f"{where}: {s}/SKILL.md has name {fm!r}, expected {folder.name!r}"
                    )
        elif not isinstance(repo, str) or not re.match(r"^[\w.-]+/[\w.-]+$", repo):
            errors.append(f"{where}: repo must be owner/name or null")

    return errors


# ---------------------------------------------------------------- generation


def rel(path: str) -> str:
    path = path.strip("/")
    return "./" if path in ("", ".") else f"./{path}"


def build_marketplace(catalog: dict) -> dict:
    mk = catalog["marketplace"]
    bundle = catalog["bundle"]
    entries = []
    for p in catalog["plugins"]:
        entry: dict = {"name": p["name"], "description": p["tagline"]}
        if p["repo"] is None:
            # Root the plugin at its own skill folder so it never picks up
            # sibling skills through the default skills/ directory.
            entry["source"] = rel(p["skills"][0])
            entry["skills"] = ["./"]
        else:
            entry["source"] = {"source": "github", "repo": p["repo"]}
            entry["skills"] = [rel(s) for s in p["skills"]]
        entry["strict"] = False
        entry["category"] = p["category"]
        entries.append(entry)

    entries.append(
        {
            "name": bundle["name"],
            "description": bundle["tagline"],
            "source": rel(f"plugins/{bundle['name']}"),
            "strict": False,
            "category": "bundle",
            "dependencies": [p["name"] for p in catalog["plugins"]],
        }
    )
    return {
        "name": mk["name"],
        "owner": mk["owner"],
        "description": mk["description"],
        "plugins": entries,
    }


def install_cmd(catalog: dict, name: str) -> str:
    return f"/plugin install {name} --marketplace {catalog['marketplace']['repo']}"


def source_link(catalog: dict, p: dict) -> str:
    if p["repo"] is None:
        repo = catalog["marketplace"]["repo"]
        return f"[this repo](https://github.com/{repo}/tree/main/{p['skills'][0]})"
    return f"[{p['repo']}](https://github.com/{p['repo']})"


def count_skills(p: dict) -> int:
    return len(p["skills"])


def build_readme_section(catalog: dict) -> str:
    lines = [START]
    for cat in catalog["categories"]:
        members = [p for p in catalog["plugins"] if p["category"] == cat["id"]]
        if not members:
            continue
        lines += [
            f"### {cat['title']}",
            "",
            "| Plugin | What it does | Skills | Source | Claude Code install |",
            "|---|---|---|---|---|",
        ]
        for p in members:
            lines.append(
                f"| `{p['name']}` | {p['tagline']} | {count_skills(p)} | "
                f"{source_link(catalog, p)} | `{install_cmd(catalog, p['name'])}` |"
            )
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def render_readme(catalog: dict, current: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(current):
        raise CatalogError(f"README.md is missing the {START} / {END} markers")
    return pattern.sub(lambda _: build_readme_section(catalog), current, count=1)


def bundle_readme(catalog: dict) -> str:
    b = catalog["bundle"]
    names = "\n".join(f"- `{p['name']}`: {p['tagline']}" for p in catalog["plugins"])
    return (
        f"# {b['name']}\n\n{b['description']}\n\n"
        f"```text\n{install_cmd(catalog, b['name'])}\n```\n\n"
        f"Installs:\n\n{names}\n\n"
        "Generated by `scripts/build_catalog.py`; edit `catalog.json` instead.\n"
    )


def render_site(catalog: dict) -> str:
    e = html.escape
    sections = []
    for cat in catalog["categories"]:
        cards = []
        for p in (x for x in catalog["plugins"] if x["category"] == cat["id"]):
            src = (
                f"https://github.com/{catalog['marketplace']['repo']}/tree/main/{p['skills'][0]}"
                if p["repo"] is None
                else f"https://github.com/{p['repo']}"
            )
            extra = ""
            if p.get("proof"):
                extra += f"<pre class=\"proof\">{e(p['proof'])}</pre>"
            if p.get("demo"):
                extra += f"<p><a href=\"{e(p['demo'])}\">Live demo</a></p>"
            cards.append(
                f"<article><h3>{e(p['name'])}</h3><p class=\"tag\">{e(p['tagline'])}</p>"
                f"<p>{e(p['description'])}</p>{extra}"
                f"<pre><code>{e(install_cmd(catalog, p['name']))}</code></pre>"
                f"<p><a href=\"{e(src)}\">Source</a> · {count_skills(p)} "
                f"skill{'s' if count_skills(p) != 1 else ''}</p></article>"
            )
        if cards:
            sections.append(f"<section><h2>{e(cat['title'])}</h2>{''.join(cards)}</section>")
    everything = install_cmd(catalog, catalog["bundle"]["name"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skills</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#66645e; --line:#e4e1d8; --code:#f1efe8; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#161614; --fg:#ecebe6; --muted:#a19f97; --line:#2f2e2a; --code:#22211e; }}
}}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 system-ui, sans-serif; }}
main {{ max-width:760px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ margin:0 0 4px; }} h2 {{ margin-top:40px; border-bottom:1px solid var(--line); padding-bottom:6px; }}
article {{ padding:16px 0; border-bottom:1px solid var(--line); }}
h3 {{ margin:0; font-family:ui-monospace, monospace; }}
.tag {{ color:var(--muted); margin:2px 0 8px; }}
pre {{ background:var(--code); padding:10px 12px; overflow-x:auto; border-radius:6px; }}
a {{ color:inherit; }}
</style>
</head>
<body><main>
<h1>Skills</h1>
<p>Every agent skill I maintain. Install all of them in Claude Code with:</p>
<pre><code>{e(everything)}</code></pre>
{''.join(sections)}
</main></body>
</html>
"""


# ---------------------------------------------------------------- main


def dump_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def outputs(catalog: dict) -> dict[Path, str]:
    bundle_dir = BUNDLE_DIR / catalog["bundle"]["name"]
    return {
        MARKETPLACE: dump_json(build_marketplace(catalog)),
        README: render_readme(catalog, README.read_text(encoding="utf-8")),
        bundle_dir / "README.md": bundle_readme(catalog),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if outputs are stale")
    ap.add_argument("--site", type=Path, help="also write the skills page here")
    args = ap.parse_args(argv)

    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read catalog.json: {exc}", file=sys.stderr)
        return 1

    errors = validate(catalog)
    if errors:
        for err in errors:
            print(f"error: {err}", file=sys.stderr)
        return 1

    try:
        files = outputs(catalog)
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.check:
        stale = [
            p.relative_to(ROOT)
            for p, text in files.items()
            if not p.exists() or p.read_text(encoding="utf-8") != text
        ]
        if stale:
            for p in stale:
                print(f"stale: {p}", file=sys.stderr)
            print("run: python scripts/build_catalog.py", file=sys.stderr)
            return 1
        print(f"ok: {len(catalog['plugins'])} plugins, outputs up to date")
        return 0

    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    if args.site:
        args.site.parent.mkdir(parents=True, exist_ok=True)
        args.site.write_text(render_site(catalog), encoding="utf-8")
        print(f"wrote {args.site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
