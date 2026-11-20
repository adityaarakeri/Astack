import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_catalog as bc  # noqa: E402


def load_catalog() -> dict:
    return json.loads(bc.CATALOG.read_text(encoding="utf-8"))


class RepoState(unittest.TestCase):
    def test_catalog_is_valid(self):
        self.assertEqual(bc.validate(load_catalog()), [])

    def test_generated_files_are_up_to_date(self):
        self.assertEqual(bc.main(["--check"]), 0)


class Marketplace(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()
        self.market = bc.build_marketplace(self.catalog)
        self.by_name = {p["name"]: p for p in self.market["plugins"]}

    def test_bundle_depends_on_every_plugin(self):
        bundle = self.by_name[self.catalog["bundle"]["name"]]
        expected = [p["name"] for p in self.catalog["plugins"]]
        self.assertEqual(bundle["dependencies"], expected)

    def test_every_catalog_plugin_is_listed(self):
        for p in self.catalog["plugins"]:
            self.assertIn(p["name"], self.by_name)

    def test_local_plugins_are_rooted_at_their_skill_folder(self):
        # Rooting at the repo would pull in every sibling under skills/.
        for p in self.catalog["plugins"]:
            if p["repo"] is None:
                entry = self.by_name[p["name"]]
                self.assertEqual(entry["source"], "./" + p["skills"][0])
                self.assertEqual(entry["skills"], ["./"])

    def test_remote_plugins_use_github_sources(self):
        for p in self.catalog["plugins"]:
            if p["repo"] is not None:
                entry = self.by_name[p["name"]]
                self.assertEqual(entry["source"], {"source": "github", "repo": p["repo"]})


class Validation(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def errors_for(self, mutate, root=bc.ROOT):
        cat = copy.deepcopy(self.catalog)
        mutate(cat)
        return bc.validate(cat, root)

    def test_duplicate_names_rejected(self):
        errs = self.errors_for(lambda c: c["plugins"].append(copy.deepcopy(c["plugins"][0])))
        self.assertTrue(any("duplicate" in e for e in errs))

    def test_bundle_name_collision_rejected(self):
        def mutate(c):
            c["plugins"][0]["name"] = c["bundle"]["name"]
        self.assertTrue(any("collides" in e for e in self.errors_for(mutate)))

    def test_unknown_category_rejected(self):
        def mutate(c):
            c["plugins"][0]["category"] = "nope"
        self.assertTrue(any("unknown category" in e for e in self.errors_for(mutate)))

    def test_missing_local_skill_rejected(self):
        def mutate(c):
            c["plugins"].append(
                {**c["plugins"][-1], "name": "ghost", "skills": ["skills/ghost"]}
            )
        self.assertTrue(any("does not exist" in e for e in self.errors_for(mutate)))

    def test_frontmatter_name_must_match_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "skills" / "real-name"
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text("---\nname: other-name\ndescription: x\n---\n")

            def mutate(c):
                c["plugins"] = [
                    {**c["plugins"][-1], "name": "real-name", "skills": ["skills/real-name"]}
                ]
            errs = self.errors_for(mutate, Path(tmp))
            self.assertTrue(any("expected 'real-name'" in e for e in errs))

    def test_path_escape_rejected(self):
        def mutate(c):
            c["plugins"][0]["skills"] = ["../outside"]
        self.assertTrue(any("inside the repo" in e for e in self.errors_for(mutate)))


class ReadmeSection(unittest.TestCase):
    def test_missing_markers_raise(self):
        with self.assertRaises(bc.CatalogError):
            bc.render_readme(load_catalog(), "# no markers here\n")

    def test_install_commands_use_marketplace_repo(self):
        cat = load_catalog()
        section = bc.build_readme_section(cat)
        for p in cat["plugins"]:
            self.assertIn(f"--marketplace {cat['marketplace']['repo']}", section)
            self.assertIn(f"`{p['name']}`", section)


class Site(unittest.TestCase):
    def test_site_lists_everything_and_escapes(self):
        cat = load_catalog()
        cat["plugins"][0]["tagline"] = "<script>"
        page = bc.render_site(cat)
        self.assertNotIn("<script>", page)
        self.assertIn("/plugin install astack", page)
        for p in cat["plugins"]:
            self.assertIn(p["name"], page)


if __name__ == "__main__":
    unittest.main()
