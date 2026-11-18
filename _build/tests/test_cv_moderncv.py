"""Tests for the moderncv list generator (cv_moderncv.py)."""
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv_moderncv as cv  # noqa: E402


def talk(**kw):
    n = {"type": "talk", "year": 2025, "month": 2, "day": 10, "format": "Talk",
         "city": "", "country": "", "venue": ""}
    n.update(kw)
    return n


class FundingTests(unittest.TestCase):
    def test_funding_row(self):
        out = cv.funding_tex([{"year": 2024, "programme": "Federal Funding",
                               "funder": "BMBF (Germany)", "amount_eur": 1500000,
                               "duration": "3 years", "role": "Principal Investigator",
                               "title": "Sustainable TiFe"}])
        self.assertIn(r"\cventry{2024}{Federal Funding}{BMBF (Germany)}{1,500,000~EUR}"
                      r"{3 years}{Principal Investigator: ``Sustainable TiFe''}", out)

    def test_funding_without_amount(self):
        out = cv.funding_tex([{"year": 2016, "programme": "HPC", "funder": "NeSI",
                               "duration": "3 years", "title": "X"}])
        self.assertIn("{NeSI}{}{3 years}{``X''}", out)
        self.assertNotIn("0~EUR", out)


class TalkTests(unittest.TestCase):
    def test_invited_talk_uses_cv_name(self):
        out = cv.invited_talks_tex([talk(category="Invited Talk", cv_name="AMN11",
                                         occasion_name="11th International Conference",
                                         city="Christchurch", country="New Zealand")])
        self.assertIn(r"\cventry{2025}{AMN11}{}{Christchurch, New Zealand}{}{Talk}", out)

    def test_poster_in_contributed(self):
        t = talk(category="Poster", format="Poster", occasion_name="MH 2024",
                 city="Saint-Malo", country="France")
        self.assertIn("{}{Poster}", cv.contributed_talks_tex([t]))
        self.assertEqual("", cv.invited_talks_tex([t]))

    def test_seminar_month(self):
        out = cv.seminars_tex([talk(category="Invited Seminar",
                                    occasion_name="University of Waikato",
                                    city="Hamilton", country="New Zealand")])
        self.assertIn(r"\cventry{Feb 2025}{Seminar}{University of Waikato}"
                      r"{Hamilton, New Zealand}{}{}", out)

    def test_workshop_label(self):
        out = cv.seminars_tex([talk(category="Workshop Lecture", occasion_name="MCBR",
                                    city="Hyderabad", country="India")])
        self.assertIn("{Workshop lecturer}{MCBR}", out)

    def test_online_place(self):
        out = cv.contributed_talks_tex([talk(category="Contributed Talk",
                                             occasion_name="IEA Task 51", venue="online")])
        self.assertIn("{}{online}{}{Talk}", out)

    def test_ampersand_escaped(self):
        out = cv.invited_talks_tex([talk(category="Invited Talk", occasion_name="A & B",
                                         city="Berlin", country="Germany")])
        self.assertIn(r"A \& B", out)

    def test_private_excluded(self):
        out = cv.invited_talks_tex([talk(category="Invited Talk", occasion_name="Secret",
                                         public=False)])
        self.assertNotIn("Secret", out)

    def test_context_in_description(self):
        out = cv.invited_talks_tex([talk(category="Invited Talk", occasion_name="Delegation",
                                         city="Perth", country="Australia",
                                         context="Led by Stefan Rouenhoff & team")])
        self.assertIn(r"{}{Talk -- Led by Stefan Rouenhoff \& team}", out)

    def test_talk_row_shows_context_on_website(self):
        import build
        row = build.talk_row(talk(category="Invited Talk", occasion_name="Delegation",
                                  context="Led by <b>X</b>"))
        self.assertIn('<p class="ts">Led by &lt;b&gt;X&lt;/b&gt;</p>', row)

    def test_talk_row_without_context_unchanged(self):
        import build
        self.assertNotIn('class="ts"', build.talk_row(talk(occasion_name="Delegation")))

    def test_sorted_newest_first(self):
        out = cv.invited_talks_tex([
            talk(category="Invited Talk", occasion_name="Old", year=2016),
            talk(category="Invited Talk", occasion_name="New", year=2025)])
        self.assertLess(out.index("New"), out.index("Old"))


class ServiceTests(unittest.TestCase):
    def test_conference_org_chair(self):
        out = cv.conference_org_tex([{"title": "DPG Spring Meeting 2026",
                                      "category": "Conference organization",
                                      "location": "Dresden", "country": "Germany",
                                      "year": 2026, "role": "Session chair"}])
        self.assertIn(r"\cventry{2026}{DPG Spring Meeting 2026}{}{Dresden, Germany}{}"
                      r"{Session chair}", out)

    def test_conference_org_ignores_other_categories(self):
        out = cv.conference_org_tex([{"title": "Reviewing", "category": "Reviewing"}])
        self.assertEqual("", out)

    def test_reviewing(self):
        out = cv.reviewing_tex([{"category": "Reviewing",
                                 "journals": ["Inorganic Chemistry", "Molecular Physics"]}])
        self.assertIn(r"\cvlistitem{\textit{Inorganic Chemistry}}", out)
        self.assertIn(r"\cvlistitem{\textit{Molecular Physics}}", out)

    def test_metrics(self):
        out = cv.metrics_tex({"citations_scholar": 2553, "citations_scopus": 1933,
                              "hindex_scholar": 27, "hindex_scopus": 24})
        self.assertIn(r"\cventry{Total Citations}{2553 (Google Scholar) / 1933 (Scopus)}"
                      r"{}{}{}{}", out)
        self.assertIn(r"\cventry{h-index}{27 (Google Scholar) / 24 (Scopus)}{}{}{}{}", out)


class PublicationTests(unittest.TestCase):
    def test_publication_numbering_and_missing_volume(self):
        papers = [{"publication": "New paper", "authors": "A. B, P. Jerabek",
                   "journal": "Calphad", "pubyear": 2026, "volume": "", "pages": "12"},
                  {"publication": "Old paper", "authors": "P. Jerabek",
                   "journal": "Science", "pubyear": 2012, "volume": "337", "pages": "1526"}]
        out = cv.publications_tex(papers, r"P\. ?Jerabek")
        lines = [l for l in out.splitlines() if l.strip().startswith(r"\cvitem")]
        self.assertTrue(lines[0].strip().startswith(r"\cvitem{\textit{2}}"))
        self.assertTrue(lines[1].strip().startswith(r"\cvitem{\textit{1}}"))
        self.assertNotIn(r"\textit{}", lines[0])
        self.assertIn(r"\textbf{P. Jerabek}", lines[0])
        self.assertIn(r"\textit{Science}, \textbf{2012}, \textit{337}, 1526.", lines[1])


    def test_empty_highlight_pattern_leaves_authors_intact(self):
        out = cv.publications_tex([{"publication": "T", "authors": "A & B",
                                    "journal": "J", "pubyear": 2020}], "")
        self.assertIn(r"``T'': A \& B, \textit{J}", out)
        self.assertNotIn(r"\textbf{}", out)


class WriteTests(unittest.TestCase):
    def test_write_creates_files(self):
        d = types.SimpleNamespace(funding=[], service=[], talks=[], publications=[],
                                  profile={})
        cfg = {"highlight_author": "Jerabek"}
        with tempfile.TemporaryDirectory() as tmp:
            n = cv.write_cv_moderncv(d, cfg, tmp)
            files = sorted(os.listdir(os.path.join(tmp, "generated")))
            self.assertEqual(8, n)
            self.assertEqual(8, len(files))
            for f in files:
                with open(os.path.join(tmp, "generated", f), encoding="utf-8") as fh:
                    self.assertTrue(fh.read().startswith("% generated from the Obsidian vault"))


if __name__ == "__main__":
    unittest.main()
