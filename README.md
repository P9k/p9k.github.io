# Persönliche Website — Generator

Diese Website wird vollständig aus den YAML-Headern der Notizen in der Obsidian-Vault
erzeugt. Es gibt keine Datenbank und keine zweite Pflegequelle: Was in der Vault steht,
steht auf der Website und im CV.

---

## Website aktualisieren

```bash
cd ~/Nextcloud/web/website
./update.sh
```

Immer auf **deinem Rechner** ausführen (dort liegen die Vault und LaTeX), nicht
irgendwo anders — der Pfad zur Vault in `_build/config.yaml` ist lokal.

**Was dabei passiert**, der Reihe nach:

1. Liest alle Notizen mit `type: paper`, `talk`, `project`, `funding`, `teaching`,
   `position`, `education`, `service`, `research-thread`, `news` sowie `CV-Profil.md`
   aus der Vault (Pfade stehen unter `sources:` in `_build/config.yaml`).
2. Kopiert das Projektbild jeder Projektnotiz (siehe Abschnitt „Projekt“ unten) nach
   `assets/img/projects/`.
3. Setzt den CV aus denselben Daten als LaTeX und kompiliert ihn mit `pdflatex` zu
   `cv.pdf` — nur wenn `pdflatex` installiert ist, siehe unten.
4. Schreibt alle sechs HTML-Seiten neu.
5. Kopiert `style.css`, `site.js` und das Profilfoto nach `assets/`.
6. Schreibt `publications.bib`, `sitemap.xml`, `feed.xml` und die JSON-Dateien in `data/`.

Alles landet direkt in diesem Ordner (`website/`) und überschreibt die vorherige
Fassung. Zum Veröffentlichen danach `./publish.sh` statt `./update.sh` — das baut
genauso neu und pusht anschließend zu GitHub Pages (siehe „Veröffentlichen über
GitHub Pages" unten). Wer stattdessen klassisch synchronisiert, schließt den
Unterordner `_build/` aus (siehe dort).

Einmalige Voraussetzungen:

```bash
pip install --user pyyaml
```

Für den PDF-Download des CV zusätzlich eine LaTeX-Installation, z. B.:

```bash
sudo apt install texlive-latex-base texlive-latex-extra texlive-fonts-recommended
```

Ohne das läuft der Build trotzdem durch — nur `cv.pdf` fehlt dann, und die Seite
zeigt den Download-Link gar nicht erst an (`cv.html` bleibt über den Browser-Druck
weiterhin als PDF speicherbar, siehe „CV erzeugen“ unten).

Mehr Ausgabe beim Bauen: `python3 _build/build.py --verbose`

---

## Von mehreren Rechnern bauen

Liegt die Vault nicht auf jedem Rechner am selben Pfad (anderer Nutzername,
anderer Sync-Ordner, …), gibt es drei gleichwertige Wege — von „einmal
einrichten, nie wieder dran denken“ bis „einmaliger Sonderfall“:

**1. Liste in `_build/config.yaml` (empfohlen für Rechner, die du öfter benutzt).**
`vault:` darf statt einem einzelnen Pfad eine Liste sein; der Generator probiert
sie der Reihe nach durch und nimmt den ersten Pfad, den es wirklich gibt:

```yaml
vault:
  - "/home/paul/Obsidian/Main-Vault"
  - "/Users/paul/Obsidian/Main-Vault"
  - "/mnt/c/Users/paul/Obsidian/Main-Vault"
```

Einmal eingetragen, läuft `./update.sh` bzw. `./publish.sh` auf jedem dieser
Rechner unverändert.

**2. Umgebungsvariable `WEBSITE_VAULT_PATH`** — praktisch, wenn du sie einmal in
dein Shell-Profil (`.bashrc`/`.zshrc`) einträgst und `config.yaml` unangetastet
lassen willst:

```bash
export WEBSITE_VAULT_PATH="$HOME/Obsidian/Main-Vault"
```

**3. `--vault` als Kommandozeilen-Argument**, für den einmaligen Sonderfall:

```bash
./update.sh --vault /pfad/zur/vault
```

Reihenfolge, falls mehrere gleichzeitig gesetzt sind: `--vault` schlägt die
Umgebungsvariable, die schlägt die Liste in `config.yaml`. Passt gar nichts,
listet die Fehlermeldung alle durchprobierten Pfade auf.

---

## Veröffentlichen über GitHub Pages

Der Ordner `website/` ist ein Git-Repository und wird komplett hochgeladen —
Generator (`_build/`) und fertige Seiten zusammen. `_build/config.yaml` enthält
nur einen lokalen Dateipfad zur Vault, keine Inhalte, das ist unkritisch. GitHub
Pages ignoriert Ordner, die mit `_` beginnen (Standardverhalten, ganz ohne
Zutun), `_build/` ist auf der veröffentlichten Seite also gar nicht erst
erreichbar — im Repository selbst bleibt er trotzdem sichtbar, das ist normal
und gewollt (so bleibt der Generator versioniert).

**Einmalige Einrichtung**, im Ordner `website/` (Repo ist schon initialisiert
und alle Dateien sind schon gestaged):

```bash
# 1. Commit-Identität setzen (nur für dieses Repo; deine E-Mail steht bei
#    einem öffentlichen Repo im Commit-Verlauf öffentlich sichtbar — nimm
#    z. B. deine GitHub-"noreply"-Adresse aus den GitHub-Einstellungen unter
#    Settings → Emails → "Keep my email address private", falls du das lieber
#    privat hältst).
git config user.name  "Dein Name"
git config user.email "deine@email"
git commit -m "Initial website"

# 2. Leeres Repository auf github.com anlegen (New repository → OHNE README,
#    .gitignore oder Lizenz ankreuzen, sonst gibt es einen Konflikt beim Push).
#    Name frei wählbar, z. B. "academic-website" oder — für eine Seite direkt
#    unter https://<username>.github.io/ ohne Unterordner — "<username>.github.io".

# 3. Verbinden und hochladen (Repo-URL von GitHub kopieren):
git branch -M main
git remote add origin git@github.com:<username>/<reponame>.git
git push -u origin main
```

**Pages aktivieren:** im Repo auf GitHub → *Settings* → *Pages* → unter
*Build and deployment* → *Source*: „Deploy from a branch“ → *Branch*: `main`,
Ordner `/ (root)` → *Save*. Nach ein bis zwei Minuten ist die Seite live unter
`https://<username>.github.io/<reponame>/` (bzw. `https://<username>.github.io/`
bei einem `<username>.github.io`-Repo).

**Danach `site.url` korrigieren**, damit `sitemap.xml`/`feed.xml` die richtige
Adresse enthalten — in `_build/config.yaml` den Platzhalter `https://example.org`
durch die echte Pages-URL ersetzen, dann einmal neu veröffentlichen (siehe
unten).

**Ab jetzt reicht für jede Aktualisierung:**

```bash
cd ~/Nextcloud/web/website
./publish.sh
```

Das baut die Seite neu (wie `./update.sh`) und pusht sie anschließend —
committet nur, wenn sich wirklich etwas geändert hat. Wer stattdessen (auch)
weiterhin auf den Hereon-Webspace synchronisieren will, kann das unverändert
zusätzlich per `rsync --exclude _build/ ...` tun (siehe unten) — beides
schließt sich nicht aus.

Öffentlich oder privat ist eine reine Geschmacksfrage: GitHub Pages funktioniert
mit privaten Repos genauso (Einstellung beim Anlegen des Repos), nur eine
eigene Domain per `CNAME`-Datei ist dann auf kostenlosen Accounts nicht
möglich.

---

## Aufbau des Ordners

```
website/
├── update.sh                 Startet den Build
├── _build/                   Nie mit hochladen — siehe unten
│   ├── build.py              Der Generator (reines Python + PyYAML)
│   ├── config.yaml           Pfade, Navigation, Optionen
│   ├── title-breaks.yaml     Optionale Umbruch-Hinweise für lange CV-Titel
│   ├── templates/base.html   HTML-Grundgerüst aller Seiten
│   ├── assets/               style.css und site.js (werden kopiert)
│   └── generated/            cv.tex + pdflatex-Nebendateien (Build-Zwischenstand)
│
├── index.html                ← ab hier alles generiert
├── publications.html
├── projects.html
├── talks.html
├── teaching.html
├── cv.html                   Druckfertig: Strg+P → als PDF speichern
├── cv.pdf                    Von pdflatex erzeugt (nur wenn installiert)
├── cv.md                     Reines Markdown, in Python erzeugt (immer)
├── contact.html               Kontaktlinks + Impressum (siehe unten)
├── publications.bib          Komplette Publikationsliste als BibTeX
├── sitemap.xml, feed.xml
├── assets/                   style.css, site.js, img/profile.jpg, img/projects/*
└── data/                     Alle Daten als JSON (zur Weiterverwendung)
```

**Nie direkt bearbeiten:** alle Dateien außerhalb von `_build/` werden bei jedem Build
überschrieben. Änderungen gehören in die Vault, in `_build/config.yaml`,
in `_build/assets/style.css` oder in `_build/templates/base.html`.

**`_build/` gehört nicht auf einen klassischen Webserver.** Er enthält den
Generator selbst und, unter `_build/generated/`, die LaTeX-Quelle des CV —
genau deshalb liegt sie dort und nicht im Website-Ordner: so wird sie nie
versehentlich mit hochgeladen und als Datei zum Download angeboten. Wer per
rsync auf einen eigenen Webspace synchronisiert, schließt `_build/` einmalig
aus, z. B. `rsync -av --exclude _build/ ./ user@server:public_html/`.

Bei **GitHub Pages** (siehe oben) ist das kein Problem: `_build/` darf im
Repository bleiben, GitHub blendet Ordner mit führendem `_` auf der
veröffentlichten Seite automatisch aus.

---

## Woher die Daten kommen

| Inhalt | `type:` | Ordner in der Vault |
|---|---|---|
| Publikationen | `paper` | `20-Arbeit/Paper/Paper` |
| Vorträge, Poster, Seminare | `talk` | `20-Arbeit/Vorträge/Vortragssammlung` |
| Projekte | `project` | `20-Arbeit/Projekte/_Projekte` |
| Förderungen, Stipendien | `funding` | `20-Arbeit/Organisation/Karriere/Förderungen` |
| Lehre | `teaching` | `20-Arbeit/Lehre` |
| Beruflicher Werdegang | `position` | `20-Arbeit/Organisation/Karriere/Stationen` |
| Ausbildung | `education` | `20-Arbeit/Organisation/Karriere/Ausbildung` |
| Gremien, Reviewing, Outreach | `service` | `20-Arbeit/Organisation/Karriere/Service` |
| Forschungsschwerpunkte (3 Kacheln) | `research-thread` | `20-Arbeit/Organisation/Karriere/Forschung` |
| Meldungen auf der Startseite | `news` | `20-Arbeit/Organisation/Karriere/News` |
| Stammdaten, Kontakt, Kennzahlen | `cv-profile` | `20-Arbeit/Organisation/Karriere/CV-Profil.md` |

Diese Pfade stehen in `_build/config.yaml` unter `sources:` und können dort geändert werden.

### Was veröffentlicht wird

* **Publikationen:** nur Notizen mit `status: Published`. Entwürfe, Ideen und
  eingereichte Manuskripte bleiben automatisch draußen.
* **Alles andere:** alles, was nicht ausdrücklich `public: false` gesetzt hat.

`public: false` in einer beliebigen Notiz nimmt sie von der Website (und aus dem CV).

### Was nicht veröffentlicht wird

Notizen enthalten oft Internes. Der Generator gibt deshalb **nie den kompletten
Fließtext einer Notiz** aus, außer bei Werdegang, Mentoring und Outreach — dort ist
der Text bewusst kurz und kuratiert. Bei Lehrnotizen wird ausschließlich das Feld
`summary:` veröffentlicht.

Interne Obsidian-Tags wie `Forschung` oder `Side` werden aus den Themen-Etiketten
herausgefiltert; die Liste steht als `topic_blocklist:` in `_build/config.yaml`.

---

## Eine neue Notiz anlegen

### Publikation

Die vorhandenen Notizen in `20-Arbeit/Paper/Paper` und das Template
`90-Meta/Templates/Paper - New Manuscript.md` bleiben unverändert nutzbar.
Für die Website zählen:

```yaml
type: paper
publication: Titel des Artikels
firstauthor: Nachname
authors: E. Alvares, T. Klassen, P. Jerabek, C. Pistidda
journal: Scr. Mater.
volume: 259
pages: 116516
doi: 10.1016/j.scriptamat.2024.116516
pubyear: 2025
runningnumber: 62          # bestimmt die Reihenfolge innerhalb eines Jahres
topics: Thermodynamics, TiFe
openaccess: true           # zeigt das Open-Access-Etikett
status: Published          # nur das erscheint auf der Website
```

Die Autorenliste wird an `P. Jerabek` automatisch fett gesetzt
(Muster: `highlight_author` in der Konfiguration).

### Vortrag, Poster, Seminar, Workshop

```yaml
type: talk
title: Seminar: University of Waikato
year: 2025
month: "02"
day: "01"
occasion_type: Seminar          # Conference | Seminar | Workshop | Webinar
occasion_name: University of Waikato
category: Invited Seminar       # steuert die Gruppierung, siehe unten
format: Talk                    # Talk | Poster | Lecture
country: New Zealand
city: Hamilton
venue: University of Waikato
public: true
url:                            # optional, verlinkt den Eintrag
slides:                         # optional
```

`category` bestimmt, unter welcher Überschrift der Eintrag erscheint:
`Invited Talk`, `Contributed Talk`, `Poster`, `Invited Seminar`, `Workshop Lecture`.
Alles andere landet unter „Other contributions“.

### Projekt

Bestehende Projektnotizen wurden um einen Block für die Website ergänzt:

```yaml
# --- website / CV fields ---
acronym: GreenH2Metals
short: Einzeiler, der auf der Website unter dem Titel steht.
role: Principal Investigator
funder: BMBF (Germany)
programme: Federal funding
grant_number: 03SF0691
amount_eur: 1500000        # reine Zahl, wird als 1.5 M€ formatiert
image:                     # optional, siehe unten
url:
public: true
```

Laufzeit und Status kommen aus den vorhandenen Feldern `startingdate`, `enddate`
und `active`. `active: true` sortiert das Projekt unter „Current projects“.

**Bild hinzufügen:** Trage im Feld `image:` einen Bildpfad ein. Drei Varianten:

```yaml
image: 90-Meta/Anhänge/banner/scrap-metal.jpg   # Pfad relativ zur Vault-Wurzel
image: scrap-metal.jpg                          # bloßer Dateiname
image: "![[scrap-metal.jpg]]"                   # per Obsidian eingefügter Anhang
```

Ein bloßer Dateiname wird automatisch in `90-Meta/Anhänge/banner/` und
`90-Meta/Anhänge/` gesucht (Liste unter `image_search_dirs:` in `_build/config.yaml`,
dort erweiterbar). Auch eine externe Bild-URL (`https://…`) ist möglich, dann wird
nichts kopiert, sondern direkt verlinkt.

**Ohne etwas zu tun:** Die sieben bestehenden Projektnotizen haben durch das
Obsidian-Banner-Plugin bereits ein `banner:`-Feld. Ist kein `image:` gesetzt, greift
der Generator automatisch darauf zurück — die vorhandenen Banner erscheinen also
ohne weiteres Zutun als Projektbilder auf der Website.

Beim nächsten `./update.sh` wird das Bild nach `assets/img/projects/<projekt>.jpg`
kopiert und oben auf der Projektkarte angezeigt (Format 16:9, zugeschnitten). Ein
Projekt ohne Bild und ohne Banner zeigt einfach keins — nichts bricht.

### Förderung

```yaml
type: funding
title: Sustainable TiFe Generation from Secondary Sources
funder: BMBF (Germany)
programme: Federal funding
category: Research grant
role: Principal Investigator
amount_eur: 1500000
grant_number:
startdate: 2024-04-01
enddate: 2027-03-31
duration: 3 years
year: 2024                 # Jahr der Bewilligung, sortiert die Liste
project: GreenH2Metals     # optionaler Verweis auf die Projektnotiz
```

### Lehre

```yaml
type: teaching
title: 2025 SoSe TUHH H2-Technik     # interner Notiztitel
course: Hydrogen Technology         # das erscheint auf der Website
institution: Technische Universität Hamburg (TUHH)
location: Hamburg
role: Co-lecturer          # Lecturer | Co-lecturer | Workshop lecturer | Tutor …
level: MSc
term: 2025 SoSe            # falls gesetzt, steht das links statt der Jahreszahl
year_start: 2025
year_end: 2025
language: English
summary: Ein bis zwei Sätze — nur dieses Feld wird veröffentlicht.
```

**Wichtig:** Vom Fließtext einer Lehrnotiz erscheint *nichts* auf der Website. Nur
`summary:` wird ausgegeben. Ablaufpläne, Teilnehmerfeedback und interne Notizen
bleiben damit privat, auch wenn sie in derselben Notiz stehen.

### Meldung auf der Startseite

Der „News“-Block auf der Startseite (`front_news:` in `_build/config.yaml`
begrenzt ihn auf die letzten vier Einträge) kommt aus zwei Quellen, gemeinsam nach
Datum sortiert:

1. **Eigene Meldungen** — Notizen mit `type: news`:

   ```yaml
   type: news
   title: HyCycleMat proposal submitted
   date: 2026-06-15
   url:
   ```

   Der Text der Meldung ist der Fließtext unter dem Header. Ohne `date:` wird das
   Erstellungsdatum der Notiz (`created:`) verwendet.

2. **Automatisch aus Publikationen** — die sechs neuesten Einträge aus
   `20-Arbeit/Paper/Paper` mit `status: Published` erzeugen von selbst je eine Zeile
   „New paper in *Journal*: Titel“, einsortiert zum 1. Januar ihres Erscheinungsjahrs.
   Dafür ist nichts zu pflegen — sobald eine Publikationsnotiz auf `Published` steht,
   taucht sie hier auf.

Für eine Meldung, die nicht mit einer Publikation zusammenhängt (ein Vortrag, eine
neue Förderung, ein Meilenstein), reicht also eine kurze `news`-Notiz.

---

## Stammdaten: `CV-Profil.md`

Diese eine Notiz steuert Name, Position, Kontakt, Links, Kennzahlen, Sprachen und
Methodenkompetenzen. Leere Felder werden stillschweigend weggelassen — ein leeres
`orcid:` heißt also einfach: kein ORCID-Link auf der Seite.

Der Fließtext der Notiz ist in Abschnitte gegliedert, die der Generator einzeln
ausliest:

* `## bio` — der lange Absatz auf der Startseite
* `## bio_short` — Kurzfassung (derzeit als Reserve, z. B. für Metadaten)
* `## research_intro` — der Satz über den drei Forschungskacheln

Die Kennzahlen (`citations_scholar`, `hindex_scholar`, `metrics_asof`) sind von Hand
gepflegt; sie erscheinen als Zeile über der Publikationsliste. `metrics_asof` wird
mit ausgegeben, damit klar ist, wie alt der Stand ist.

Die Kontakt-/Link-Felder (`email`, `orcid`, `scholar`, `researchgate`, `github`,
`linkedin`, `mastodon`, `hereon_profile`) tauchen automatisch überall dort auf, wo
sie hingehören — Startseite, `cv.html` und `contact.html` —, sobald sie ausgefüllt
sind; leer heißt weiterhin einfach „nicht anzeigen“. `email` wird dabei nirgends im
Klartext ins HTML geschrieben (siehe „E-Mail vor Spam schützen“ unten).

---

## E-Mail vor Spam schützen

`email` aus `CV-Profil.md` erscheint auf der Website nie als Klartext im HTML —
der Generator schreibt jedes Zeichen als numerische HTML-Entität
(`&#112;&#97;...`). Browser und Screenreader zeigen ganz normal die lesbare,
klickbare Adresse an, aber simple Scraper, die den rohen Quelltext nach
`name@domain`-Mustern durchsuchen, finden dort keine. Kein JavaScript nötig,
kein Sicherheitsversprechen gegen ausgefeilte Bots — aber genau die Art von
Massen-Harvesting, vor der du dich schützen wolltest, greift damit ins Leere.
Betroffen sind Startseite, `cv.html` und `contact.html`. Nicht betroffen ist
`cv.pdf`: PDF-Text lässt sich immer maschinell auslesen, eine serverseitige
Verschleierung dort bringt nichts.

---

## CV erzeugen

`cv.html` ist die Website-Fassung. Der CV wird **vollautomatisch** aus denselben
Vault-Daten wie der Rest der Seite gebaut (`CV-Profil.md` + Education/Positions/
Funding/Service/Teaching/Talks/Papers-Notizen) — nichts davon wird von Hand
gepflegt. Es gibt drei Ausgabeformen, alle aus genau derselben Datenquelle,
alle bei jedem `./update.sh` neu erzeugt:

**„Download PDF“** verlinkt auf `cv.pdf`, mit `pdflatex` erzeugt (siehe unten).
**„Download Markdown“** verlinkt auf `cv.md` — eine reine Markdown-Fassung, komplett
in Python geschrieben (`build_markdown_cv()` in `_build/build.py`), ohne jede
Zusatzabhängigkeit (kein Pandoc, kein YAMLResume/Node.js). Praktisch für ein
schnelles Copy-Paste in eine Bewerbung, ein Wiki oder einen Chat. Abschalten mit
`markdown_cv: false` unter `options:` in `config.yaml`.
**Browser-Druck** funktioniert unabhängig von beidem immer: Im Browser
**Strg+P → Als PDF speichern**. Das Druck-Stylesheet blendet Navigation, Filter und
Buttons aus, setzt die Schrift auf 10 pt und bricht sauber um.

Beide Download-Links erscheinen auf der Seite nur, wenn das letzte `./update.sh`
die jeweilige Datei auch tatsächlich erzeugen konnte.

*Warum kein YAMLResume?* Das wäre eine zusätzliche Node.js-Toolchain gewesen und
sein Schema kennt von Haus aus keine Talks/Funding/Teaching-Abschnitte — beides
widerspricht dem Grundsatz „ohne große externe Tools“ dieses Projekts. Die
Markdown-Ausgabe deckt denselben Bedarf (portables Klartextformat) ohne diese
Kosten.

### Publikationsliste im PDF/Markdown-CV

Format wie in der Chemie üblich (angelehnt an *Angewandte Chemie*): Autoren
(eigener Name automatisch fett, über `highlight_author` in `config.yaml` —
dieselbe Regel wie auf `publications.html`), Titel, *Journal* **Jahrgang**,
*Band*, Seiten. Kein Umbauen nötig — das folgt automatisch aus `journal:`,
`pubyear:`, `volume:`, `pages:` in der Paper-Notiz.

Lange Titel mit Chemieformeln ohne Leerzeichen (z. B. `[Ni(ZnMe)6(ZnCp*)2]`)
haben für `pdflatex` keine Stelle zum Umbrechen und liefen früher teils über
den Seitenrand hinaus. Dagegen zwei Maßnahmen: Die ganze Publikationsliste
steht in einer `\sloppy`-Gruppe (etwas lockerer Zeilenausgleich statt starrem
Überlauf), und zusätzlich `_build/title-breaks.yaml` — eine optionale,
von Hand gepflegte Datei mit gezielten Umbruch-Hinweisen für einzelne Titel,
ganz ohne LaTeX-Kenntnisse: den Titel (oder das problematische Wort) eintragen,
daneben dieselbe Stelle nochmal mit `|` an jeder Stelle, an der ein Umbruch
in Ordnung wäre. Datei ist auskommentiert und selbsterklärend; leer/fehlend
ändert nichts. Aktuell (Stand dieses Updates) braucht keiner der 70 Titel
einen manuellen Hinweis — die Datei ist als Reserve für zukünftige Titel da.

### Wenn kein PDF erscheint

`./update.sh` meldet dann beim Bauen `cv.pdf : SKIPPED - pdflatex is not installed.`
Nachinstallieren mit:

```bash
sudo apt install texlive-latex-base texlive-latex-extra texlive-fonts-recommended
```

und `./update.sh` erneut ausführen. Bis dahin bleibt der Download-Link auf der Seite
einfach weg, statt auf eine fehlende Datei zu zeigen. `cv.md` ist davon nicht
betroffen — reines Python, kein `pdflatex` nötig, erscheint also immer.

### Die LaTeX-Quelle selbst

Sie liegt nach jedem Build unter `_build/generated/cv.tex` — nicht im Website-Ordner,
damit sie nie versehentlich als Download angeboten wird (siehe „Aufbau des Ordners“).
Zum Nachvollziehen oder Anpassen:

```bash
cd _build/generated
pdflatex cv.tex
```

Sie braucht nur Standardpakete (`geometry`, `hyperref`, `xcolor`, `titlesec`,
`enumitem`, `textcomp`, `newunicodechar`) — bewusst *keine* Sonderklasse wie
`curve.cls` und keine Icon-/Font-Pakete (`fontawesome5`, `simpleicons`,
`cochineal`, …), auch wenn Layout und Kontaktzeile ("Email · ORCID · Scholar · …"
in Blau/Petrol) genau davon inspiriert sind. Der Grund: eine Sonderklasse plus
mehrere Zusatzdateien wäre genau die Art fragiler Abhängigkeit, die schon einmal
zum `eurosym.sty`-Fehler geführt hat — mit reinem `article` + Standardpaketen
kompiliert es garantiert mit einem nackten `pdflatex`. Wenn du lieber deine
bestehende CV-Klasse verwendest: Der Generator schreibt die Abschnitte über das
Makro `\entry{links}{rechts}`, das oben in der Präambel definiert ist — das lässt
sich dort umdefinieren, ohne den Generator anzufassen. Diese Datei wird bei jedem
Build überschrieben; eigene Anpassungen gehören in `build_latex_cv()` (PDF) bzw.
`build_markdown_cv()` (Markdown) in `_build/build.py`, nicht in die generierten
Dateien selbst.

---

## Kontaktseite & Impressum

`contact.html` (Nav-Punkt „contact“) zeigt zwei Dinge:

**Kontakt-Links.** Dieselbe Liste wie im Header der Startseite (E-Mail,
Google Scholar, ORCID, ResearchGate, GitHub, LinkedIn, Hereon-Profil) — einfach
die entsprechenden Felder in `CV-Profil.md` ausfüllen, siehe oben.

**Impressum.** Optional, standardmäßig **ausgeschaltet**. Steuerbar über den
Block `impressum:` in `_build/config.yaml`:

```yaml
impressum:
  enabled: false                  # auf true stellen, wenn die Angaben stimmen
  responsible_name: ""            # leer = Name aus CV-Profil.md
  address_lines:
    - ""
    - ""
  email: ""                       # leer = email aus CV-Profil.md
  phone: ""
  extra: ""                       # freier Text, z. B. USt-ID, Aufsichtsbehörde
```

Lässt du `responsible_name`, `address_lines` und `email` leer, greift automatisch
`CV-Profil.md` (Name, `address_line`, `email`) — dort steht deine Hereon-Adresse
ja bereits drin. Heißt in der Praxis meistens: einfach `enabled: true` setzen und
prüfen, ob dir die übernommenen Angaben genügen, oder eigene Zeilen eintragen,
wenn du z. B. eine private statt der dienstlichen Adresse willst.

**Wichtig, keine Rechtsberatung:** Das ist eine Vorlage, kein geprüfter
Rechtstext. Ob und in welcher Form eine Website ein Impressum braucht und was
genau hineingehört (z. B. Verantwortlicher nach § 18 Abs. 2 MStV, ggf.
USt-ID), hängt vom Einzelfall ab — bei einer Seite, die deine Hereon-Zugehörigkeit
zeigt, lohnt sich kurz Rücksprache mit der Rechts-/Kommunikationsabteilung, bevor
du `enabled: true` setzt.

---

## Aussehen ändern

* **Akzentfarbe, Abstände, Schriftgrößen:** `_build/assets/style.css`, ganz oben im
  Block `:root{ … }`. `--acc` ist die Akzentfarbe (aktuell Petrol `#10635c`), darunter
  steht derselbe Satz Variablen noch zweimal für den Dunkelmodus.
* **Seitengerüst, Meta-Tags, Schriftarten:** `_build/templates/base.html`.
* **Navigation:** `nav:` in `_build/config.yaml`.
* **Hell/Dunkel:** folgt der Systemeinstellung; der Knopf oben rechts überschreibt sie.
  Die Wahl merkt sich der Browser in `localStorage` und gilt dann für alle Seiten.
  Beim Öffnen direkt von der Festplatte (`file://`) bekommt jede Datei vom Browser
  einen eigenen Speicherbereich — dort würde die Einstellung auf jeder Unterseite
  wieder verloren gehen. Deshalb hängt `site.js` in diesem Fall `#theme=dark` an die
  internen Links und räumt die Adresszeile danach wieder auf. Auf dem Webserver
  passiert das nicht, die URLs bleiben sauber.
* **Domain** (für `sitemap.xml` und `feed.xml`): `site.url` in `_build/config.yaml`.

Die Google-Fonts-Einbindung in `base.html` ist die einzige externe Abhängigkeit der
fertigen Seite. Wenn die Seite ganz ohne externe Anfragen auskommen soll: die beiden
`<link>`-Zeilen entfernen — die CSS-Schriftstapel fallen dann auf Systemschriften zurück.

---

## Hintergrund-Animation

Eine dezente, ruhige Animation kann hinter dem Seiteninhalt laufen — gesteuert über
eine einzige Zeile in `_build/config.yaml`:

```yaml
options:
  background_animation: "bands"   # oder "none", um sie auszuschalten
```

Zur Auswahl stehen (alle als eigene Funktion in `_build/assets/bg.js`, dort auch
kommentiert):

| Schlüssel | Motiv |
|---|---|
| `none` | keine Animation |
| `lattice` | Kristallgitter, leicht driftend |
| `contours` | wabernde Konturlinien (Potentialfläche) |
| `orbits` | langsame elliptische Umlaufbahnen |
| `diffusion` | driftende Punkte in blassem Gitter |
| `waves` | weiche wandernde Farbverläufe |
| `wavefunction` | atmende Orbital-Ladungswolken |
| `bands` | Bandstruktur-artige Dispersionskurven *(aktuell aktiv)* |
| `mdtraj` | Atome mit thermischer Zitterbewegung + Bahnspur |
| `interference` | zwei Quellen mit überlagernden Ringwellen |
| `levels` | diskrete Energieniveaus, gelegentlicher Sprung |
| `hopping` | H-Atome springen zwischen Zwischengitterplätzen |
| `front` | fortschreitende Diffusionsfront |
| `phase` | wachsende/verblassende Keime (Phasenübergang) |
| `tank` | rhythmisches Be-/Entladen eines Behälters |
| `dissociation` | H₂-Molekül dissoziiert an einer Oberfläche |

Einfach den Schlüssel ändern und `./update.sh` (bzw. `./publish.sh`) laufen lassen —
sonst muss nichts angepasst werden, `bg.js` wird unverändert mit ausgeliefert und liest
die Auswahl zur Laufzeit aus `<body data-bg="…">`.

Technisch: reines `<canvas>`, folgt automatisch der Akzentfarbe (hell/dunkel), pausiert
im Hintergrundtab, respektiert `prefers-reduced-motion` (dann läuft gar nichts), hat
`pointer-events:none` und liegt hinter dem gesamten Inhalt. Im Druck-Stylesheet
(`cv.html` → PDF) ist sie ohnehin ausgeblendet.

---

## Regelmäßig prüfen

Einmal im Jahr lohnt ein Blick auf:

* `CV-Profil.md` → Kennzahlen und `metrics_asof`
* Projekte, deren `enddate` vorbei ist → `active: false` setzen
* `site.url` in der Konfiguration, sobald die endgültige Domain feststeht

---

## Fehlersuche

| Symptom | Ursache |
|---|---|
| `Vault not found. Tried: ...` | Keiner der Pfade existiert auf diesem Rechner — Liste unter `vault:` in `_build/config.yaml` ergänzen, `WEBSITE_VAULT_PATH` setzen oder `--vault` übergeben, siehe „Von mehreren Rechnern bauen“ |
| `PyYAML is missing` | `pip install --user pyyaml` |
| Eintrag fehlt auf der Website | `public: false`, oder bei Papers `status:` ist nicht `Published`, oder die Notiz liegt in einem Unterordner, der mit `_` beginnt |
| Eintrag steht in der falschen Gruppe | `category:` in der Notiz prüfen |
| Datum wird nicht angezeigt | Datumsfelder brauchen das Format `JJJJ-MM-TT` |
| Kaputte YAML-Header | Der Generator fängt Parser-Fehler ab und liest den Header zeilenweise — das Ergebnis kann dann aber unvollständig sein. `--verbose` zeigt, was geladen wurde |
| Projektbild erscheint nicht | Pfad in `image:` (oder `banner:`) prüfen — er ist relativ zur Vault-Wurzel, nicht zur Notiz. `--verbose` zeigt unter „project images“, wie viele gefunden wurden |
| `cv.pdf` fehlt, Link auf der CV-Seite auch | `pdflatex` ist nicht installiert, siehe „CV erzeugen“. Die Konsolenausgabe von `./update.sh` sagt es explizit |
| `pdflatex` meldet einen Fehler | Die ersten Fehlerzeilen stehen in der Konsole, das volle Protokoll in `_build/generated/cv.log`. Meist ein Sonderzeichen, das der Generator noch nicht kennt — kurze Nachricht genügt, das lässt sich in `TEX_UNICODE` in `_build/build.py` ergänzen |
| `! LaTeX Error: File 'eurosym.sty' not found` (ältere Fehlerprotokolle) | Behoben: `build_latex_cv()` nutzt seit September 2026 `\texteuro` aus dem Standardpaket `textcomp` statt `eurosym`, keine zusätzliche `apt install` nötig. Falls der Fehler doch wieder auftaucht: `_build/build.py` ist nicht aktuell, neu vom Repository holen |
| `cv.md` fehlt | `markdown_cv: false` in `_build/config.yaml` — auf `true` setzen. Braucht kein `pdflatex`, sollte also praktisch nie fehlen |
| Kontakt-Link fehlt auf `contact.html`/Startseite | Zugehöriges Feld (`orcid`, `github`, `linkedin`, …) ist in `CV-Profil.md` leer |
| Impressum erscheint nicht auf `contact.html` | `impressum.enabled` steht auf `false` in `_build/config.yaml` — Absicht, siehe „Kontaktseite & Impressum“ |
| Hintergrund-Animation erscheint nicht | Entweder `background_animation: "none"` in `_build/config.yaml`, oder das Betriebssystem/der Browser hat „Bewegung reduzieren“ aktiviert — dann bleibt sie absichtlich aus |
