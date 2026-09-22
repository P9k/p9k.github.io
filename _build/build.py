#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static website generator for an academic homepage.

Reads the YAML front matter of notes in an Obsidian vault and writes a plain
static website (HTML + CSS + a little JavaScript) plus a printable CV and a
LaTeX version of it.

Usage:      python3 _build/build.py [--config _build/config.yaml] [--verbose]
Requires:   Python 3.8+ and PyYAML.   No other dependencies.
"""

import argparse
import datetime as dt
import html
import io
import json
import os
import re
import shutil
import sys
import unicodedata

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is missing.  Install it with:  pip install --user pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date.today()

# ===========================================================================
#  Front matter reading
# ===========================================================================

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


def parse_frontmatter(text):
    """Return (dict, body).  Falls back to a tolerant line parser."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    try:
        data = yaml.safe_load(raw)
        if isinstance(data, dict):
            return data, body
    except yaml.YAMLError:
        pass
    data, key = {}, None
    for line in raw.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0].isspace():
            if line.lstrip().startswith("- ") and key:
                data.setdefault(key, [])
                if isinstance(data[key], list):
                    data[key].append(line.lstrip()[2:].strip())
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            data[key] = val if val else None
    return data, body


def read_note(path):
    with io.open(path, encoding="utf-8") as fh:
        fm, body = parse_frontmatter(fh.read())
    fm = fm or {}
    fm["_path"] = path
    fm["_slug"] = os.path.splitext(os.path.basename(path))[0]
    fm["_body"] = body
    return fm


def scan(folder, wanted_type=None, recursive=True):
    """Collect notes of a given `type:` from a folder."""
    out = []
    if not os.path.isdir(folder):
        return out
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_"))]
        for fn in sorted(files):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            note = read_note(os.path.join(root, fn))
            if wanted_type and str(note.get("type", "")).strip() != wanted_type:
                continue
            out.append(note)
        if not recursive:
            break
    return out


# ===========================================================================
#  Small helpers
# ===========================================================================

def S(v):
    """Front matter value -> clean string."""
    if v is None or v is False:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(S(x) for x in v if x is not None and S(x))
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v).strip()


def L(v):
    """Front matter value -> list of strings."""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [S(x) for x in v if S(x)]
    return [p.strip() for p in str(v).split(",") if p.strip()]


def is_public(note, default=True):
    v = note.get("public", None)
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return S(v).lower() not in ("false", "no", "0")


def I(v, default=0):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def E(s):
    return html.escape(S(s), quote=True)


MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
MON3 = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def month_year(y, m, short=True):
    y, m = I(y), I(m)
    names = MON3 if short else MONTHS
    if y and 1 <= m <= 12:
        return "%s %d" % (names[m], y)
    return str(y) if y else ""


def fmt_date(value, short=True):
    s = S(value)
    m = re.match(r"(\d{4})-(\d{2})", s)
    if m:
        return month_year(m.group(1), m.group(2), short)
    m = re.match(r"(\d{4})", s)
    return m.group(1) if m else ""


def year_of(value):
    m = re.match(r"(\d{4})", S(value))
    return I(m.group(1)) if m else 0


def span(start, end, open_label="present"):
    a, b = fmt_date(start), fmt_date(end)
    if a and b:
        return "%s &ndash; %s" % (a, b)
    if a:
        return "%s &ndash; %s" % (a, open_label)
    return b or ""


def money(value):
    n = I(value)
    if not n:
        return ""
    if n >= 1000000:
        v = n / 1000000.0
        return ("%.1f M€" % v).replace(".0 M", " M")
    if n >= 1000:
        return "%d k€" % round(n / 1000.0)
    return "%d €" % n


def md_inline(text):
    """A very small subset of Markdown: *em*, **strong**, `code`, [t](u)."""
    t = E(text)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|mailto:[^)\s]+|[.#/][^)\s]*)\)",
               r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def md_block(text):
    """Paragraphs, bullet lists and inline markup.  Callouts are dropped."""
    lines = [l for l in S(text).split("\n")]
    lines = [l for l in lines if not l.lstrip().startswith(">")]
    out, para, bullets = [], [], []

    def flush():
        if bullets:
            out.append("<ul>" + "".join("<li>%s</li>" % md_inline(b) for b in bullets) + "</ul>")
            del bullets[:]
        if para:
            out.append("<p>%s</p>" % md_inline(" ".join(para)))
            del para[:]

    for line in lines:
        st = line.strip()
        if not st:
            flush()
        elif st.startswith(("- ", "* ")):
            if para:
                flush()
            bullets.append(st[2:])
        elif st.startswith("#"):
            flush()
        else:
            if bullets:
                flush()
            para.append(st)
    flush()
    return "\n".join(out)


def body_sections(body):
    """Split a note body into {heading-slug: text} using '## heading' markers."""
    parts, cur, buf = {}, None, []
    for line in S(body).split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if cur:
                parts[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1).strip().lower().replace(" ", "_"), []
        elif cur is not None:
            buf.append(line)
    if cur:
        parts[cur] = "\n".join(buf).strip()
    return parts


def topics_of(note, cfg):
    """Topics of a note, minus the internal tags listed in the configuration."""
    block = {t.lower() for t in cfg.get("topic_blocklist", [])}
    return [t for t in L(note.get("topics")) if t.lower() not in block]


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", S(s).lower()).strip("-")
    return s or "item"


def resolve_vault_image(vault, note, attachment_dirs):
    """Find the picture a project note points at.

    Looks at `image:` first, then falls back to `banner:` (the field the
    Obsidian Banners plugin already uses on most project notes, so existing
    projects get a picture on the website for free). Accepts a plain vault
    path, an Obsidian ![[wikilink]] embed, or a bare filename resolved
    against the vault's attachment folders. An http(s) URL is used as-is.
    Returns {"kind": "url"|"file", "src": ...} or None.
    """
    v = S(note.get("image")) or S(note.get("banner"))
    if not v:
        return None
    if v.startswith("http://") or v.startswith("https://"):
        return {"kind": "url", "src": v}
    m = re.match(r"^!?\[\[([^\]|]+)(?:\|[^\]]*)?\]\]$", v)
    if m:
        v = m.group(1)
    v = v.strip()
    candidates = [v]
    if "/" not in v:
        candidates += [os.path.join(d, v) for d in attachment_dirs]
    for c in candidates:
        p = os.path.join(vault, c)
        if os.path.isfile(p):
            return {"kind": "file", "src": p}
    return None


def copy_project_images(cfg, d, out_dir):
    """Copy each project's picture into assets/img/projects/ and record its
    published URL on the note as `_image_url` (empty string if it has none)."""
    vault = os.path.expanduser(cfg["vault"])
    attach_dirs = cfg.get("image_search_dirs", [])
    img_dir = os.path.join(out_dir, "assets", "img", "projects")
    n_copied = 0
    for p in d.projects:
        info = resolve_vault_image(vault, p, attach_dirs)
        if not info:
            p["_image_url"] = ""
            continue
        if info["kind"] == "url":
            p["_image_url"] = info["src"]
            continue
        ext = os.path.splitext(info["src"])[1].lower() or ".jpg"
        dest_name = slugify(S(p.get("acronym")) or p["_slug"]) + ext
        os.makedirs(img_dir, exist_ok=True)
        shutil.copy2(info["src"], os.path.join(img_dir, dest_name))
        p["_image_url"] = "assets/img/projects/" + dest_name
        n_copied += 1
    return n_copied


# ===========================================================================
#  Collectors
# ===========================================================================

class Data(object):
    pass


def collect(cfg):
    vault = os.path.expanduser(cfg["vault"])
    src = cfg["sources"]
    opt = cfg["options"]
    d = Data()

    def p(key):
        return os.path.join(vault, src[key])

    # --- profile -----------------------------------------------------------
    prof_path = os.path.join(vault, src["profile"])
    d.profile = read_note(prof_path) if os.path.isfile(prof_path) else {}
    d.prose = body_sections(d.profile.get("_body", ""))

    # --- publications ------------------------------------------------------
    ok = set(opt["published_status"])
    pubs = []
    for n in scan(p("papers"), "paper"):
        status = S(n.get("status"))
        if status not in ok:
            continue
        if not is_public(n):
            continue
        pubs.append(n)
    pubs.sort(key=lambda n: (-I(n.get("pubyear")), -I(n.get("runningnumber")),
                             S(n.get("publication")).lower()))
    d.publications = pubs

    # --- talks -------------------------------------------------------------
    talks = [n for n in scan(p("talks"), "talk") if is_public(n)]
    talks.sort(key=lambda n: (-I(n.get("year")), -I(n.get("month")), -I(n.get("day"))))
    d.talks = talks

    # --- projects ----------------------------------------------------------
    projs = [n for n in scan(p("projects"), "project") if is_public(n)]

    def pstart(n):
        return S(n.get("startingdate")) or S(n.get("startdate"))

    def pend(n):
        return S(n.get("enddate"))
    for n in projs:
        n["_start"], n["_end"] = pstart(n), pend(n)
        act = n.get("active")
        n["_active"] = (act is True) or (S(act).lower() in ("true", "yes", "1"))
    projs.sort(key=lambda n: (not n["_active"], -year_of(n["_end"]), -year_of(n["_start"])))
    d.projects = projs

    # --- funding, teaching, career ----------------------------------------
    fund = [n for n in scan(p("funding"), "funding") if is_public(n)]
    fund.sort(key=lambda n: -(I(n.get("year")) or year_of(n.get("startdate"))))
    d.funding = fund

    teach = [n for n in scan(p("teaching"), "teaching") if is_public(n)]
    teach.sort(key=lambda n: -(I(n.get("year_start")) or year_of(n.get("created"))))
    d.teaching = teach

    pos = [n for n in scan(p("positions"), "position") if is_public(n)]
    pos.sort(key=lambda n: -(I(n.get("sort_key")) or year_of(n.get("startdate")) * 100))
    d.positions = pos

    edu = [n for n in scan(p("education"), "education") if is_public(n)]
    edu.sort(key=lambda n: -(I(n.get("sort_key")) or year_of(n.get("enddate")) * 100))
    d.education = edu

    serv = [n for n in scan(p("service"), "service") if is_public(n)]
    d.service = serv

    thr = [n for n in scan(p("research"), "research-thread") if is_public(n)]
    thr.sort(key=lambda n: I(n.get("order"), 99))
    d.threads = thr

    # --- news: explicit notes first, then derived from papers and talks ----
    news = [n for n in scan(p("news"), "news") if is_public(n)]
    items = [{"date": S(n.get("date")) or S(n.get("created"))[:10],
              "when": fmt_date(S(n.get("date")) or S(n.get("created"))[:10]),
              "title": S(n.get("title")),
              "text": md_block(n.get("_body", "")) or "",
              "url": S(n.get("url"))} for n in news]
    for n in d.publications[:6]:
        y = I(n.get("pubyear"))
        if not y:
            continue
        items.append({
            "date": "%04d-01-01" % y,   # sorts below dated news notes of the same year
            "when": str(y),
            "title": "",
            "text": "<p>New paper in <em>%s</em>: %s</p>" % (
                E(n.get("journal")) or "press", E(S(n.get("publication")))),
            "url": doi_url(n)})
    items = [i for i in items if i["text"] or i["title"]]
    items.sort(key=lambda i: i["date"], reverse=True)
    d.news = items

    return d


def doi_url(note):
    doi = S(note.get("doi"))
    if not doi:
        return ""
    if doi.startswith("http"):
        return doi
    return "https://doi.org/" + doi.lstrip("/")


# ===========================================================================
#  Rendering helpers
# ===========================================================================

def highlight_authors(authors, pattern):
    text = E(authors)
    if not text:
        return ""
    try:
        return re.sub("(%s)" % pattern, r"<strong>\1</strong>", text)
    except re.error:
        return text


def publication_html(n, cfg, with_bibtex=True, gutter="year"):
    title = E(S(n.get("publication")) or n.get("_slug"))
    authors = highlight_authors(n.get("authors"), cfg["highlight_author"])
    journal, vol, pages = S(n.get("journal")), S(n.get("volume")), S(n.get("pages"))
    if vol in ("0", "0.0"):
        vol = ""
    year = S(n.get("pubyear"))
    url = doi_url(n)

    ref = []
    if journal:
        ref.append("<i>%s</i>" % E(journal))
    if vol:
        ref.append("<b>%s</b>" % E(vol))
    if pages:
        ref.append(E(pages))
    ref = ", ".join(ref)
    if year and ref:
        ref += " (%s)" % E(year)

    badges = ""
    if S(n.get("openaccess")).lower() in ("true", "yes", "1"):
        badges += '<span class="badge">open access</span>'

    links = []
    if url:
        links.append('<a href="%s" rel="noopener">doi:%s</a>' % (E(url), E(S(n.get("doi")))))
    pub = S(n.get("publisher"))
    if pub.startswith("http") and not url:
        links.append('<a href="%s" rel="noopener">publisher</a>' % E(pub))
    if with_bibtex:
        links.append('<button class="bibtn" type="button" data-key="%s">BibTeX</button>' % E(bib_key(n)))

    if gutter == "number" and I(n.get("runningnumber")):
        label = "#%d" % I(n.get("runningnumber"))
    else:
        label = year
    num = '<div class="yr">%s</div>' % E(label)
    body = ['<p class="t">%s%s</p>' % (title, badges)]
    if authors:
        body.append('<p class="a">%s</p>' % authors)
    if ref or links:
        body.append('<p class="j">%s%s</p>' % (
            ref, (" &middot; " + " &middot; ".join(links)) if links else ""))
    body.append('<pre class="bib" id="bib-%s" hidden>%s</pre>' % (E(bib_key(n)), E(bibtex_entry(n))))

    data = ' data-year="%s" data-topics="%s" data-cat="%s" data-search="%s"' % (
        E(year), E(S(n.get("topics")).lower()), E(S(n.get("category")).lower()),
        E((S(n.get("publication")) + " " + S(n.get("authors")) + " " +
           S(n.get("journal")) + " " + S(n.get("topics"))).lower()))
    return '<div class="pub"%s>%s<div>%s</div></div>' % (data, num, "".join(body))


def bib_key(n):
    first = S(n.get("firstauthor")) or "anon"
    first = re.sub(r"[^A-Za-z]", "", first) or "anon"
    return "%s%s%s" % (first.capitalize(), S(n.get("pubyear")), S(n.get("runningletter")))


def bibtex_entry(n):
    fields = [
        ("author", " and ".join(a.strip() for a in S(n.get("authors")).split(",") if a.strip())),
        ("title", "{%s}" % S(n.get("publication"))),
        ("journal", S(n.get("journal"))),
        ("year", S(n.get("pubyear"))),
        ("volume", S(n.get("volume"))),
        ("pages", S(n.get("pages"))),
        ("doi", S(n.get("doi"))),
    ]
    lines = ["@article{%s," % bib_key(n)]
    for k, v in fields:
        if v:
            lines.append("  %-8s = {%s}," % (k, v))
    lines.append("}")
    return "\n".join(lines)


# ===========================================================================
#  Page templates
# ===========================================================================

def page(cfg, current, title, content, extra_head="", extra_js="", body_class=""):
    nav = []
    for label, href in cfg["nav"]:
        cls = ' class="cur"' if href == current else ""
        nav.append('<a%s href="%s">%s</a>' % (cls, E(href), E(label)))
    name = S(cfg["_profile"].get("name")) or cfg["site"]["title"]
    prefix = S(cfg["_profile"].get("degree_prefix"))
    brand = E(name) + ('<span> &middot; %s</span>' % E(prefix) if prefix else "")

    tpl_path = os.path.join(HERE, "templates", "base.html")
    with io.open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()

    return (tpl
            .replace("{{lang}}", E(cfg["site"]["lang"]))
            .replace("{{title}}", E(title))
            .replace("{{description}}", E(cfg["site"]["description"]))
            .replace("{{body_class}}", E(body_class))
            .replace("{{bg}}", E(S(cfg["options"].get("background_animation")) or "none"))
            .replace("{{brand}}", brand)
            .replace("{{brand_href}}", "index.html")
            .replace("{{nav}}", "\n      ".join(nav))
            .replace("{{content}}", content)
            .replace("{{footer_name}}", E(name))
            .replace("{{footer_location}}", E(cfg["site"]["footer_location"]))
            .replace("{{year}}", str(TODAY.year))
            .replace("{{built}}", TODAY.strftime("%d %B %Y"))
            .replace("{{extra_head}}", extra_head)
            .replace("{{extra_js}}", extra_js))


def section(title, lead="", inner="", anchor=""):
    a = ' id="%s"' % E(anchor) if anchor else ""
    out = ['<section%s><div class="wrap">' % a]
    out.append('<h2 class="sec">%s</h2>' % E(title))
    if lead:
        out.append('<p class="seclead">%s</p>' % md_inline(lead))
    out.append(inner)
    out.append("</div></section>")
    return "\n".join(out)


# --------------------------------------------------------------- front page
def obf_mail(addr):
    """HTML-entity-encode every character of an email address.

    Browsers and screen readers decode this back to a normal, clickable
    address, but the raw HTML source that scrapers scan never contains a
    plain-text address - it defeats simple regex-based spam harvesters
    without needing JavaScript and without hiding the address from real
    visitors."""
    return "".join("&#%d;" % ord(c) for c in addr)


def social_links(prof, include_cv=False):
    """(href, text) pairs for every populated contact / profile link.

    Shared by the about page, the CV header and the contact page so the set
    of links only has to be maintained in one place."""
    raw = [("email", S(prof.get("email"))),
           ("Google Scholar", S(prof.get("scholar"))),
           ("ORCID", S(prof.get("orcid"))),
           ("ResearchGate", S(prof.get("researchgate"))),
           ("GitHub", S(prof.get("github"))),
           ("LinkedIn", S(prof.get("linkedin"))),
           ("Hereon profile", S(prof.get("hereon_profile")))]
    out = []
    for label, value in raw:
        if not value:
            continue
        if label == "email":
            out.append(("mailto:" + obf_mail(value), "Email"))
        else:
            out.append((E(value), E(label)))
    if include_cv:
        out.append(("cv.html", "Curriculum Vitae"))
    return out


def build_index(cfg, d):
    prof, prose = d.profile, d.prose
    opt = cfg["options"]
    out = []

    social = ['<a href="%s" rel="noopener">%s</a>' % (href, text)
              for href, text in social_links(prof, include_cv=True)]

    role_bits = [S(prof.get("position")), S(prof.get("position_second"))]
    role = " &middot; ".join(E(b) for b in role_bits if b)
    affil = " &middot; ".join(E(b) for b in [S(prof.get("department")),
                                             S(prof.get("organisation")),
                                             S(prof.get("city"))] if b)

    out.append("""<section class="hero"><div class="wrap">
  <img class="portrait" src="assets/img/profile.jpg" alt="%s" width="560" height="560">
  <h1 class="name">%s</h1>
  <p class="role"><strong>%s</strong><br>%s</p>
  <div class="bio">%s</div>
  <div class="social">%s</div>
</div></section>""" % (E(S(prof.get("name"))), E(S(prof.get("name"))), role, affil,
                       md_block(prose.get("bio", "")), "\n    ".join(social)))

    if d.threads:
        cards = []
        for t in d.threads:
            link = S(t.get("link"))
            inner = ('<div class="ic">%s</div><h3>%s</h3><p>%s</p>' %
                     (E(S(t.get("icon"))), E(S(t.get("title"))),
                      md_inline(re.sub(r"\s+", " ", S(t.get("_body")).strip()))))
            if link:
                cards.append('<a class="thread" href="%s">%s</a>' % (E(link), inner))
            else:
                cards.append('<div class="thread">%s</div>' % inner)
        out.append(section("Research", prose.get("research_intro", ""),
                           '<div class="threads">%s</div>' % "".join(cards)))

    if d.news:
        rows = []
        for item in d.news[:opt["front_news"]]:
            inner = re.sub(r"</?p>", "", item["text"]) or E(item["title"])
            if item["title"] and item["text"]:
                inner = "<strong>%s</strong> %s" % (E(item["title"]), inner)
            if item["url"]:
                inner += ' <a href="%s" rel="noopener" aria-label="Read more">&rarr;</a>' % E(item["url"])
            rows.append("<li><time>%s</time><div><p>%s</p></div></li>"
                        % (E(item["when"]), inner))
        out.append(section("News", "", '<ul class="news">%s</ul>' % "".join(rows)))

    if d.publications:
        inner = "".join(publication_html(n, cfg) for n in d.publications[:opt["front_publications"]])
        inner += '<a class="more" href="publications.html">All %d publications &rarr;</a>' % len(d.publications)
        out.append(section("Selected publications", "", inner))

    active = [p for p in d.projects if p["_active"]][:opt["front_projects"]]
    if active:
        rows = []
        for p in active:
            rows.append(
                '<div class="proj"><div><p class="pt">%s</p><p class="pd">%s</p></div>'
                '<div class="pr">%s%s</div></div>' % (
                    E(S(p.get("acronym")) or p["_slug"]),
                    md_inline(S(p.get("short"))),
                    span(p["_start"], p["_end"]),
                    ("<br>" + money(p.get("amount_eur"))) if money(p.get("amount_eur")) else ""))
        rows.append('<a class="more" href="projects.html">All projects &rarr;</a>')
        out.append(section("Current projects", "", "".join(rows)))

    return page(cfg, "index.html", cfg["site"]["title"], "\n".join(out))


# ------------------------------------------------------------- publications
def build_publications(cfg, d):
    pubs = d.publications
    years = sorted({I(n.get("pubyear")) for n in pubs if I(n.get("pubyear"))}, reverse=True)
    topics = sorted({t.strip() for n in pubs for t in topics_of(n, cfg)}, key=str.lower)

    controls = ['<div class="filters">',
                '<input type="search" id="q" placeholder="Search title, author, journal…" '
                'aria-label="Search publications">',
                '<select id="fy" aria-label="Filter by year"><option value="">All years</option>']
    controls += ['<option>%d</option>' % y for y in years]
    controls.append('</select><select id="ft" aria-label="Filter by topic">'
                    '<option value="">All topics</option>')
    controls += ['<option>%s</option>' % E(t) for t in topics]
    controls.append('</select>')
    controls.append('<span class="count" id="cnt"></span>')
    controls.append('<a class="dl" href="publications.bib">Download .bib</a>')
    controls.append("</div>")

    groups = []
    for y in years:
        rows = "".join(publication_html(n, cfg, gutter="number")
                       for n in pubs if I(n.get("pubyear")) == y)
        groups.append('<div class="pubyear" data-y="%d"><h3 class="ygroup">%d</h3>%s</div>' % (y, y, rows))
    rest = [n for n in pubs if not I(n.get("pubyear"))]
    if rest:
        groups.append('<div class="pubyear" data-y="0"><h3 class="ygroup">Other</h3>%s</div>'
                      % "".join(publication_html(n, cfg, gutter="number") for n in rest))

    lead = "%d peer-reviewed journal articles." % len(pubs)
    prof = d.profile
    if S(prof.get("citations_scholar")):
        lead += (" %s citations, h-index %s (Google Scholar, %s)." %
                 (S(prof.get("citations_scholar")), S(prof.get("hindex_scholar")),
                  fmt_date(prof.get("metrics_asof"))))

    content = section("Publications", lead, "".join(controls) + "".join(groups))
    return page(cfg, "publications.html", "Publications", content, body_class="page-pubs")


# ----------------------------------------------------------------- projects
def build_projects(cfg, d):
    def card(p):
        meta = []
        if S(p.get("role")):
            meta.append(E(S(p.get("role"))))
        if S(p.get("funder")):
            meta.append(E(S(p.get("funder"))))
        if money(p.get("amount_eur")):
            meta.append(money(p.get("amount_eur")))
        if S(p.get("grant_number")):
            meta.append("grant " + E(S(p.get("grant_number"))))
        chips = []
        for t in topics_of(p, cfg)[:4]:
            chips.append('<span class="chip">%s</span>' % E(t))
        title = E(S(p.get("acronym")) or p["_slug"])
        sub = E(p["_slug"]) if S(p.get("acronym")) and p["_slug"] != S(p.get("acronym")) else ""
        img = ('<img class="pimg" src="%s" alt="" loading="lazy">' % E(p["_image_url"])
               if p.get("_image_url") else "")
        return ('<article class="pcard">%s'
                '<div class="pcard-body">'
                '<header><h3>%s</h3><span class="when">%s</span></header>'
                '%s<p class="pd">%s</p><p class="pm">%s</p>%s</div></article>'
                % (img, title, span(p["_start"], p["_end"]),
                   ('<p class="psub">%s</p>' % sub) if sub else "",
                   md_inline(S(p.get("short"))),
                   " &middot; ".join(meta),
                   ('<div class="chips">%s</div>' % "".join(chips)) if chips else ""))

    active = [p for p in d.projects if p["_active"]]
    done = [p for p in d.projects if not p["_active"]]
    out = []
    if active:
        out.append(section("Current projects", "", '<div class="pgrid">%s</div>'
                           % "".join(card(p) for p in active)))
    if done:
        out.append(section("Completed projects", "", '<div class="pgrid">%s</div>'
                           % "".join(card(p) for p in done)))

    if d.funding:
        rows = []
        total = 0
        for f in d.funding:
            total += I(f.get("amount_eur"))
            bits = [S(f.get("funder")), S(f.get("programme")), S(f.get("role"))]
            rows.append('<div class="frow"><div class="fy">%s</div><div>'
                        '<p class="ft">%s</p><p class="fm">%s</p></div>'
                        '<div class="fa">%s%s</div></div>'
                        % (E(S(f.get("year")) or fmt_date(f.get("startdate"))),
                           E(S(f.get("title"))),
                           " &middot; ".join(E(b) for b in bits if b),
                           money(f.get("amount_eur")),
                           ('<br><span class="fd">%s</span>' % E(S(f.get("duration"))))
                           if S(f.get("duration")) else ""))
        lead = "Third-party funding and fellowships acquired, %s in total." % money(total)
        out.append(section("Funding", lead, "".join(rows)))
    return page(cfg, "projects.html", "Projects", "\n".join(out))


# -------------------------------------------------------------------- talks
TALK_GROUPS = [
    ("Invited talks", lambda n: S(n.get("category")) == "Invited Talk"),
    ("Contributed talks", lambda n: S(n.get("category")) == "Contributed Talk"),
    ("Posters", lambda n: S(n.get("category")) == "Poster" or S(n.get("format")) == "Poster"),
    ("Invited seminars", lambda n: S(n.get("category")) == "Invited Seminar"),
    ("Workshop lectures", lambda n: S(n.get("category")) == "Workshop Lecture"),
]


def talk_row(n):
    where = ", ".join(x for x in [S(n.get("venue")), S(n.get("city")), S(n.get("country"))] if x)
    occ = S(n.get("occasion_name")) or S(n.get("title"))
    url = S(n.get("url"))
    name = ('<a href="%s" rel="noopener">%s</a>' % (E(url), E(occ))) if url else E(occ)
    return ('<div class="talk"><div class="yr">%s</div><div>'
            '<p class="tt">%s</p><p class="tw">%s</p></div></div>'
            % (E(month_year(n.get("year"), n.get("month"))), name, E(where)))


def build_talks(cfg, d):
    used, out = set(), []
    for label, test in TALK_GROUPS:
        rows = [n for n in d.talks if test(n) and id(n) not in used]
        for n in rows:
            used.add(id(n))
        if rows:
            out.append(section(label, "", "".join(talk_row(n) for n in rows)))
    rest = [n for n in d.talks if id(n) not in used]
    if rest:
        out.append(section("Other contributions", "", "".join(talk_row(n) for n in rest)))
    return page(cfg, "talks.html", "Talks and posters", "\n".join(out))


# ----------------------------------------------------------------- teaching
def build_teaching(cfg, d):
    out = []
    rows = []
    for t in d.teaching:
        when = S(t.get("term")) or span(S(t.get("year_start")), S(t.get("year_end")), "present")
        if not when:
            when = S(t.get("year_start"))
        where = ", ".join(x for x in [S(t.get("institution")), S(t.get("location"))] if x)
        meta = " &middot; ".join(E(x) for x in [S(t.get("role")), S(t.get("level")),
                                                S(t.get("language"))] if x)
        # Only the curated `summary:` field is published — note bodies stay private.
        rows.append('<div class="talk"><div class="yr">%s</div><div>'
                    '<p class="tt">%s</p><p class="tw">%s</p>%s%s</div></div>'
                    % (when, E(S(t.get("course")) or S(t.get("title")) or t["_slug"]), E(where),
                       ('<p class="tm">%s</p>' % meta) if meta else "",
                       ('<p class="ts">%s</p>' % md_inline(S(t.get("summary"))))
                       if S(t.get("summary")) else ""))
    if rows:
        out.append(section("Teaching", "", "".join(rows)))

    for cat, label in (("Mentoring", "Mentoring and supervision"), ("Outreach", "Outreach")):
        items = [s for s in d.service if S(s.get("category")) == cat]
        if items:
            out.append(section(label, "", "".join(md_block(s.get("_body", "")) for s in items)))
    return page(cfg, "teaching.html", "Teaching", "\n".join(out))


# ----------------------------------------------------------------------- CV
def build_cv(cfg, d):
    prof, prose = d.profile, d.prose
    out = []

    contact = []
    if S(prof.get("email")):
        contact.append('<a href="mailto:%s" rel="noopener">Email</a>' % obf_mail(S(prof.get("email"))))
    for label, value in (("ORCID", S(prof.get("orcid"))), ("Google Scholar", S(prof.get("scholar")))):
        if value:
            contact.append('<a href="%s" rel="noopener">%s</a>' % (E(value), E(label)))
    pdf_link = '<a href="cv.pdf" rel="noopener">Download PDF</a>' if cfg.get("_cv_pdf_ok") else ""
    md_link = '<a href="cv.md" rel="noopener">Download Markdown</a>' if cfg.get("_cv_md_ok") else ""
    head = """<section class="hero cvhead"><div class="wrap">
  <img class="portrait small" src="assets/img/profile.jpg" alt="" width="560" height="560">
  <h1 class="name">%s</h1>
  <p class="role"><strong>%s</strong><br>%s<br>%s</p>
  <div class="social">%s%s%s</div>
</div></section>""" % (E(S(prof.get("name"))),
                       E(S(prof.get("position"))),
                       E(" &middot; ".join(x for x in [S(prof.get("position_second"))] if x)),
                       E(", ".join(x for x in [S(prof.get("organisation")),
                                               S(prof.get("address_line"))] if x)),
                       "\n    ".join(contact), pdf_link, md_link)
    out.append(head)

    def rows(items, left, right):
        return "".join('<div class="cvrow"><div class="yr">%s</div><div>%s</div></div>'
                       % (left(i), right(i)) for i in items)

    if d.education:
        out.append(section("Education", "", rows(
            d.education,
            lambda e: span(e.get("startdate"), e.get("enddate")) or fmt_date(e.get("enddate")),
            lambda e: "<p class=\"tt\">%s</p><p class=\"tw\">%s</p>%s%s" % (
                E(S(e.get("degree")) or S(e.get("title"))),
                E(", ".join(x for x in [S(e.get("institution")), S(e.get("location"))] if x)),
                ('<p class="tm">Thesis: <em>%s</em>%s</p>' % (
                    E(S(e.get("thesis"))),
                    (" (grade: %s)" % E(S(e.get("grade")))) if S(e.get("grade")) else ""))
                if S(e.get("thesis")) else "",
                ('<p class="tm">Supervisor: %s</p>' % E(S(e.get("supervisor"))))
                if S(e.get("supervisor")) else ""))))

    if d.positions:
        out.append(section("Professional experience", "", rows(
            d.positions,
            lambda p: span(p.get("startdate"), p.get("enddate")),
            lambda p: '<p class="tt">%s</p><p class="tw">%s</p>%s' % (
                E(S(p.get("title"))),
                E(", ".join(x for x in [S(p.get("organisation")), S(p.get("location"))] if x)),
                md_block(p.get("_body", ""))))))

    if d.funding:
        out.append(section("Third-party funding", "", rows(
            d.funding,
            lambda f: E(S(f.get("year")) or fmt_date(f.get("startdate"))),
            lambda f: '<p class="tt">%s</p><p class="tw">%s</p>' % (
                E(S(f.get("title"))),
                " &middot; ".join(E(x) for x in [S(f.get("funder")), S(f.get("role")),
                                                 money(f.get("amount_eur")),
                                                 S(f.get("duration"))] if x)))))

    org = [s for s in d.service if S(s.get("category")) == "Conference organization"]
    if org:
        org.sort(key=lambda s: -I(s.get("year")))
        out.append(section("Conference organization", "", rows(
            org, lambda s: E(S(s.get("year"))),
            lambda s: '<p class="tt">%s</p><p class="tw">%s</p>%s' % (
                E(S(s.get("title"))),
                " &middot; ".join(E(x) for x in [S(s.get("role")), S(s.get("location")),
                                                 S(s.get("country"))] if x),
                md_block(s.get("_body", ""))))))

    if d.teaching:
        out.append(section("Teaching", "", rows(
            d.teaching,
            lambda t: E(S(t.get("term")) or span(S(t.get("year_start")), S(t.get("year_end")))),
            lambda t: '<p class="tt">%s</p><p class="tw">%s</p>' % (
                E(S(t.get("course")) or S(t.get("title"))),
                " &middot; ".join(E(x) for x in [S(t.get("role")), S(t.get("institution")),
                                                 S(t.get("location"))] if x)))))

    # skills, languages, methods
    prof_rows = []
    for label, key in (("Languages", "languages"),
                       ("Operating systems", "skills_os"),
                       ("Quantum chemistry codes", "skills_qc"),
                       ("Programming", "skills_programming"),
                       ("Other software", "skills_other")):
        v = S(prof.get(key))
        if v:
            prof_rows.append('<div class="cvrow"><div class="yr">%s</div><div><p class="tw">%s</p></div></div>'
                             % (E(label), E(v)))
    if prof_rows:
        out.append(section("Skills and languages", "", "".join(prof_rows)))

    meth_rows = []
    for label, key in (("Ab-initio and DFT", "methods_abinitio"),
                       ("Basic techniques", "methods_basic"),
                       ("Advanced techniques", "methods_advanced"),
                       ("Other", "methods_other")):
        v = S(prof.get(key))
        if v:
            meth_rows.append('<div class="cvrow"><div class="yr">%s</div><div><p class="tw">%s</p></div></div>'
                             % (E(label), E(v)))
    if meth_rows:
        out.append(section("Quantum chemical methods", "", "".join(meth_rows)))

    rev = [s for s in d.service if S(s.get("category")) == "Reviewing"]
    if rev:
        js = []
        for s in rev:
            js += L(s.get("journals"))
        out.append(section("Reviewing activities", "",
                           '<ul class="cols">%s</ul>' % "".join("<li>%s</li>" % E(j) for j in js)))

    mem = [s for s in d.service if S(s.get("category")) in ("Membership", "Mentoring", "Outreach")]
    for s in mem:
        out.append(section(S(s.get("title")), "", md_block(s.get("_body", ""))))

    # talks summary
    counts = {}
    for n in d.talks:
        counts[S(n.get("category")) or "Other"] = counts.get(S(n.get("category")) or "Other", 0) + 1
    if counts:
        li = "".join("<li>%s: %d</li>" % (E(k), v) for k, v in sorted(counts.items()))
        out.append(section("Talks and posters", "",
                           '<ul class="cols">%s</ul>'
                           '<a class="more" href="talks.html">Full list &rarr;</a>' % li))

    if d.publications:
        items = []
        total = len(d.publications)
        for i, n in enumerate(d.publications):
            items.append('<div class="cvpub"><div class="no">%d</div><div>'
                         '<p class="t">%s</p><p class="a">%s</p><p class="j">%s</p></div></div>'
                         % (total - i, E(S(n.get("publication"))),
                            highlight_authors(n.get("authors"), cfg["highlight_author"]),
                            " &middot; ".join(x for x in [
                                ("<i>%s</i>" % E(S(n.get("journal")))) if S(n.get("journal")) else "",
                                ("<b>%s</b>, %s" % (E(S(n.get("volume"))), E(S(n.get("pages")))))
                                if S(n.get("volume")) else E(S(n.get("pages"))),
                                E(S(n.get("pubyear")))] if x)))
        out.append(section("Peer-reviewed journal articles",
                           "%d articles." % total, "".join(items)))

    return page(cfg, "cv.html", "Curriculum Vitae", "\n".join(out), body_class="page-cv")


# ------------------------------------------------------------------- contact
def build_contact(cfg, d):
    prof = d.profile
    out = []

    links = social_links(prof, include_cv=True)
    if links:
        row = "".join('<a href="%s" rel="noopener">%s</a>' % (href, text) for href, text in links)
        out.append(section("Get in touch", "", '<div class="social">%s</div>' % row))

    imp = cfg.get("impressum") or {}
    if imp.get("enabled"):
        parts = []
        name = S(imp.get("responsible_name")) or S(prof.get("name"))
        if name:
            parts.append("<p><strong>%s</strong></p>" % E(name))
        addr = [S(x) for x in (imp.get("address_lines") or []) if S(x)]
        if not addr and S(prof.get("address_line")):
            addr = [a.strip() for a in S(prof.get("address_line")).split(",") if a.strip()]
        if addr:
            parts.append("<p>%s</p>" % "<br>".join(E(a) for a in addr))
        email = S(imp.get("email")) or S(prof.get("email"))
        if email:
            parts.append('<p><a href="mailto:%s" rel="noopener">%s</a></p>'
                         % (obf_mail(email), obf_mail(email)))
        if S(imp.get("phone")):
            parts.append("<p>%s</p>" % E(S(imp.get("phone"))))
        if S(imp.get("extra")):
            parts.append(md_block(S(imp.get("extra"))))
        if parts:
            out.append(section("Impressum", "", "".join(parts), anchor="impressum"))

    if not out:
        out.append(section("Contact", "", "<p>No contact details configured yet.</p>"))

    return page(cfg, "contact.html", "Contact", "\n".join(out))


# ===========================================================================
#  LaTeX CV
# ===========================================================================

# Characters that plain pdflatex + inputenc cannot typeset on its own.  Anything
# listed here is declared via \newunicodechar in the preamble, but only when it
# actually occurs in the document.
TEX_UNICODE = {}


def _fill_greek():
    names = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu "
             "nu xi omicron pi rho finalsigma sigma tau upsilon phi chi psi omega").split()
    for i, name in enumerate(names):
        lo = chr(0x03B1 + i)
        if name == "finalsigma":
            TEX_UNICODE[lo] = r"\ensuremath{\varsigma}"
            continue
        TEX_UNICODE[lo] = r"\ensuremath{\%s}" % name
        up = chr(0x0391 + i)
        TEX_UNICODE[up] = (r"\ensuremath{\%s}" % name.capitalize()
                           if name in ("gamma", "delta", "theta", "lambda", "xi", "pi",
                                       "sigma", "upsilon", "phi", "psi", "omega")
                           else r"\ensuremath{\mathrm{%s}}" % up)


_fill_greek()
for _i, _d in enumerate("0123456789"):
    TEX_UNICODE[chr(0x2080 + _i)] = r"\ensuremath{_%s}" % _d          # ₀…₉
TEX_UNICODE.update({
    "²": r"\ensuremath{^2}", "³": r"\ensuremath{^3}", "¹": r"\ensuremath{^1}",
    "⁺": r"\ensuremath{^+}", "⁻": r"\ensuremath{^-}",
    "₊": r"\ensuremath{_+}", "₋": r"\ensuremath{_-}",
    "·": r"\ensuremath{\cdot}", "×": r"\ensuremath{\times}",
    "→": r"\ensuremath{\rightarrow}", "←": r"\ensuremath{\leftarrow}",
    "⇌": r"\ensuremath{\rightleftharpoons}",
    "≈": r"\ensuremath{\approx}", "≤": r"\ensuremath{\leq}",
    "≥": r"\ensuremath{\geq}", "±": r"\ensuremath{\pm}",
    "å": r"\aa{}", "Å": r"\AA{}", "°": r"\textdegree{}",
})

# Straightforward replacements applied to every string.
TEX_PLAIN = [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
             ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
             ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
             ("€", r"\texteuro{}"),
             ("‐", "-"), ("−", r"\ensuremath{-}"), (" ", "~")]


def tex_escape(s):
    s = S(s)
    for a, b in TEX_PLAIN:
        s = s.replace(a, b)
    return s


def load_title_breaks():
    """Optional, user-maintained line-break hints for long publication
    titles that pdflatex can't wrap on its own -- chemical formulas like
    "[Ni(ZnMe)6(ZnCp*)2]" have no spaces or hyphens for TeX to break at, so
    without a hint they either overflow the page margin or force very loose
    spacing on the rest of the line. See _build/title-breaks.yaml.
    """
    path = os.path.join(HERE, "title-breaks.yaml")
    if not os.path.isfile(path):
        return {}
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError:
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def tex_escape_with_breaks(text, breaks):
    """tex_escape(), plus user-supplied manual break points from
    title-breaks.yaml. A '|' in a hint's replacement becomes an invisible
    optional break (\\allowbreak) -- nothing is shown unless the line
    actually wraps there, so it's safe to sprinkle liberally.
    """
    t = S(text)
    for bad, good in breaks.items():
        if bad and bad in t:
            t = t.replace(bad, good)
    return tex_escape(t).replace("|", r"\allowbreak{}")


def highlight_authors_tex(authors, pattern):
    """LaTeX counterpart of highlight_authors(): bold the CV owner's own
    name (highlight_author in config.yaml) wherever it appears in an
    author list, matching what publications.html already does on the site.
    """
    text = tex_escape(authors)
    if not text:
        return ""
    try:
        return re.sub("(%s)" % pattern, r"\\textbf{\1}", text)
    except re.error:
        return text


def tex_unicode_preamble(document):
    """Declare only those special characters that really occur in the document."""
    lines, unknown = [], set()
    for ch in sorted(set(document)):
        if ord(ch) < 128 or unicodedata.category(ch) == "Ll" and ord(ch) < 0x0180:
            continue
        if ord(ch) < 0x0100:          # Latin-1: inputenc + T1 handle these
            continue
        if ch in TEX_UNICODE:
            lines.append(r"\newunicodechar{%s}{%s}" % (ch, TEX_UNICODE[ch]))
        elif ord(ch) > 0x2019 and unicodedata.category(ch).startswith("P"):
            continue                  # dashes and quotes: inputenc copes
        elif ch not in "–—‘’“”…":
            unknown.add(ch)
    for ch in sorted(unknown):
        lines.append(r"\newunicodechar{%s}{\textbf{?}}" % ch)
        print("  LaTeX warning : no mapping for %r (U+%04X, %s) - add it to "
              "TEX_UNICODE in build.py" % (ch, ord(ch), unicodedata.name(ch, "?")))
    return "\n".join(lines)


def build_latex_cv(cfg, d):
    prof = d.profile
    o = []
    A = o.append
    A(r"""% Generated by _build/build.py -- do not edit by hand.
% Header/field-row layout inspired by the "curve" CV class
% (https://www.overleaf.com/latex/templates/a-customised-curve-cv/mvmbhkwsnmwv),
% reimplemented here as plain article + standard packages so the build
% keeps compiling with a bare pdflatex -- no curve.cls, fontawesome5,
% simpleicons or extra font packages required.
\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[margin=2.4cm]{geometry}
\usepackage{textcomp}
\usepackage{enumitem}
\usepackage{newunicodechar}
%%UNICODE%%
\usepackage[colorlinks=true,urlcolor=cvblue,linkcolor=cvblue]{hyperref}
\usepackage{xcolor}
\definecolor{cvpetrol}{HTML}{10635C}
\definecolor{cvblue}{HTML}{1F5FA8}
\usepackage{titlesec}
\titleformat{\section}{\color{cvpetrol}\large\bfseries}{}{0pt}{}[\vspace{-6pt}\color{cvpetrol}\rule{\linewidth}{0.6pt}]
\titlespacing{\section}{0pt}{16pt}{8pt}
\newcommand{\entry}[2]{\noindent\begin{minipage}[t]{0.20\linewidth}\raggedleft\small\color{black!60}#1\end{minipage}%
\hspace{0.02\linewidth}\begin{minipage}[t]{0.76\linewidth}#2\end{minipage}\par\vspace{5pt}}
\newcommand{\cvfield}[2]{{\color{cvblue}\bfseries\scriptsize #1}~#2}
\setlength{\parindent}{0pt}
\pagestyle{empty}
\begin{document}
""")
    A(r"{\sffamily\Huge\bfseries\color{cvpetrol}%s}\par\vspace{3pt}" % tex_escape(S(prof.get("name"))))
    A(r"{\large\color{black!70}%s}\par" % tex_escape(S(prof.get("position"))))
    if S(prof.get("position_second")):
        A(r"{\large\color{black!70}%s}\par" % tex_escape(S(prof.get("position_second"))))
    A(r"\vspace{5pt}{\color{cvblue}\rule{\linewidth}{1.1pt}}\par\vspace{7pt}")

    def short_url(u):
        return re.sub(r"^https?://(www\.)?", "", S(u)).rstrip("/")

    field_defs = []
    if S(prof.get("email")):
        field_defs.append(("Email", "mailto:%s" % S(prof.get("email")), S(prof.get("email"))))
    if S(prof.get("orcid")):
        field_defs.append(("ORCID", S(prof.get("orcid")), short_url(prof.get("orcid")).replace("orcid.org/", "")))
    if S(prof.get("scholar")):
        field_defs.append(("Scholar", S(prof.get("scholar")), "profile"))
    if S(prof.get("github")):
        field_defs.append(("GitHub", S(prof.get("github")), short_url(prof.get("github")).split("/")[-1]))
    if S(prof.get("linkedin")):
        field_defs.append(("LinkedIn", S(prof.get("linkedin")), short_url(prof.get("linkedin")).split("/")[-1]))
    if field_defs:
        # \sloppy (scoped to this one paragraph): with several short, non-
        # hyphenatable \mbox'd fields on one line, plain LaTeX's default
        # \tolerance can fail to find ANY feasible break and silently runs
        # the whole row off the page edge instead of wrapping it -- \sloppy
        # relaxes spacing so it wraps onto a second line when needed.
        A((r"{\sloppy " + r"\ \hspace{0.7em}".join(
            r"\mbox{\cvfield{%s}{\href{%s}{%s}}}" % (lbl, href, tex_escape(disp))
            for lbl, href, disp in field_defs)) + r"\par}\vspace{3pt}")

    A(r"{\color{black!65}\small %s}\par" % tex_escape(
        ", ".join(x for x in [S(prof.get("organisation")), S(prof.get("address_line"))] if x)))
    A(r"\vspace{10pt}")

    def sec(title, body):
        if body.strip():
            A(r"\section*{%s}" % tex_escape(title))
            A(body)

    def entries(items, left, right):
        return "\n".join(r"\entry{%s}{%s}" % (left(i), right(i)) for i in items)

    def clean(t):
        return tex_escape(re.sub(r"&\w+;", "", t.replace("&ndash;", "--")))

    sec("Education", entries(
        d.education,
        lambda e: clean(span(e.get("startdate"), e.get("enddate"))),
        lambda e: r"\textbf{%s}, \emph{%s}%s" % (
            tex_escape(S(e.get("degree")) or S(e.get("title"))),
            tex_escape(S(e.get("institution"))),
            (r"\\ \small Thesis: \emph{%s}" % tex_escape(S(e.get("thesis")))) if S(e.get("thesis")) else "")))

    sec("Professional experience", entries(
        d.positions,
        lambda p: clean(span(p.get("startdate"), p.get("enddate"))),
        lambda p: r"\textbf{%s}, \emph{%s}%s" % (
            tex_escape(S(p.get("title"))), tex_escape(S(p.get("organisation"))),
            (r"\\ \small %s" % tex_escape(re.sub(r"\s+", " ", S(p.get("_body")).strip())))
            if S(p.get("_body")).strip() else "")))

    sec("Third-party funding", entries(
        d.funding,
        lambda f: tex_escape(S(f.get("year"))),
        lambda f: r"\textbf{%s}\\ \small %s" % (
            tex_escape(S(f.get("title"))),
            tex_escape(" | ".join(x for x in [S(f.get("funder")), S(f.get("role")),
                                              money(f.get("amount_eur")),
                                              S(f.get("duration"))] if x)))))

    org = sorted([s for s in d.service if S(s.get("category")) == "Conference organization"],
                 key=lambda s: -I(s.get("year")))
    sec("Conference organization", entries(
        org, lambda s: tex_escape(S(s.get("year"))),
        lambda s: r"\textbf{%s}\\ \small %s" % (
            tex_escape(S(s.get("title"))),
            tex_escape(", ".join(x for x in [S(s.get("role")), S(s.get("location")),
                                             S(s.get("country"))] if x)))))

    sec("Teaching", entries(
        d.teaching,
        lambda t: tex_escape(S(t.get("term")) or clean(span(S(t.get("year_start")), S(t.get("year_end"))))),
        lambda t: r"\textbf{%s}\\ \small %s" % (
            tex_escape(S(t.get("course")) or S(t.get("title"))),
            tex_escape(", ".join(x for x in [S(t.get("role")), S(t.get("institution")),
                                             S(t.get("location"))] if x)))))

    talks_by = {}
    for n in d.talks:
        talks_by.setdefault(S(n.get("category")) or "Other", []).append(n)
    body = []
    for cat in ("Invited Talk", "Contributed Talk", "Poster", "Invited Seminar", "Workshop Lecture"):
        for n in talks_by.get(cat, []):
            body.append(r"\entry{%s}{\textbf{%s}, %s\\ \small %s}" % (
                tex_escape(month_year(n.get("year"), n.get("month"))),
                tex_escape(S(n.get("occasion_name")) or S(n.get("title"))),
                tex_escape(", ".join(x for x in [S(n.get("city")), S(n.get("country"))] if x)),
                tex_escape(cat)))
    sec("Talks and posters", "\n".join(body))

    if d.publications:
        breaks = load_title_breaks()
        pubs = []
        total = len(d.publications)
        # Angewandte Chemie reference style: authors, title, journal + bold
        # year, italic volume, pages. \sloppy (scoped to the whole list) lets
        # long titles wrap onto the next line with slightly looser spacing
        # instead of silently overflowing the page margin -- see also
        # title-breaks.yaml for chemical formulas that have no natural break
        # point at all.
        pubs.append(r"{\sloppy\begin{enumerate}[leftmargin=2.2em,itemsep=4pt,start=1]")
        for i, n in enumerate(d.publications):
            journal, year = S(n.get("journal")), S(n.get("pubyear"))
            journal_year = " ".join(x for x in [
                (r"\emph{%s}" % tex_escape(journal)) if journal else "",
                (r"\textbf{%s}" % tex_escape(year)) if year else ""] if x)
            tail = ", ".join(x for x in [
                journal_year,
                (r"\emph{%s}" % tex_escape(S(n.get("volume")))) if S(n.get("volume")) else "",
                tex_escape(S(n.get("pages")))] if x)
            pubs.append(r"\item[%d.] %s, %s, %s." % (
                total - i,
                highlight_authors_tex(n.get("authors"), cfg["highlight_author"]),
                tex_escape_with_breaks(n.get("publication"), breaks), tail))
        pubs.append(r"\end{enumerate}}")
        sec("Peer-reviewed journal articles", "\n".join(pubs))

    A(r"\end{document}")
    doc = "\n".join(o)
    return doc.replace("%%UNICODE%%", tex_unicode_preamble(doc))


MD_ESCAPE_RE = re.compile(r"([\\`*_{}\[\]#])")


def md_escape(s):
    """Escape Markdown special characters in raw (non-Markdown) text."""
    return MD_ESCAPE_RE.sub(r"\\\1", S(s))


def md_highlight_authors(authors, pattern):
    """Markdown counterpart of highlight_authors_tex(): bold the CV owner's
    own name in an author list.
    """
    text = md_escape(authors)
    if not text:
        return ""
    try:
        return re.sub("(%s)" % pattern, r"**\1**", text)
    except re.error:
        return text


def build_markdown_cv(cfg, d):
    """Plain-Markdown rendering of the CV -- same data and structure as
    build_latex_cv(), written to cv.md next to cv.html/cv.pdf. Pure Python,
    no external tools (no pandoc, no YAMLResume) -- one more free-standing
    export of the same underlying vault data.
    """
    prof = d.profile
    o = []
    A = o.append

    A("# %s" % md_escape(S(prof.get("name"))))
    A("")
    for r in (S(prof.get("position")), S(prof.get("position_second"))):
        if r:
            A("**%s**  " % md_escape(r))
    org_line = ", ".join(x for x in [S(prof.get("organisation")), S(prof.get("address_line"))] if x)
    if org_line:
        A(md_escape(org_line) + "  ")
    if S(prof.get("email")):
        A("[%s](mailto:%s)" % (md_escape(S(prof.get("email"))), S(prof.get("email"))))
    A("")

    def sec(title, body):
        if body.strip():
            A("## %s" % title)
            A("")
            A(body)
            A("")

    def entries(items, left, right):
        return "\n\n".join("**%s**  \n%s" % (left(i), right(i)) for i in items)

    def clean_md(t):
        return re.sub(r"&\w+;", "", t.replace("&ndash;", "–"))

    sec("Education", entries(
        d.education,
        lambda e: clean_md(span(e.get("startdate"), e.get("enddate"))),
        lambda e: "%s, *%s*%s" % (
            md_escape(S(e.get("degree")) or S(e.get("title"))),
            md_escape(S(e.get("institution"))),
            ("  \nThesis: *%s*" % md_escape(S(e.get("thesis")))) if S(e.get("thesis")) else "")))

    sec("Professional experience", entries(
        d.positions,
        lambda p: clean_md(span(p.get("startdate"), p.get("enddate"))),
        lambda p: "%s, *%s*%s" % (
            md_escape(S(p.get("title"))), md_escape(S(p.get("organisation"))),
            ("  \n%s" % md_escape(re.sub(r"\s+", " ", S(p.get("_body")).strip())))
            if S(p.get("_body")).strip() else "")))

    sec("Third-party funding", entries(
        d.funding,
        lambda f: md_escape(S(f.get("year"))),
        lambda f: "%s  \n%s" % (
            md_escape(S(f.get("title"))),
            md_escape(" | ".join(x for x in [S(f.get("funder")), S(f.get("role")),
                                              money(f.get("amount_eur")),
                                              S(f.get("duration"))] if x)))))

    org = sorted([s for s in d.service if S(s.get("category")) == "Conference organization"],
                 key=lambda s: -I(s.get("year")))
    sec("Conference organization", entries(
        org, lambda s: md_escape(S(s.get("year"))),
        lambda s: "%s  \n%s" % (
            md_escape(S(s.get("title"))),
            md_escape(", ".join(x for x in [S(s.get("role")), S(s.get("location")),
                                             S(s.get("country"))] if x)))))

    sec("Teaching", entries(
        d.teaching,
        lambda t: md_escape(S(t.get("term")) or clean_md(span(S(t.get("year_start")), S(t.get("year_end"))))),
        lambda t: "%s  \n%s" % (
            md_escape(S(t.get("course")) or S(t.get("title"))),
            md_escape(", ".join(x for x in [S(t.get("role")), S(t.get("institution")),
                                             S(t.get("location"))] if x)))))

    talks_by = {}
    for n in d.talks:
        talks_by.setdefault(S(n.get("category")) or "Other", []).append(n)
    body = []
    for cat in ("Invited Talk", "Contributed Talk", "Poster", "Invited Seminar", "Workshop Lecture"):
        for n in talks_by.get(cat, []):
            body.append("**%s**  \n%s, %s  \n%s" % (
                md_escape(month_year(n.get("year"), n.get("month"))),
                md_escape(S(n.get("occasion_name")) or S(n.get("title"))),
                md_escape(", ".join(x for x in [S(n.get("city")), S(n.get("country"))] if x)),
                md_escape(cat)))
    sec("Talks and posters", "\n\n".join(body))

    if d.publications:
        pubs = []
        total = len(d.publications)
        # Same Angewandte Chemie-style order as the PDF/LaTeX CV: authors,
        # title, journal + bold year, italic volume, pages.
        for i, n in enumerate(d.publications):
            journal, year = S(n.get("journal")), S(n.get("pubyear"))
            journal_year = " ".join(x for x in [
                ("*%s*" % md_escape(journal)) if journal else "",
                ("**%s**" % md_escape(year)) if year else ""] if x)
            tail = ", ".join(x for x in [
                journal_year,
                ("*%s*" % md_escape(S(n.get("volume")))) if S(n.get("volume")) else "",
                md_escape(S(n.get("pages")))] if x)
            pubs.append("%d. %s, %s, %s." % (
                total - i, md_highlight_authors(S(n.get("authors")), cfg["highlight_author"]),
                md_escape(S(n.get("publication"))), tail))
        sec("Peer-reviewed journal articles", "\n".join(pubs))

    return "\n".join(o).rstrip() + "\n"


def build_cv_markdown(cfg, d, out_dir):
    """Write cv.md - a plain-Markdown rendering of the CV, generated purely
    in Python from the same vault data as cv.html/cv.pdf. No external tools
    (no pandoc, no Node/YAMLResume) -- switch off with markdown_cv: false.
    Returns True when cv.md was written.
    """
    if not cfg["options"].get("markdown_cv", True):
        return False
    md = build_markdown_cv(cfg, d)
    with io.open(os.path.join(out_dir, "cv.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    print("  cv.md         : written (%d kB)" % (len(md.encode("utf-8")) // 1024))
    return True


# ===========================================================================
#  Extras
# ===========================================================================

def build_bib(d):
    return "\n\n".join(bibtex_entry(n) for n in d.publications) + "\n"


def build_sitemap(cfg):
    base = cfg["site"]["url"].rstrip("/")
    urls = "".join('<url><loc>%s/%s</loc><lastmod>%s</lastmod></url>'
                   % (base, href, TODAY.isoformat()) for _, href in cfg["nav"])
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls)


def build_feed(cfg, d):
    base = cfg["site"]["url"].rstrip("/")
    items = []
    for n in d.publications[:20]:
        items.append("""<item><title>%s</title><link>%s</link>
<guid isPermaLink="false">%s</guid><pubDate>%s</pubDate>
<description>%s</description></item>""" % (
            E(S(n.get("publication"))), E(doi_url(n) or base),
            E(bib_key(n)),
            "Thu, 01 Jan %s 00:00:00 +0000" % (S(n.get("pubyear")) or TODAY.year),
            E("%s. %s" % (S(n.get("authors")), S(n.get("journal"))))))
    return ("""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>%s</title><link>%s</link>
<description>%s</description>%s</channel></rss>\n"""
            % (E(cfg["site"]["title"]), E(base), E(cfg["site"]["description"]), "".join(items)))


def build_json(d):
    def pick(n, keys):
        return {k: S(n.get(k)) for k in keys}
    return {
        "publications.json": [dict(pick(n, ["publication", "authors", "journal", "volume",
                                            "pages", "doi", "pubyear", "topics", "category",
                                            "openaccess"]), bibkey=bib_key(n))
                              for n in d.publications],
        "talks.json": [pick(n, ["title", "occasion_name", "occasion_type", "category", "format",
                                "year", "month", "city", "country", "venue"]) for n in d.talks],
        "projects.json": [dict(pick(n, ["acronym", "short", "role", "funder", "programme",
                                        "grant_number", "amount_eur", "status", "category"]),
                               name=n["_slug"], start=n["_start"], end=n["_end"],
                               active=n["_active"]) for n in d.projects],
        "funding.json": [pick(n, ["title", "funder", "programme", "role", "amount_eur",
                                  "grant_number", "year", "duration"]) for n in d.funding],
        "teaching.json": [pick(n, ["title", "institution", "role", "level", "term",
                                   "year_start", "year_end", "location"]) for n in d.teaching],
    }


def build_cv_pdf(cfg, d, out_dir, verbose=False):
    """Typeset the CV to PDF and publish it as cv.pdf.

    The LaTeX source is generated into _build/generated/ (never into the
    website root, so it is never offered as a download) and compiled with
    pdflatex when that is installed. Returns True when cv.pdf was written.
    """
    if not cfg["options"].get("latex_cv", True):
        return False

    tex = build_latex_cv(cfg, d)
    work_dir = os.path.join(HERE, "generated")
    os.makedirs(work_dir, exist_ok=True)
    tex_path = os.path.join(work_dir, "cv.tex")
    io.open(tex_path, "w", encoding="utf-8").write(tex)

    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        print("  cv.pdf        : SKIPPED - pdflatex is not installed.")
        print("                  Install a LaTeX distribution (e.g. 'sudo apt install "
              "texlive-latex-base texlive-latex-extra texlive-fonts-recommended') "
              "and rebuild, or open the print stylesheet on cv.html instead "
              "(browser -> Print -> Save as PDF).")
        print("                  The LaTeX source is kept at _build/generated/cv.tex.")
        return False

    import subprocess
    ok = True
    for pass_no in (1, 2):  # twice, so hyperref's cross references settle
        try:
            result = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "cv.tex"],
                cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=90)
        except Exception as exc:
            print("  cv.pdf        : FAILED to run pdflatex (%s)" % exc)
            ok = False
            break
        if result.returncode != 0:
            ok = False
            log = result.stdout.decode("utf-8", "replace")
            errors = [l for l in log.split("\n") if l.startswith("!")]
            print("  cv.pdf        : FAILED (pdflatex exit %d)" % result.returncode)
            for l in errors[:5]:
                print("                  %s" % l)
            print("                  Full log: _build/generated/cv.log")
            break

    pdf_src = os.path.join(work_dir, "cv.pdf")
    if ok and os.path.isfile(pdf_src):
        shutil.copy2(pdf_src, os.path.join(out_dir, "cv.pdf"))
        print("  cv.pdf        : compiled (%d kB)"
              % (os.path.getsize(pdf_src) // 1024))
        return True

    # A previous successful build may have left a stale PDF published -
    # remove it rather than serve outdated content silently.
    stale = os.path.join(out_dir, "cv.pdf")
    if os.path.isfile(stale):
        os.remove(stale)
    return False


# ===========================================================================
#  Main
# ===========================================================================

def resolve_vault(cfg, cli_vault):
    """Pick the vault path to use on THIS computer.

    Tried in order, first match wins:
      1. --vault on the command line.
      2. The WEBSITE_VAULT_PATH environment variable.
      3. Every entry under 'vault:' in config.yaml - a single path, or a
         list of candidate paths, which is handy when the same config.yaml
         is shared across several computers (e.g. via the git repo) and the
         vault isn't always mounted at the same location.
    The first candidate that actually exists as a directory wins.
    """
    candidates = []
    if cli_vault:
        candidates.append(cli_vault)
    env = os.environ.get("WEBSITE_VAULT_PATH")
    if env:
        candidates.append(env)
    cfg_vault = cfg.get("vault")
    if isinstance(cfg_vault, (list, tuple)):
        candidates.extend(cfg_vault)
    elif cfg_vault:
        candidates.append(cfg_vault)

    for c in candidates:
        p = os.path.expanduser(str(c))
        if os.path.isdir(p):
            return p

    tried = "\n".join("  - %s" % os.path.expanduser(str(c)) for c in candidates)
    sys.exit("Vault not found. Tried:\n%s\n\n"
              "Fix 'vault:' in config.yaml (it may be a list of candidate paths, "
              "one per computer you build on), set the WEBSITE_VAULT_PATH "
              "environment variable, or pass --vault."
              % (tried or "  (nothing configured)"))


def main():
    ap = argparse.ArgumentParser(description="Build the website from the Obsidian vault.")
    ap.add_argument("--config", default=os.path.join(HERE, "config.yaml"))
    ap.add_argument("--vault", default=None,
                    help="override the vault path from the configuration file")
    ap.add_argument("--output", default=None,
                    help="override the output folder from the configuration file")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    with io.open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if args.output:
        cfg["output"] = args.output

    vault = resolve_vault(cfg, args.vault)
    cfg["vault"] = vault

    out_dir = os.path.abspath(os.path.join(HERE, "..", cfg.get("output", ".")))
    os.makedirs(out_dir, exist_ok=True)

    print("Reading vault   : %s" % vault)
    d = collect(cfg)
    cfg["_profile"] = d.profile

    print("  publications  : %d" % len(d.publications))
    print("  talks         : %d" % len(d.talks))
    print("  projects      : %d" % len(d.projects))
    print("  funding       : %d" % len(d.funding))
    print("  teaching      : %d" % len(d.teaching))
    print("  positions     : %d   education: %d   service: %d"
          % (len(d.positions), len(d.education), len(d.service)))

    n_img = copy_project_images(cfg, d, out_dir)
    if n_img:
        print("  project images: %d" % n_img)

    cfg["_cv_pdf_ok"] = build_cv_pdf(cfg, d, out_dir, verbose=args.verbose)
    cfg["_cv_md_ok"] = build_cv_markdown(cfg, d, out_dir)

    pages = {
        "index.html": build_index(cfg, d),
        "publications.html": build_publications(cfg, d),
        "projects.html": build_projects(cfg, d),
        "talks.html": build_talks(cfg, d),
        "teaching.html": build_teaching(cfg, d),
        "cv.html": build_cv(cfg, d),
        "contact.html": build_contact(cfg, d),
    }
    for name, text in pages.items():
        with io.open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write(text)
        if args.verbose:
            print("  wrote %s (%d kB)" % (name, len(text) // 1024))

    # assets
    src_assets = os.path.join(HERE, "assets")
    dst_assets = os.path.join(out_dir, "assets")
    os.makedirs(dst_assets, exist_ok=True)
    for fn in os.listdir(src_assets):
        s = os.path.join(src_assets, fn)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(dst_assets, fn))

    # profile photo: copy from the vault when the profile note points at one
    photo = S(d.profile.get("photo"))
    if photo:
        src = os.path.join(vault, photo)
        if os.path.isfile(src):
            os.makedirs(os.path.join(dst_assets, "img"), exist_ok=True)
            shutil.copy2(src, os.path.join(dst_assets, "img", "profile.jpg"))
            print("  photo         : taken from the vault")

    # data + extras
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    for name, payload in build_json(d).items():
        with io.open(os.path.join(data_dir, name), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, indent=1))

    opt = cfg["options"]
    if opt.get("bibtex"):
        io.open(os.path.join(out_dir, "publications.bib"), "w", encoding="utf-8").write(build_bib(d))
    if opt.get("sitemap"):
        io.open(os.path.join(out_dir, "sitemap.xml"), "w", encoding="utf-8").write(build_sitemap(cfg))
    if opt.get("feed"):
        io.open(os.path.join(out_dir, "feed.xml"), "w", encoding="utf-8").write(build_feed(cfg, d))

    print("Website written : %s" % out_dir)


if __name__ == "__main__":
    main()
