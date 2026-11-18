"""The website's own CV (cv.html, cv.pdf source, cv.md) links to the website."""
import io
import os
import sys
import tempfile
import unittest

import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import build  # noqa: E402

PROFILE = """---
type: cv-profile
name: Test Person
email: test@example.org
orcid: https://orcid.org/0000-0000-0000-0000
---
"""


class CvWebsiteLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as fh:
            cls.cfg = yaml.safe_load(fh)
        cls.tmp = tempfile.TemporaryDirectory()
        prof = os.path.join(cls.tmp.name, cls.cfg["sources"]["profile"])
        os.makedirs(os.path.dirname(prof))
        with io.open(prof, "w", encoding="utf-8") as fh:
            fh.write(PROFILE)
        cls.cfg["vault"] = cls.tmp.name
        cls.cfg["site"]["url"] = "https://example.org/"
        cls.d = build.collect(cls.cfg)
        cls.cfg["_profile"] = cls.d.profile

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_html_cv_links_website(self):
        self.assertIn('href="https://example.org"', build.build_cv(self.cfg, self.d))

    def test_latex_cv_links_website(self):
        tex = build.build_latex_cv(self.cfg, self.d)
        self.assertIn(r"\href{https://example.org}{example.org}", tex)

    def test_markdown_cv_links_website(self):
        self.assertIn("[example.org](https://example.org)",
                      build.build_markdown_cv(self.cfg, self.d))


if __name__ == "__main__":
    unittest.main()
