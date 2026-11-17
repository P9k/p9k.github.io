"""
List sections of Paul's hand-maintained moderncv CV, generated from the vault.

Each function returns LaTeX lines in exactly the markup the existing CV.tex
uses (\\cventry, \\cvitem, \\cvlistitem). CV.tex keeps the section headers and
all hand-written parts and pulls these files in with \\input{generated/...}.
Written by `build.py --cv-out DIR` to DIR/generated/.
"""
import io
import os

from build import (S, I, L, is_public, month_year, tex_escape,
                   highlight_authors_tex)

HEADER = "% generated from the Obsidian vault by build.py -- do not edit\n"


def _public(notes):
    return [n for n in notes if is_public(n)]


def _amount(value):
    n = I(value)
    return "{:,}~EUR".format(n) if n else ""


def _place(*parts, note=None):
    s = ", ".join(S(p) for p in parts if S(p))
    if not s and note is not None:
        if "online" in (S(note.get("venue")) + S(note.get("city"))).lower():
            return "online"
    return s


def _entry(*args):
    return "\\cventry" + "".join("{%s}" % a for a in args)


def _talk_key(n):
    return (-I(n.get("year")), -I(n.get("month")), -I(n.get("day")))


def _talk_name(n):
    return tex_escape(S(n.get("cv_name")) or S(n.get("occasion_name")) or S(n.get("title")))


def _is_poster(n):
    return S(n.get("category")) == "Poster" or S(n.get("format")) == "Poster"


def _talk_rows(talks, categories):
    rows = sorted([n for n in _public(talks) if S(n.get("category")) in categories],
                  key=_talk_key)
    return "".join(
        _entry(I(n.get("year")) or "", _talk_name(n), "",
               tex_escape(_place(n.get("city"), n.get("country"), note=n)), "",
               "Poster" if _is_poster(n) else "Talk") + "\n"
        for n in rows)


def funding_tex(notes):
    rows = sorted(_public(notes), key=lambda n: -I(n.get("year")))
    out = []
    for n in rows:
        title = "``%s''" % tex_escape(n.get("title"))
        role = S(n.get("role"))
        out.append(_entry(I(n.get("year")) or "", tex_escape(n.get("programme")),
                          tex_escape(n.get("funder")), _amount(n.get("amount_eur")),
                          tex_escape(n.get("duration")),
                          "%s: %s" % (tex_escape(role), title) if role else title))
    return "".join(r + "\n" for r in out)


def conference_org_tex(service_notes):
    rows = sorted([n for n in _public(service_notes)
                   if S(n.get("category")) == "Conference organization"],
                  key=lambda n: (-I(n.get("year")), S(n.get("title")).lower()))
    return "".join(
        _entry(I(n.get("year")) or "", tex_escape(S(n.get("cv_name")) or S(n.get("title"))),
               "", tex_escape(_place(n.get("location"), n.get("country"))), "",
               tex_escape(n.get("role"))) + "\n"
        for n in rows)


def invited_talks_tex(talks):
    return _talk_rows(talks, ("Invited Talk",))


def contributed_talks_tex(talks):
    return _talk_rows(talks, ("Contributed Talk", "Poster"))


def seminars_tex(talks):
    labels = {"Invited Seminar": "Seminar", "Workshop Lecture": "Workshop lecturer"}
    rows = sorted([n for n in _public(talks) if S(n.get("category")) in labels],
                  key=_talk_key)
    return "".join(
        _entry(month_year(n.get("year"), n.get("month")), labels[S(n.get("category"))],
               _talk_name(n), tex_escape(_place(n.get("city"), n.get("country"), note=n)),
               "", "") + "\n"
        for n in rows)


def reviewing_tex(service_notes):
    out = []
    for n in _public(service_notes):
        if S(n.get("category")) == "Reviewing":
            out += ["\\cvlistitem{\\textit{%s}}\n" % tex_escape(j) for j in L(n.get("journals"))]
    return "".join(out)


def metrics_tex(profile):
    p = profile or {}
    out = []
    if S(p.get("citations_scholar")) or S(p.get("citations_scopus")):
        out.append(_entry("Total Citations", "%s (Google Scholar) / %s (Scopus)"
                          % (S(p.get("citations_scholar")), S(p.get("citations_scopus"))),
                          "", "", "", ""))
    if S(p.get("hindex_scholar")) or S(p.get("hindex_scopus")):
        out.append(_entry("h-index", "%s (Google Scholar) / %s (Scopus)"
                          % (S(p.get("hindex_scholar")), S(p.get("hindex_scopus"))),
                          "", "", "", ""))
    return "".join(r + "\n" for r in out)


def publications_tex(papers, highlight_pattern):
    """`papers` arrive newest first (as collect() sorts them); numbered N..1."""
    out = []
    total = len(papers)
    for i, n in enumerate(papers):
        bits = ["``%s'': %s" % (tex_escape(n.get("publication")),
                                highlight_authors_tex(n.get("authors"), highlight_pattern))]
        if S(n.get("journal")):
            bits.append("\\textit{%s}" % tex_escape(n.get("journal")))
        if S(n.get("pubyear")):
            bits.append("\\textbf{%s}" % S(n.get("pubyear")))
        if S(n.get("volume")):
            bits.append("\\textit{%s}" % tex_escape(n.get("volume")))
        if S(n.get("pages")):
            bits.append(tex_escape(n.get("pages")))
        out.append("  \\cvitem{\\textit{%d}}{%s.}\n\n" % (total - i, ", ".join(bits)))
    return "".join(out)


def render_all(d, cfg):
    files = {
        "funding.tex": funding_tex(d.funding),
        "conference-organization.tex": conference_org_tex(d.service),
        "invited-talks.tex": invited_talks_tex(d.talks),
        "contributed-talks.tex": contributed_talks_tex(d.talks),
        "seminars.tex": seminars_tex(d.talks),
        "reviewing.tex": reviewing_tex(d.service),
        "metrics.tex": metrics_tex(d.profile),
        "publications.tex": publications_tex(d.publications, cfg.get("highlight_author", "")),
    }
    return {k: HEADER + v for k, v in files.items()}


def write_cv_moderncv(d, cfg, out_dir):
    gen = os.path.join(out_dir, "generated")
    os.makedirs(gen, exist_ok=True)
    files = render_all(d, cfg)
    for name, text in files.items():
        with io.open(os.path.join(gen, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return len(files)
