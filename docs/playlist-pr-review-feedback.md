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
| Branch PR2 | `cursor/playlist-pr2-form-c980` (enthält PR1 + PR2) |
| Frontend | `hatch run frontend` → http://127.0.0.1:5173 |
| API | `hatch run api` → http://127.0.0.1:8000 |
| Daten | `data/reviews.jsonl` muss lokal vorhanden sein (z. B. `./sync_data.sh pull`) |
| Screenshots PR2-Review | `frontend/screenshots/review-2026-07-03/` |

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
| P1 | Doppelsteuerung Archiv-Pool | Chips (50 / 200 / Alle) **und** Range-Slider für dieselbe Größe. | Ein führendes Control wählen oder Synchronisation visuell eindeutiger machen (Slider-Position bei Chip „200“ wirkte links — irritierend). |
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
**Review-Datum:** _noch nicht reviewed_

### Geplant laut Umsetzungsplan

- TuneMyMusic-Anleitung (nummeriert, nach Generierung)
- CSV primär vom Backend
- Playlist-Namen nach Modus + Datum + Suffix `(2)`

### Review-Checkliste (auszufüllen)

| Kategorie | Fragen | Notizen |
|-----------|----------|---------|
| **UX** | Ist der Export-Flow ohne Vorwissen verständlich? | |
| **UX** | Sind Kopieren / TXT / CSV klar priorisiert? | |
| **UI** | Gruppierung der Export-Buttons? | |
| **Copy** | TuneMyMusic-Schritte verständlich auf Deutsch? | |
| **Namen** | Default-Namen nachvollziehbar bei wiederholter Generierung? | |

### Feedback

_(noch offen)_

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
| TuneMyMusic-Export erklären | offen | PR3 |
| Archiv-Pool-Steuerung vereinfachen | offen | PR2-Follow-up oder PR4 |
| Slider-Zwischenfeedback | offen | PR2-Follow-up |
| Aktive Profil-Filter auf Playlist-Seite sichtbar | offen | später |
| Vorschau vor Generierung | bewusst nicht in v1 | — |

---

## Changelog

| Datum | PR | Änderung |
|-------|-----|----------|
| 2026-07-03 | PR1 | Erstreview: Mobile-Fix bestätigt, keine Regression |
| 2026-07-03 | PR2 | UX/UI-Review mit Screenshots (Desktop + Mobile, Neuheiten + Archiv) |
