# CV-Sync: Obsidian → privates GitHub-Repo → Overleaf

Stand: 2026-11-17 · Status: Entwurf zur Freigabe

## Ziel und Warum
Paul pflegt seinen ausführlichen CV (`OneDrive - Hereon/cv/CV.tex`, moderncv „casual“, blau, XeLaTeX,
Minion/Myriad Pro) bisher von Hand. Er ist seit April 2025 nicht aktualisiert, während die Obsidian-Vault
(Quelle der Website) aktuell ist. Ziel: die schnell wachsenden Listen kommen automatisch aus der Vault,
Stil und Layout bleiben exakt, und der CV ist von überall in Overleaf (Premium-Lizenz vorhanden) bearbeit- und
übersetzbar.

## Ziele
- Listen im CV werden aus der Vault erzeugt, im bisherigen moderncv-Markup (`\cventry`, `\cvitem`, `\cvlistitem`).
- Privates GitHub-Repo `P9k/cv` als gemeinsame Quelle; Overleaf-Projekt per GitHub-Sync daran gekoppelt.
- Ein Befehl aktualisiert die erzeugten Dateien und pusht sie (Push nur über WSL).

## Nicht-Ziele / Anti-Ziele
- Kein neues Layout, keine anderen Abschnittsnamen.
- Private Angaben (Adresse, Telefon, Geburtsdatum, Kind) landen nie im öffentlichen Website-Repo.
- Kein automatisches Pullen in Overleaf (Overleaf erlaubt das nur per Knopfdruck).
- `Academic-achievements.tex` und `Publications.tex` vorerst nicht (können später dieselben Dateien einbinden).

## Ansätze (betrachtet)
1. **Overleaf mit GitHub-Sync (gewählt)** – Premium vorhanden; GitHub dient zusätzlich als Backup/Versionierung.
2. Overleaf mit „Datei von URL“ – für den Free-Tarif gedacht; mit Premium unnötig umständlich.
3. Nur lokal bauen – kein Zugriff „von überall“.

## Aufteilung: was wird erzeugt, was bleibt von Hand
**Erzeugt aus der Vault** (je eine Datei in `generated/`, in `CV.tex` per `\input{generated/…}` eingebunden):

| Datei | Abschnitt in CV.tex | Quelle |
|---|---|---|
| `funding.tex` | External Funding | Förderungen (Jahr, Programm, Geldgeber, Betrag, Dauer, Beschreibung) |
| `conference-organization.tex` | Conference Organization | Service, `category: Conference organization` (inkl. DPG-Session-Chairs) |
| `invited-talks.tex` | Invited Talks | Vorträge, `Invited Talk` |
| `contributed-talks.tex` | Contributed Talks/Posters | Vorträge, `Contributed Talk` + `Poster` |
| `seminars.tex` | Seminars and Workshops | Vorträge, `Invited Seminar` + `Workshop Lecture` |
| `reviewing.tex` | Reviewing Activities | `Reviewing.md` → `journals` |
| `metrics.tex` | Citation Metrics | CV-Profil (`citations_*`, `hindex_*`) |
| `publications.tex` | Peer-reviewed Journal Articles | Paper mit `status: Published`, absteigend nummeriert |

**Bleibt handgepflegt in `CV.tex`:** Kopf/Foto/Kontakt, Personal Details, University Education,
Professional Experience & Teaching, Scholarships, Languages, IT-Knowledge, Quantum Chemical Methods,
Engagement and Other Activities. (Ändern sich selten und sind bewusst ausformuliert.)

*Meine Entscheidung (korrigierbar):* Session-Chairs stehen künftig unter „Conference Organization“
statt unter „Invited Talks“ – konsistent mit Website.

## Technik
- `build.py` bekommt eine zusätzliche Ausgabe `cv_moderncv` (Zielordner per `config.yaml`, z. B. der
  lokale Klon des CV-Repos). Format orientiert sich zeilengenau am heutigen `CV.tex`
  (z. B. `\cventry{2025}{AMN11}{}{Christchurch, NZ}{}{Talk}`; Seminare mit Monat „Feb 2025“).
  LaTeX-Escaping für &, %, _, # usw.
- Kurzname im CV: neues optionales Feld `cv_name` in Vortrags-/Service-Notizen (z. B. „AMN11“),
  sonst `occasion_name`.
- Skript `cv-sync.sh` im CV-Repo: Build ausführen → `generated/` committen → `git push` über WSL.
- CV-Repo-Inhalt: `CV.tex`, `fotos/`, `generated/`, `fonts/`, `.gitignore` (aux/log/pdf-Zwischendateien);
  alte PDFs, `Lebenslauf/`, `marsden/` bleiben nur lokal (nicht versioniert).
- Schriften: Minion/Myriad Pro als `.otf` in `fonts/`, `CV.tex` lädt sie mit `Path=./fonts/` –
  Layout bleibt identisch. **Lizenzfrage liegt bei Paul**; Alternative: Crimson Pro + Source Sans 3.
- Overleaf: neues Projekt „aus GitHub importieren“ (macht Paul selbst im Browser, braucht seinen Login).

## Ablauf im Alltag
Vortrag in Obsidian eintragen → `cv-sync.sh` (oder zusammen mit dem Website-Publish) → in Overleaf
„Pull GitHub changes“ → übersetzen. Handtexte in Overleaf ändern → „Push to GitHub“.

## Dem Umsetzer überlassen
Genaue Formatierung von Sonderfällen (fehlender Ort, Online-Termine), Reihenfolge innerhalb eines Jahres,
Abgleich der erzeugten Listen mit dem heutigen PDF (Vorher/Nachher-Vergleich vor dem ersten Push).
