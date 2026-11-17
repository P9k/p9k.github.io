# CV-Sync (Obsidian → GitHub → Overleaf) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The list sections of Paul's hand-made moderncv CV are generated from the Obsidian vault into `generated/*.tex`, the CV lives in a private GitHub repo `P9k/cv`, and Overleaf pulls it via GitHub sync.

**Architecture:** A new focused module `_build/cv_moderncv.py` (website repo) turns the already-collected vault data (`collect(cfg)` → `Data`) into moderncv snippets. `build.py` gets `--cv-out DIR` and `--cv-only`. The CV folder `OneDrive - Hereon/cv` becomes a git repo whose `CV.tex` keeps all hand-written parts and `\input`s the generated files; `cv-sync.sh` (run in WSL) regenerates, commits and pushes.

**Tech Stack:** Python 3 + PyYAML (existing generator), `unittest` (no new dependency), XeLaTeX + moderncv (casual, blue), git via WSL.

**Spec:** `docs/superpowers/specs/2026-11-17-cv-overleaf-sync-design.md`

## Global Constraints
- Layout, colours, fonts and section titles of `CV.tex` stay exactly as they are.
- Address, phone, date of birth, child never enter the public website repo or the website output.
- `git push` only via WSL (`wsl.exe -e bash -lc '…'`), never Git Bash/PowerShell.
- The GitHub repo is created by Paul in the browser (no `gh` CLI installed); Overleaf import is done by Paul.
- Generated files are UTF-8, compiled with XeLaTeX (Unicode like ü, —, “ ” may stay literal).
- Python run on Windows with `C:\Python314\python`; in WSL with `python3`.

## Review Focus
1. Text with LaTeX specials (`&`, `%`, `_`, `#`) — e.g. talk title “Experiment & Theory” — must compile: escape via existing `tex_escape`.
2. Online talks without city/country (IEA Web Meeting) — place column shows `online`, never a dangling comma.
3. Funding without `amount_eur` or `duration` — empty argument, no “0 EUR”.
4. Papers missing `volume` or `pages` — field omitted, no `\textit{}` or double commas.
5. `public: false` notes and non-`Published` papers — never appear in any generated file.

---

### Task 1: moderncv formatters

**Files:**
- Create: `_build/cv_moderncv.py`
- Test: `_build/tests/test_cv_moderncv.py`

**Interfaces:**
- Consumes from `build.py`: `S`, `I`, `L`, `tex_escape`, `highlight_authors_tex`, `month_year`, `is_public` (import `build` as module; tests put `_build` on `sys.path`).
- Produces (all return a `str` of LaTeX lines, `""` if no rows):
  - `funding_tex(notes) -> str`
  - `conference_org_tex(service_notes) -> str`
  - `invited_talks_tex(talks) -> str`
  - `contributed_talks_tex(talks) -> str`
  - `seminars_tex(talks) -> str`
  - `reviewing_tex(service_notes) -> str`
  - `metrics_tex(profile) -> str`
  - `publications_tex(papers, highlight_pattern) -> str`
  - `render_all(d, cfg) -> dict[str, str]` mapping file names `funding.tex`, `conference-organization.tex`, `invited-talks.tex`, `contributed-talks.tex`, `seminars.tex`, `reviewing.tex`, `metrics.tex`, `publications.tex` to content; each content starts with `% generated from the Obsidian vault by build.py -- do not edit\n`.

Formats (copy exactly; `{x}` = `tex_escape`d value):
- Funding (sorted by `year` desc): `\cventry{YEAR}{PROGRAMME}{FUNDER}{AMOUNT}{DURATION}{ROLE: ``TITLE''}` — AMOUNT = `1,500,000~EUR` (thousands with comma) or empty; last arg is just ``` ``TITLE'' ``` if no role.
- Conference org (year desc, then title): `\cventry{YEAR}{NAME}{}{LOCATION, COUNTRY}{}{ROLE}`; NAME = `cv_name` or `title`.
- Invited talks = category `Invited Talk`; contributed = `Contributed Talk` or `Poster`; both: `\cventry{YEAR}{NAME}{}{CITY, COUNTRY}{}{Talk|Poster}`; NAME = `cv_name` or `occasion_name`; last arg `Poster` if `format == Poster` or category `Poster`, else `Talk`. Sort year, month, day desc.
- Seminars = `Invited Seminar` (label `Seminar`) or `Workshop Lecture` (label `Workshop lecturer`): `\cventry{Mon YYYY}{LABEL}{NAME}{CITY, COUNTRY}{}{}` using `month_year(year, month)`.
- Place string: `", ".join` of non-empty city/country; if empty and venue/city contains “online” → `online`.
- Reviewing: one `\cvlistitem{\textit{JOURNAL}}` per entry of `journals` in the note with category `Reviewing`.
- Metrics: `\cventry{Total Citations}{C1 (Google Scholar) / C2 (Scopus)}{}{}{}{}` and `\cventry{h-index}{H1 (Google Scholar) / H2 (Scopus)}{}{}{}{}` from `citations_scholar`, `citations_scopus`, `hindex_scholar`, `hindex_scopus`.
- Publications (input already filtered/sorted newest first by `collect`): numbered N…1, `\cvitem{\textit{N}}{``TITLE'': AUTHORS, \textit{JOURNAL}, \textbf{YEAR}, \textit{VOLUME}, PAGES.}` with `highlight_authors_tex(authors, pattern)`; omit `\textit{VOLUME}, ` / `PAGES` when empty.

- [ ] **Step 1: Write failing tests** in `_build/tests/test_cv_moderncv.py` (`unittest`), notes as plain dicts:
  - `test_funding_row`: `{"year":2024,"programme":"Federal Funding","funder":"BMBF (Germany)","amount_eur":1500000,"duration":"3 years","role":"Principal Investigator","title":"Sustainable TiFe"}` → contains `\cventry{2024}{Federal Funding}{BMBF (Germany)}{1,500,000~EUR}{3 years}{Principal Investigator: ``Sustainable TiFe''}`
  - `test_funding_without_amount`: amount missing → `}{}{3 years}`
  - `test_invited_talk_uses_cv_name`: `cv_name:"AMN11"`, city Christchurch, country New Zealand → `\cventry{2025}{AMN11}{}{Christchurch, New Zealand}{}{Talk}`
  - `test_poster_in_contributed`: category Poster → ends `{}{Poster}` and appears in `contributed_talks_tex`, not in `invited_talks_tex`
  - `test_seminar_month`: year 2025, month 2, category Invited Seminar, occasion_name `University of Waikato`, Hamilton/New Zealand → `\cventry{Feb 2025}{Seminar}{University of Waikato}{Hamilton, New Zealand}{}{}`
  - `test_online_place`: no city/country, venue `online` → `{online}`
  - `test_ampersand_escaped`: occasion_name `A & B` → contains `A \& B`
  - `test_private_excluded`: `public: False` talk → not in output
  - `test_publication_numbering_and_missing_volume`: two papers → first line starts `\cvitem{\textit{2}}`; paper without volume has no `\textit{}`
  - `test_conference_org_chair`: `{"title":"DPG Spring Meeting 2026","category":"Conference organization","location":"Dresden","country":"Germany","year":2026,"role":"Session chair"}` → `\cventry{2026}{DPG Spring Meeting 2026}{}{Dresden, Germany}{}{Session chair}`
- [ ] **Step 2: Run** `C:\Python314\python -m unittest discover -s _build/tests -v` → FAIL (module missing).
- [ ] **Step 3: Implement** the functions above in `_build/cv_moderncv.py`.
- [ ] **Step 4: Run** the same command → all PASS.
- [ ] **Step 5: Commit** `feat(cv): moderncv list formatters` (website repo branch).

### Task 2: build.py CLI `--cv-out` / `--cv-only`

**Files:**
- Modify: `_build/build.py` (`main()` ~L2216)
- Test: `_build/tests/test_cv_moderncv.py`

**Interfaces:**
- Consumes: `render_all(d, cfg)` from Task 1.
- Produces: `write_cv_moderncv(d, cfg, out_dir) -> int` (writes `out_dir/generated/*.tex`, creates folder, returns file count) in `cv_moderncv.py`; CLI flags `--cv-out DIR` (also write moderncv files) and `--cv-only` (with `--cv-out`: skip all website output, only collect + write CV files).

- [ ] **Step 1: Test** `test_write_creates_files`: `write_cv_moderncv` on a minimal fake `Data` (attributes `funding, service, talks, publications, profile` = empty lists/dict) into a `tempfile.TemporaryDirectory()` → 8 files exist in `generated/`, each starting with the header comment.
- [ ] **Step 2: Run** tests → FAIL.
- [ ] **Step 3: Implement** `write_cv_moderncv`; in `main()` add the two flags; with `--cv-only` return right after `collect` + `write_cv_moderncv` (print `CV files written : N → DIR`).
- [ ] **Step 4: Verify** tests PASS, and a real run
  `C:\Python314\python _build/build.py --vault C:/Users/jerabek/Obsidian/Main-Vault --cv-only --cv-out <scratchpad>/cvtest`
  prints 8 files; `generated/invited-talks.tex` contains `German-New Zealand WTZ Meeting`; website repo `git status` unchanged.
- [ ] **Step 5: Commit** `feat(cv): --cv-out/--cv-only`; fast-forward `main` in the main checkout (`git -C <main> merge --ff-only <branch>`); no push yet.

### Task 3: Short CV names in the vault

**Files:**
- Modify (vault, `20-Arbeit/Vorträge/Vortragssammlung`): add `cv_name:` to the talks the old CV abbreviated — AMN10 → `AMN10`, AMN11 → `AMN11`, CMMSE-2016/2018 → `CMMSE-2016`/`CMMSE-2018`, REHE-12 → `REHE-2017`, NZIC-16 → `NZIC-16`, ISTCP IX → `ISTCP 2016`, WATOC-11 → `WATOC 2017`, Humboldt Kolleg → `Humboldt Kolleg 2017`, MH 2024 → `International Symposium of Metal-Hydrogen Systems`.
- Modify: `90-Meta/Templates/Website - Vortrag.md` and `Website - Service.md` — add empty `cv_name:` line.

- [ ] **Step 1:** Add the fields (insert after `occasion_name:`; keep YAML valid — quote values with `:`).
- [ ] **Step 2: Verify** every edited note parses with `yaml.safe_load` and rerun the Task-2 command: `invited-talks.tex` shows `{AMN11}` and `{CMMSE-2018}`.

### Task 4: CV repo and CV.tex wiring

**Files (folder `C:\Users\jerabek\OneDrive - Hereon\cv`):**
- Create: `.gitignore` (`*.aux *.log *.out *.synctex.gz *.fdb_latexmk *.fls missfont.log`, plus `/Lebenslauf/ /marsden/ /*.pdf !/CV.pdf`… keep only `CV.pdf` tracked), `fonts/` (copy the 8 Minion/Myriad Pro `.otf` from `%LOCALAPPDATA%\Microsoft\Windows\Fonts`), `cv-sync.sh`, `README.md` (3-line workflow).
- Modify: `CV.tex` — `\setmainfont{MinionPro-Regular.otf}[Path=./fonts/, …]` and same for sans; replace bodies of sections External Funding, Conference Organization, Invited Talks, Contributed Talks/Posters, Seminars and Workshops, Reviewing Activities, Citation Metrics, Peer-reviewed Journal Articles with `\input{generated/<file>}` (section headers stay in `CV.tex`). Keep a backup `CV.tex.pre-sync` (gitignored).
- `cv-sync.sh` (bash, run in WSL): `python3 "<website>/_build/build.py" --cv-only --cv-out "$(dirname "$0")"` → `git add generated` → commit `Sync CV lists from vault YYYY-MM-DD` if changes → `git push`.

- [ ] **Step 1:** `git init -b main`, add files, generate once (Task-2 command with `--cv-out` = this folder).
- [ ] **Step 2: Verify compile:** `xelatex -interaction=nonstopmode CV.tex` exits 0, no `! ` errors in log; `pdftotext CV.pdf` shows sections in the original order and contains `DPG Spring Meeting 2026`, `Curtin University`, 70 numbered articles.
- [ ] **Step 3: Visual check:** render page 1 and the talks page of old vs new PDF (`pdftoppm -r 60`) and compare — same fonts, colours, column layout.
- [ ] **Step 4: Commit** `Initial CV repo with generated lists` (in the cv repo).

### Task 5: GitHub + Overleaf hand-over

- [ ] **Step 1 (Paul):** create empty **private** repo `P9k/cv` at github.com/new (no README).
- [ ] **Step 2:** `git remote add origin git@github.com:P9k/cv.git`; push via WSL: `wsl.exe -e bash -lc 'cd "/mnt/c/Users/jerabek/OneDrive - Hereon/cv" && git push -u origin main'`. Verify `git status -sb` shows `main...origin/main`.
- [ ] **Step 3 (Paul):** Overleaf → New project → Import from GitHub → `P9k/cv`; set compiler to XeLaTeX, main document `CV.tex`; compile.
- [ ] **Step 4:** Smoke test of the loop: run `cv-sync.sh` via WSL after a trivial vault change (none needed if nothing changed → script prints “nothing to sync”).
