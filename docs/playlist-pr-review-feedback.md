# Playlist-PRs — Review-Feedback (UX / UI / Ästhetik)

Status: Laufendes Review-Dokument  
Basis: [`playlist-generierung-umsetzungsplan.md`](playlist-generierung-umsetzungsplan.md)  
Evaluierung (Ist vor PR1): [`playlists-evaluierung-2026-06-30.md`](playlists-evaluierung-2026-06-30.md)

Dieses Dokument sammelt **manuelles Test-Feedback** zu den Playlist-PRs (PR1–PR5).
Jede PR-Runde bekommt einen eigenen Abschnitt. Neue Erkenntnisse werden dort ergänzt,
nicht in separaten Einzeldateien pro PR.

---

## Test-Setup (Referenz)

| Einstellung | Wert |
|-------------|------|
| Branch PR3 | `cursor/playlist-pr3-export-c980` (enthält PR1 + PR2 + PR3) |
| Frontend | `hatch run frontend` → http://127.0.0.1:5173 |
| API | `hatch run api` → http://127.0.0.1:8000 |
| Daten | `data/reviews.jsonl` muss lokal vorhanden sein (z. B. `./sync_data.sh pull`) |
| Screenshots PR2-Review (Formular) | `frontend/screenshots/review-2026-07-03/` |
| Screenshots PR3-Review (Ergebnis) | `frontend/screenshots/review-2026-07-03-pr3/` |

---

## PR1 — Mobile-Layout & Export-Shell

**Branch:** `cursor/playlist-pr1-layout-c980`  
**Review-Datum:** 2026-07-03

### Umgesetzt (Kurz)

- Einspaltiges Layout; leere „Danach“-Sidebar entfernt
- Export-Hinweis unter dem Button vor der Generierung
- Ergebnisbereich mit `playlist-results-head` und Export-Leiste

### Feedback

| Kategorie | Befund |
|-----------|--------|
| **UX** | Mobile-Überlappung (Formular / Sidebar) ist behoben — Hauptziel erreicht. |
| **UX** | Export-Hinweis unter dem Button ist klarer als die alte leere Sidebar. |
| **UI** | Ergebnis-Export-Buttons oben rechts (Desktop) wirken aufgeräumt. |
| **Regression** | Keine Auswirkung auf Archiv/Neuheiten; leere Empfehlungsseiten lagen an fehlendem `reviews.jsonl` (Umgebung), nicht an PR1. |

### Offen / für spätere PRs

- TuneMyMusic-Anleitung noch dünn → **PR3**
- Ergebnisdarstellung noch schlicht → **PR4**

---

## PR2 — Formular, Modus-Steuerungen & API-Mapping

**Branch:** `cursor/playlist-pr2-form-c980`  
**Review-Datum:** 2026-07-03  
**Screenshots:** `playlist-neuheiten-desktop.png`, `playlist-archiv-desktop.png`, `playlist-neuheiten-mobile.png`, `playlist-archiv-mobile.png` (Ordner oben)

### Gesamteindruck

PR2 ist ein klarer Fortschritt gegenüber dem alten Select-Formular. Modus-Karten,
Chips und Slider passen zum Musikprofil-Wizard. Die Seite wirkt noch wie ein
**Konfigurations-Werkzeug**, nicht wie der emotionale Abschluss von Aktuell/Entdecken.

### Was gut funktioniert

**Struktur & Klarheit**

- Modus-Karten (Neuheiten / Archiv) sind sofort verständlich; aktiver Zustand gut sichtbar.
- Archiv-Pool-Zeile (*„6236 Alben passen … Playlist aus den Top 200“*) gibt endlich Kontext.
- Track-Chips (20 / 30 / 50) mit Hinweis (*„30 Titel — gut zum Reinhören“*) sind freundlich.
- Profil-Zeile *„Basierend auf deinem Musikprofil“* + Link ist sinnvoll platziert.
- Kontextzeile bei Deep-Link (*„Aus deinen Neuheiten · Letzte Update-Runde“*) hilft.

**Mobile**

- Keine Überlappung; Modus-Karten stapeln sauber (PR1-Fix hält).

**Ästhetik**

- Papier-Hintergrund, Serif-Headline, rote Akzente: konsistent mit Plattenradar.
- `generator-card` rahmt das Formular klar, ohne zu schwer zu wirken.

### UX — Auffälligkeiten

| Priorität | Thema | Befund | Vorschlag |
|-----------|-------|--------|-----------|
| P1 | Ungleiches Gewicht Neuheiten vs. Archiv | Neuheiten: Dropdown + 1 Slider. Archiv: Pool-Text, Chips, 2 Slider — deutlich dichter. | Kurze Einordnung unter Moduswahl oder Archiv-Bereich einklappen bis Modus aktiv. |
| P1 | Doppelsteuerung Archiv-Pool | Chips (50 / 200 / Alle) **und** Range-Slider für dieselbe Größe. | Ein führendes Control wählen oder Synchronisation visuell eindeutiger machen (Slider-Position bei Chip „200“ wirkte links — irritierend). **PR3:** Chip „Max.“ bei Pools > 1000 — besser, aber Doppelsteuerung bleibt. |
| P2 | Slider ohne Zwischenwert | Fokus- und Archiv-Tiefen-Slider zeigen nur Endlabels. | Kurzes Zwischenfeedback (z. B. „eher Entdecken“, „mittig“, „stark fokussiert“). |
| P2 | Label „Fokus“ doppelt | Feldüberschrift und rechter Slider-Endpunkt heißen beide „Fokus“. | Feldlabel z. B. „Stimmung“ oder rechten Pol nur als Richtung belassen. |
| P2 | Zeitraum-Dropdown | Native `<select>` neben Cards/Chips stilistisch ein Bruch. | In PR2b oder später: Segment-Control wie bei Track-Anzahl. |
| P2 | Langer Scrollweg (Mobile) | Intro + Profil-Zeile + Kontext + Formular; Archiv noch länger. Button erst nach viel Scroll. | Intro kürzen oder Formular visuell früher starten lassen. |
| P3 | Export-Hinweis | TuneMyMusic-Text klein unter dem Button; Flow vor erster Generierung abstrakt. | **PR3**: nummerierte Anleitung nach Generierung. |

### Ästhetik — Details

| Aspekt | Eindruck |
|--------|----------|
| Hierarchie | Headline und Modus-Karten dominieren. Pool-Summary sehr zurückhaltend (grau/klein) — Schlüsselzahl „6236“ könnte etwas stärker. |
| Rhythmus | Ruhig, gleichmäßig. Archiv wirkt „slider-lastig“. |
| Konsistenz | Choice-Cards/Chips passen zum Profil-Setup; Dropdown und Number-Input bei „Eigene“ wirken älter. |
| Vergleich Aktuell/Entdecken | Dort Highlights, Fotos, narrative Texte. Hier Formular — größter verbleibender Stil-Bruch (für PR4 relevant). |

### Akzeptanzkriterien (Plan) — Review-Stand

- [x] Archiv-Slider-Maximum aus API-`total` (lokal: 6236)
- [x] Nur modus-relevante Felder sichtbar
- [x] Defaults: Update-Runden 1, Tracks 30, Archiv min(200, pool)
- [ ] Visuell: Doppelsteuerung Archiv-Pool noch verwirrend

### Fazit PR2

**Merge-fähig** aus Layout-/Funktionssicht. Vor Produktreife: Archiv-Pool-Controls
vereinfachen und Slider-Feedback verbessern (Quick Wins, auch ohne PR3).

---

## PR3 — Export-Flow & Playlist-Namen

**Branch:** `cursor/playlist-pr3-export-c980`  
**Review-Datum:** 2026-07-03  
**Screenshots:** `playlist-archiv-ergebnis-mobile.png` (Ordner `review-2026-07-03-pr3/`); Formular weiterhin in `review-2026-07-03/`

### Umgesetzt (Kurz)

- Modus-spezifische Default-Namen (`Plattenradar Archiv|Neuheiten YYYY-MM-DD`)
- Remix mit Suffix `(2)`, `(3)`, … über **Nochmal mischen**
- **Als CSV herunterladen** als primäre Aktion (roter Button)
- TuneMyMusic-Anleitung als aufklappbares `<details>` + Freitext-Textarea
- Bugfix: Archiv-Pool auf API-Maximum 1000 gekappt (Chip **Max.**)

### Gesamteindruck

PR3 liefert funktional das Versprochene: Export ist klarer priorisiert, Namen
sind nachvollziehbar, Remix ist praktisch. Visuell bleibt die Seite aber ein
**langes Formular mit angehängter Tabelle** — kein „Fertig, deine Playlist“-Moment.
Der größte UX-Sprung fehlt noch: **Ergebnis und Export fühlen sich nicht wie
Belohnung an**, sondern wie Anhang unter dem gleichen Werkzeug.

### Was gut funktioniert

**Export & Namen**

- CSV als Primary Button ist richtig — das ist der TuneMyMusic-Pfad Nr. 1.
- Modus im Dateinamen (`Plattenradar Archiv …`) hilft bei mehreren Exporten.
- **Nochmal mischen** mit hochzählendem Suffix `(2)` ist nachvollziehbar und nützlich.
- Freitext-Textarea für TuneMyMusic ist inhaltlich korrekt (Artist – Track).

**Anleitung**

- Nummerierte Schritte sind klarer als der alte Einzeiler in der Sidebar.
- Link zu TuneMyMusic direkt in Schritt 1 — gut.

**Technik**

- Archiv-Limit-Fix verhindert den 422-Fehler bei „Alle“/großen Pools.
- Fehlermeldungen aus der API sind lesbarer (kein nacktes „Unprocessable Content“).

### UX — Auffälligkeiten

| Priorität | Thema | Befund | Vorschlag |
|-----------|-------|--------|-----------|
| P0 | Formular bleibt nach Generierung voll sichtbar | Ergebnis erscheint **unter** dem kompletten Formular. Auf Mobile sehr langer Scroll: Button → Tabelle → Anleitung. Kein Fokuswechsel. | Nach Erfolg Formular einklappen/zusammenfalten oder automatisch zum Ergebnis scrollen; optional „Einstellungen ändern“ zum Wiederaufklappen. |
| P1 | TuneMyMusic-Anleitung versteckt | `<details>` ist **zu** — viele Nutzer sehen nur die Tabelle. PR3-Ziel war „Export erklären“, aber die Erklärung landet am Seitenende, collapsed. | Nach Generierung: Anleitung **offen** und **über** der Tabelle (oder als zweite Spalte Desktop); klare Überschrift „Nächster Schritt“. |
| P1 | Vier Buttons ohne klare Gruppen | **Als CSV**, **Nochmal mischen**, **Text kopieren**, **Als TXT** in einer Leiste — Export und Regenerieren vermischen sich. | Zwei Gruppen: „Export“ (CSV primär, TXT/Text sekundär) und separat „Neue Ziehung“ (Remix). |
| P1 | CSV vs. Freitext widersprüchlich | Anleitung nennt „CSV **oder** Freitext“, gleichzeitig gibt es CSV-Download **und** große Textarea unten. Unklar, welchen Weg man nehmen soll. | Einen empfohlenen Pfad hervorheben (z. B. „Empfohlen: CSV herunterladen“) und Freitext als Alternative kennzeichnen. |
| P2 | Kein Erfolgsmoment | Nach Klick springt die Seite zur Tabelle ohne Bestätigung („30 Titel bereit“ o. ä.). | Kurzer Erfolgskopf: *„Deine Playlist ist fertig — 30 Titel aus dem Archiv.“* |
| P2 | Tabelle ohne Kontext | Nur Künstler / Album / Track — kein Rating, keine Passung, kein Review-Link (PR4-Thema, aber schon jetzt spürbar). | PR4; bis dahin: Track-Anzahl im Kopf reicht als Minimum. |
| P2 | Chip **Max.** | Technisch korrekt (API-Limit 1000), für Nutzer undurchsichtig bei „6236 Alben passen … Top 1000“. | Label z. B. „Bis 1000“ oder Hilfetext: *„Maximal 1000 Top-Alben pro Playlist.“* |
| P2 | **Nochmal mischen** ohne Erklärung | Name wird hochgezählt, Einstellungen bleiben — nicht offensichtlich. | Tooltip oder Kurztext: *„Gleiche Einstellungen, neue Zufallsauswahl.“* |
| P3 | Intro-Text noch lang | Header + Profil-Zeile + Formular + Ergebnis = viel Vorlauf. | Intro auf Ergebnis-Seite kürzen oder nach erster Generierung ausblenden. |
| P3 | Mobile Export-Buttons | Vier Buttons umbrechen auf 2+ Zeilen — okay, aber unruhig. | Primär-CSV full-width, Rest als sekundäre Zeile. |

### Ästhetik — Details

| Aspekt | Eindruck |
|--------|----------|
| **Hierarchie** | Roter CSV-Button sticht hervor — gut. Ergebnis-Überschrift (Playlist-Name) konkurriert mit Seiten-Headline „Neue Playlist erzeugen“; zwei H1-Ebenen-Gefühl. |
| **Rhythmus** | Formular → Tabelle → Details-Box: drei verschiedene Blöcke ohne visuelle Brücke. Kein „Kapitelwechsel“ zum Ergebnis. |
| **TuneMyMusic-Box** | Dezenter Rahmen, aber wirkt wie Nachthought unter der langen Tabelle. |
| **Tabelle** | Funktional, aber kalt — lange Albumtitel brechen unschön (z. B. Yves Tumor). Kein Zebra/Hover wie auf Entdecken-Kacheln. |
| **Vergleich Streamlit** | Dort nummerierte Schritte + Deezer-Link prominenter. React holt auf, aber Sichtbarkeit noch schwächer. |

### Review-Checkliste (Plan)

| Kategorie | Fragen | Notizen |
|-----------|----------|---------|
| **UX** | Export ohne Vorwissen verständlich? | Teilweise — CSV-Button hilft; Anleitung zu versteckt. |
| **UX** | Kopieren / TXT / CSV priorisiert? | CSV primär ja; TXT/Text redundant wirkend. |
| **UI** | Button-Gruppierung? | Verbesserungswürdig (Export vs. Remix). |
| **Copy** | TuneMyMusic-Schritte auf Deutsch klar? | Ja, aber zu generisch; CSV/Freitext-Wahl unklar. |
| **Namen** | Default + Remix-Suffix? | Ja, gut gelöst. |

### Akzeptanzkriterien (Plan) — Review-Stand

- [x] TuneMyMusic-Anleitung nach Generierung vorhanden
- [x] CSV vom Backend (primärer Download)
- [x] Modus-spezifische Namen + `(2)`-Suffix bei Remix
- [ ] Anleitung ausreichend **sichtbar** (aktuell collapsed, unter Tabelle)
- [ ] Export-Flow fühlt sich **geleitet** an (empfohlener Pfad fehlt)

### Fazit PR3

**Funktional ein Schritt vorwärts**, ästhetisch und narrativ noch zurückhaltend. Die
größten Hebel für das nächste Iterieren: **Ergebnis als eigene Phase** (Formular
zuklappen, Erfolgskopf, Anleitung oben offen) und **Export-Buttons strukturieren**.
Die reine Track-Tabelle bleibt bis PR4 das Hauptästhetik-Problem.

### Bugfix in PR3 (Nebenbefund)

- `archive_limit` > 1000 → 422; UI jetzt gekappt. Chip „Max.“ statt „Alle“ bei großen Pools.

---

## PR4 — Ergebnisliste (Hybrid-Zeilen, Kontext)

**Branch:** `cursor/playlist-pr4-results-c980`  
**Review-Datum:** _noch nicht reviewed_

### Geplant laut Umsetzungsplan

- Ergebniszeilen mit Rating, Passung, Review-Link, ggf. Fotos
- Weniger „HTML-Tabelle“, mehr Anbindung an Entdecken-Ästhetik

### Review-Checkliste (auszufüllen)

| Kategorie | Fragen | Notizen |
|-----------|----------|---------|
| **UX** | Erkennt man sofort, warum ein Track in der Playlist ist? | |
| **UI** | Anschluss an Highlight-Kacheln / RecommendationList? | |
| **Mobile** | Tabelle vs. Karten auf 390px? | |
| **Ästhetik** | Fühlt sich die Seite wie Abschluss der Entdeckungsreise an? | |

### Feedback

_(noch offen)_

---

## PR5 — Tests & Screenshots

**Branch:** `cursor/playlist-pr5-screenshots-c980`  
**Review-Datum:** _noch nicht reviewed_

### Geplant laut Umsetzungsplan

- Playwright-Referenzen Formular Desktop/Mobile + Ergebnis
- Regression gegen Überlappung Mobile

### Review-Checkliste (auszufüllen)

| Kategorie | Fragen | Notizen |
|-----------|----------|---------|
| **CI** | Screenshots stabil auf Linux? | |
| **Coverage** | Neuheiten + Archiv + Ergebnis abgedeckt? | |
| **Docs** | Dieses Feedback-Dokument aktualisiert? | |

### Feedback

_(noch offen)_

---

## Übergreifende Themen (alle PRs)

| Thema | Status | Ziel-PR |
|-------|--------|---------|
| Emotionaler Anschluss an Aktuell/Entdecken | offen | PR4 |
| TuneMyMusic-Export erklären | teilweise (PR3: Anleitung vorhanden, aber versteckt) | PR3-Follow-up |
| Archiv-Pool-Steuerung vereinfachen | teilweise (Limit-Fix; Doppelsteuerung offen) | PR2/PR3-Follow-up |
| Slider-Zwischenfeedback | offen | PR2-Follow-up |
| Ergebnis als eigene Phase (Formular nach Generierung) | offen | PR3-Follow-up oder PR4 |
| Export-Button-Gruppierung (Export vs. Remix) | offen | PR3-Follow-up |
| Aktive Profil-Filter auf Playlist-Seite sichtbar | offen | später |
| Vorschau vor Generierung | bewusst nicht in v1 | — |

---

## Changelog

| Datum | PR | Änderung |
|-------|-----|----------|
| 2026-07-03 | PR1 | Erstreview: Mobile-Fix bestätigt, keine Regression |
| 2026-07-03 | PR2 | UX/UI-Review mit Screenshots (Desktop + Mobile, Neuheiten + Archiv) |
| 2026-07-03 | PR3 | UX/UI-Review Export-Flow, Ergebnisansicht, Remix; Screenshot Ergebnis Mobile |
