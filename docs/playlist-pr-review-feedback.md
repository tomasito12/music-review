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
| **Integrations-Branch (empfohlen)** | `cursor/playlist-integration-c980` (PR1–PR5 zusammen) |
| Branch PR3 (historisch) | `cursor/playlist-pr3-export-c980` |
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

## Integration v2 — Gesamtreview (Product Owner)

**Branch:** `cursor/playlist-integration-c980`  
**Review-Datum:** 2026-07-03  
**Tester:** Product Owner (manuelles Durchklicken nach Zusammenführung PR2–PR5)

Dieser Abschnitt bündelt **neues Nutzer-Feedback** auf dem Integrations-Stand. Er ist die
Basis für die **nächste Implementierungsrunde** (v2). Agent-Reviews aus PR1–PR3 bleiben
darunter als Referenz erhalten.

### Gesamteindruck

Die Playlist-Generierung ist funktional weit — Formular, Ergebniszeilen mit Fotos und
Export sind grundsätzlich da. In der Nutzung wirkt die Seite aber noch **unruhig**
(Moduswechsel, Button-Leiste, unklare Slider) und der Export-Flow zu **mehrstufig**
(TuneMyMusic-Link versteckt, viele gleichwertige Buttons). Mehrere Punkte aus dem
Agent-Review (PR2/PR3) werden hier **bestätigt und verschärft**.

---

### 1. Moduswechsel Neuheiten ↔ Archiv — springende Box

**Befund:** Bei Neuheiten erscheint oberhalb der Formular-Box eine Zeile wie
*„Aus deinen Neuheiten · Letzte Update-Runde“*. Bei Archiv fehlt diese Zeile — die Box
rutscht nach oben/unten. Beim Hin- und Herspringen wirkt das Layout instabil.

**Einordnung:** Die Zeile ist **keine Überschrift**, sondern eine **Kontextzeile**
(Deep-Link-Herkunft + gewählter Zeitraum). Sie wird nur im Neuheiten-Modus gerendert,
wenn man von Neuheiten in die Playlist-Seite kam (`playlistSourceContextLine`).

**Empfehlung (Agent):** Die Zeile im Formularbereich **entfernen oder beidseitig
stabilisieren**. Modus-Karten (Neuheiten / Archiv) und das Zeitraum-Dropdown erklären
den Kontext bereits; die Kontextzeile ist redundant und verursacht den Layout-Sprung.
Falls Herkunft wichtig bleibt: für **beide** Modi eine gleich hohe Zeile reservieren
(z. B. Archiv: *„Aus dem Plattentests-Archiv“*) — aber lieber ganz weg und nur in
Modus-Karte + Feldern kommunizieren.

| Priorität | Aktion |
|-----------|--------|
| P1 | Kontextzeile nicht modus-abhängig ein-/ausblenden (entfernen oder symmetrisch) |

---

### 2. Zeitraum / Update-Runden — nur drei Optionen

**Befund:** Dropdown bietet nur *Letzte Update-Runde*, *Letzte 4*, *Letzte 8*.
Das fühlt sich zu grob an — vor allem wenn lokal nur wenige echte Scrape-Batches existieren
(unregelmäßige Updates in den letzten Wochen → effektiv ~3 unterscheidbare „Runden“).

**Technischer Hintergrund (Ist-Stand Code):**

- Backend: `select_reviews_for_update_rounds` — bis **20 Runden** (`MAX_UPDATE_ROUNDS`).
  Mit Batch-Historie (`update_batches.jsonl`) werden echte Scrape-Läufe genutzt;
  **ohne** Historie: Fallback **20 Reviews pro Runde** (`REVIEWS_PER_ROUND_FALLBACK = 20`,
  analog `NEW_REVIEWS_PER_ROUND` im Frontend).
- Frontend Playlist: nur **3 feste Optionen** (`UPDATE_ROUND_OPTIONS`: 1 / 4 / 8).
- Stündlicher Cron auf Produktion soll Batch-Historie langfristig füllen — dann werden
  mehr echte Runden verfügbar.

**Nutzer-Wunsch:** Zwischenlösung, bis tägliche/stündliche Updates die Batch-Lücken
schließen. Erinnerung an Diskussion: *„Jede Update-Runde = 20 Titel“* als Fallback-Logik
— im Code bereits angelegt, aber in der UI nicht transparent.

**Offene Produktfragen:**

| Frage | Notizen |
|-------|---------|
| Mehr als 3 Optionen? | Backend erlaubt 1–20; UI könnte z. B. 1 / 2 / 4 / 8 / 12 / 20 oder Slider „letzte N Runden“ anbieten. |
| Dropdown skaliert? | Bei 1–20 Runden noch okay; ab ~10 eher **Segment-Chips** oder **Slider mit Label** (*„ca. 60 neueste Reviews“*). |
| Fallback sichtbar machen? | Wenn keine Batch-Historie: Hinweis *„Zeitraum geschätzt (je ~20 Reviews pro Runde)“* statt stiller Fallback. |
| Abhängigkeit Cron | Kein reines UI-Problem — mit regelmäßigen Scrapes wird Batch-Modus dominieren. |

| Priorität | Aktion |
|-----------|--------|
| P1 | Zeitraum-Auswahl erweitern (mind. feinere Stufen bis 20) und Fallback in Copy erklären |
| P2 | Pool-Größe im UI anzeigen (*„~40 Reviews aus 2 Runden“*) |

---

### 3. Fokus-Slider (Neuheiten) — nicht intuitiv

**Befund:** Slider *Entdecken ↔ Fokus* ist inhaltlich unklar. **„Fokus“** kommt doppelt vor
(Feldlabel und rechter Endpunkt). Keine Erklärung, was sich an der Playlist ändert.
Entspricht nicht dem Anspruch an intuitive Bedienung.

**Technisch:** Steuert `tasteExponent` + `selectionStrategy` (gewichtete vs. stratifizierte
Auswahl) — für Nutzer nicht erkennbar.

**Bestätigt:** Entspricht Agent-Finding PR2 (P2 „Label Fokus doppelt“, Slider ohne Zwischenfeedback).

| Priorität | Aktion |
|-----------|--------|
| P0 | Slider neu benennen + Kurztext/Hilfe (*was passiert bei links vs. rechts?*) |
| P1 | Zwischenfeedback oder Beispiel-Sätze statt nackter Endlabels |

---

### 4. Formular — Positives (beide Modi)

| Element | Eindruck |
|---------|----------|
| **Anzahl Tracks** | Gut umgesetzt (Chips + Hinweise) — gilt für Neuheiten und Archiv. |
| **Playlist-Name Neuheiten** | Gut; Default `Plattenradar YYYY-MM-DD` passt. |
| **Playlist-Name Archiv** | Default soll **`Plattenarchiv YYYY-MM-DD`** heißen (ein Wort, **ohne** Bindestrich). Aktuell: `Platten-Archiv …`. |

| Priorität | Aktion |
|-----------|--------|
| P2 | Default-Name Archiv auf `Plattenarchiv` umstellen (Code + Tests + Screenshots) |

---

### 4a. Archiv — Top-Alben aus deinem Profil

**Befund:** UI meldet z. B. *„10.000 Alben passen zu deinem Profil“*, Auswahl ist aber auf
**max. 1000** begrenzt (API-Limit `archive_limit`). Wirkt widersprüchlich.

**Einordnung:** Technisches API-Maximum; Chip **Max.** bei großen Pools ist korrekt, aber
die Diskrepanz zwischen angezeigtem Pool und wählbarem Maximum irritiert.

**Entscheidung (PO):** Erst mal **so lassen** — kein v2-Blocker. Langfristig API-Limit oder
Kommunikation prüfen (*„Playlist aus bis zu 1000 Top-Alben“*).

| Priorität | Aktion |
|-----------|--------|
| P3 | Copy/Hilfetext: erklären, warum bei sehr großen Pools nur 1000 wählbar sind |
| — | API-Limit erhöhen | bewusst zurückgestellt |

---

### 4b. Archiv — „Titel pro Album“ (Breit streuen ↔ Alben vertiefen)

**Befund:** Slider *Breit streuen* / *Alben vertiefen* ist — wie der Fokus-Slider bei
Neuheiten — **inhaltlich nicht verständlich**. Nutzer erwartet konkretes Verhalten:

| Position | Erwartetes Verhalten (PO) |
|----------|---------------------------|
| **Ganz links (Breit streuen)** | Jedes Album höchstens **ein** Track in der Playlist |
| **Ganz rechts (Alben vertiefen)** | Wenige Alben (ca. **1–2**), dafür **mehrere Titel pro Album** (bis ca. **4**) |

**Technischer Ist-Stand:** `archiveDepth` steuert nur `tasteExponent` + `selectionStrategy`
(gewichtete vs. stratifizierte Ziehung) — **keine** explizite Obergrenze „Tracks pro Album“.
Das erklärt die Lücke zwischen UI-Versprechen und tatsächlichem Ergebnis.

**Frage:** Slider oder Presets?

**Empfehlung (Agent):** **Presets (Segment-Chips)** statt kontinuierlichem Slider — analog
zu „Anzahl Tracks“, das gut ankommt.

| Preset (Vorschlag) | Nutzerversprechen | Umsetzung (Ziel) |
|--------------------|-------------------|------------------|
| **Vielfalt** | Möglichst viele verschiedene Alben | Max. 1 Highlight-Track pro Album erzwingen |
| **Ausgewogen** | Mix aus Breite und Tiefe | Default; moderates Album-Limit (z. B. 2–3 Tracks/Album) |
| **Album vertiefen** | Wenige Alben, mehr Songs davon | Max. 2–3 Alben dominieren, bis 4 Tracks/Album |

**Warum keine Skala:** Die gewünschten Endpunkte sind **diskrete Playlist-Logiken**, keine
feine Gewichtungskurve. Drei benannte Modi sind leichter zu testen, zu erklären und in der
Hilfe zu beschreiben als „35 % Archiv-Tiefe“.

**Optional später:** Unter „Erweitert“ ein Slider — für v2 reichen Presets + ein Satz
Hilfetext unter der Auswahl.

| Priorität | Aktion |
|-----------|--------|
| P0 | Slider durch **3 Presets** ersetzen (Vielfalt / Ausgewogen / Album vertiefen) |
| P0 | Backend/Builder: echte Regeln **max. Tracks pro Album** (nicht nur Gewichtung) |
| P1 | Kurztext unter Presets mit Beispiel (*„bis zu 30 Alben · je 1 Titel“*) |

---

### 5. Ergebnis — Export-Buttons (vier in einer Reihe)

**Gilt für Neuheiten und Archiv** (gleiche Ergebnisansicht).

**Befund:** Nach „Playlist vorbereiten“ oben **vier Buttons**: CSV, Nochmal mischen, Text
kopieren, TXT. Passen nicht in eine Zeile → umbrechen, wirkt unruhig und billig.

**Zusätzlich:** **Nochmal mischen** hat eine andere Funktion (neue Zufallsziehung) als die
drei Export-Aktionen — sollte visuell getrennt sein.

**Bestätigt:** Agent-Review PR3 (P1 Button-Gruppierung, P3 Mobile-Umbruch).

| Priorität | Aktion |
|-----------|--------|
| P0 | Zwei Gruppen: **Export** (CSV primär, TXT/Kopieren sekundär) vs. **Neue Ziehung** (Mischen) |
| P1 | Layout: CSV full-width oder 2-Zeilen-Raster; kein 4er-Chaos in einer Zeile |

---

### 6. Ergebnis — Künstler-Mosaik (max. 6 Kacheln)

**Befund:** Oben maximal **6 Künstlerbilder** als Kacheln; darunter deutlich mehr Zeilen
mit Fotos. Nutzer fragen sich: *Warum nur diese sechs?*

**Agent-Einordnung (UX):**

| Option | Pro | Contra |
|--------|-----|--------|
| **Mosaik entfernen** | Keine Redundanz; Fotos nur in Zeilen — konsistent. | Weniger „Playlist-Cover“-Gefühl oben. |
| **Mosaik behalten, erklären** | Dekorativer Header möglich. | Braucht Copy (*„Auszug aus deiner Playlist“*) — erklärt trotzdem nicht die Zahl 6. |
| **Alle Künstler als Mosaik** | Keine willkürliche Grenze. | Bei 30+ Tracks unübersichtlich und langsam (Bilder). |

**Empfehlung:** Mosaik **streichen** oder durch **kompakten Erfolgskopf** ersetzen
(*„30 Titel · Plattenarchiv 2026-07-03“*). Fotos gehören in die Zeilen — dort sind sie
funktional (Orientierung pro Track). Die 6er-Kachel wirkt wie ein halbes Feature.

| Priorität | Aktion |
|-----------|--------|
| P1 | Mosaik entfernen oder durch statischen Kopf ersetzen |
| P2 | Falls Mosaik bleibt: kurze Begründung in UI |

---

### 7. Ergebnis — Zeilen: Metadaten & Leerraum

**Gilt für Neuheiten und Archiv** — PO-Feedback aus beiden Modi.

**Befund:** Rechts in den Ergebniszeilen ist viel **ungenutzter Platz**. Bei langen
ersten Zeilen (Künstler · Album) ist der Platz gut (kein unschöner Umbruch); bei kurzen
Zeilen wirkt die rechte Hälfte leer.

**Wunsch:** Zusätzliche Metadaten in den Zeilen, z. B.:

- **Erscheinungsjahr**
- **Plattenlabel**

(Daten in `metadata` / MusicBrainz grundsätzlich im System vorhanden — Anbindung an
Playlist-Export-Items prüfen.)

| Priorität | Aktion |
|-----------|--------|
| P1 | Jahr + Label in Ergebniszeile (rechte Spalte oder zweite Zeile) |
| P2 | Layout: rechte Spalte nur wenn Metadaten da; sonst schmalere Zeile |

---

### 7a. Ergebnis — Künstler-Thumbnails (Größe & Nutzen)

**Gilt für Neuheiten und Archiv.**

**Befund:** Thumbnails in den Ergebniszeilen sind oft **sehr klein**; auf dem Foto erkennt
man häufig nichts. Nutzer fragt sich: *Warum überhaupt Bilder, wenn sie nichts zeigen?*
Zusatzfrage: Soll ein Klick das Bild vergrößern?

**Einordnung:** Fotos sind **Dekoration / Orientierung**, kein Kernfeature der Playlist.
Sie sollen „Farbe“ und Wiedererkennung bringen — funktionieren nur, wenn das Motiv
erkennbar ist.

**Empfehlung (Agent):**

| Option | Bewertung |
|--------|-----------|
| **Klick → Lightbox / groß** | Für v2 **nicht empfohlen** — extra UI, wenig Mehrwert für den Export-Flow; Nutzer will danach exportieren, nicht Bilder betrachten. |
| **Größe leicht erhöhen** | Sinnvoll, wenn Layout es zulässt (z. B. 40–48 px statt aktuell kleiner). |
| **Fallback Initialen-Avatar** | Wenn kein brauchbares Bild: farbiger Kreis mit Initialen (wie Entdecken) — klarer als unlesbares Foto. |
| **Thumbnails ganz weglassen** | Nur wenn Metadaten (Jahr, Label) die Zeile tragen; sonst wirkt Liste zu textlastig. |

**Fazit:** Kleine unlesbare Fotos sind schlechter als gut lesbare Initialen. **Kein**
Tap-to-Zoom in v2; stattdessen erkennbare Größe oder Initialen-Fallback. Kein P0.

| Priorität | Aktion |
|-----------|--------|
| P2 | Thumbnail-Größe prüfen; Initialen-Fallback wenn Bild fehlt/unbrauchbar |
| P3 | Kein Lightbox-Zoom (bewusst nicht) |

---

### 8. TuneMyMusic — Import vereinfachen

**Befund:** Link *„TuneMyMusic öffnen“* in der Anleitung ist **versteckt** (in `<details>`,
unter der Trackliste). Für jeden Import nötig — zu viele Schritte: CSV laden, Seite
suchen, Link klicken, Datei hochladen.

**Nutzer-Idee:** Download und TuneMyMusic in **einem Schritt** — z. B.:

- Ein Button *„CSV herunterladen und TuneMyMusic öffnen“* (Download + `window.open` auf
  TuneMyMusic-Import-URL mit Hinweis zum Datei-Upload), oder
- Deep-Link soweit TuneMyMusic API/URL-Schema es erlaubt (zu prüfen).

**Bestätigt:** Agent-Review PR3 (Anleitung versteckt, Export nicht geleitet).

| Priorität | Aktion |
|-----------|--------|
| P0 | TuneMyMusic-Schritt **prominent** direkt neben CSV (nicht nur in Details) |
| P1 | Kombi-Aktion „Export + TuneMyMusic öffnen“ |
| P2 | Anleitung nach Generierung standardmäßig **aufgeklappt** |

---

### Prioritäten v2 (Konsolidiert)

| P | Thema | Quelle |
|---|-------|--------|
| P0 | Fokus-Slider (Neuheiten) verständlich machen | PO + PR2 |
| P0 | Archiv „Titel pro Album“ als Presets + echte Album-Regeln | PO |
| P0 | Export-Buttons gruppieren + Layout beruhigen | PO + PR3 |
| P0 | TuneMyMusic prominenter / Kombi-Schritt | PO + PR3 |
| P1 | Kontextzeile Moduswechsel (Layout-Sprung) | PO |
| P1 | Update-Runden: mehr Optionen + Fallback erklären | PO |
| P1 | Mosaik oben entfernen oder ersetzen | PO |
| P1 | Jahr + Label in Ergebniszeilen (Neuheiten + Archiv) | PO |
| P2 | Default-Name `Plattenarchiv` (ohne Bindestrich) | PO |
| P2 | Thumbnail-Größe / Initialen-Fallback | PO |
| P2 | Ergebnis als eigene Phase (Formular einklappen) | PR3 |
| P2 | Archiv-Pool Doppelsteuerung (Chips + Slider) | PR2 |
| P3 | Archiv-Pool 1000 vs. angezeigtes Total erklären | PO |

### Fazit Integration v2

**Nicht neu bauen, sondern polieren:** Die Pipeline steht; die nächste Runde soll
**Ruhe ins Layout** (symmetrisches Formular, ruhige Button-Hierarchie), **Klarheit bei
Steuerungen** (Zeitraum, Fokus, **Archiv-Titel-pro-Album**) und **Export in einem Atemzug**
(TuneMyMusic) bringen. Ergebniszeilen können mit Metadaten, erkennbaren Avataren und ohne
redundantes Mosaik professioneller wirken.

---

## v2 — Implementierungsreview (Playlist v2)

**Branch:** `cursor/improve-playlist-v2`  
**Review-Datum:** 2026-07-03  
**Basis:** Integration v2 PO-Feedback + Phasen 1–4 aus [`playlist-v2-redesign-plan.md`](playlist-v2-redesign-plan.md)

### Umgesetzt (Kurz)

| Thema | Status |
|-------|--------|
| Zwei-Phasen-UI (Formular einklappen nach Generierung) | erledigt (Phase 1) |
| Export-Gruppen + CSV/TuneMyMusic-Kombi | erledigt (Phase 1) |
| Kontextzeile Layout-Sprung entfernt | erledigt (Phase 1) |
| Default `Plattenarchiv` | erledigt (Phase 1) |
| Neuheiten Mood-Presets statt Fokus-Slider | erledigt (Phase 2) |
| Zeitraum-Chips 1/2/4/8/12/20 + Pool-Hinweis | erledigt (Phase 2) |
| Archiv-Pool nur Chips (kein Doppel-Slider) | erledigt (Phase 2) |
| Mosaik entfernt, Erfolgskopf | erledigt (Phase 2) |
| Initialen-Fallback, größere Thumbnails | erledigt (Phase 2) |
| Archiv Spread-Presets + Backend Album-Caps | erledigt (Phase 3) |
| Jahr + Label in Ergebniszeilen | erledigt (Phase 3) |
| Erweitert-Akkordeon (Name, Fein-Slider) | erledigt (Phase 4) |
| Playwright-Referenzen aktualisiert | erledigt (Phase 4) |

### Offen / bewusst zurückgestellt

| Thema | Notiz |
|-------|-------|
| API-Limit > 1000 | PO-Entscheidung: später |
| Lightbox auf Künstlerbildern | bewusst nicht in v2 |
| Rating / Passung in Zeilen | später |
| Vorschau vor Generierung | nicht in v1/v2 |

### Fazit v2

Die Playlist-Seite folgt jetzt dem Zwei-Phasen-Modell: ruhiges Konfigurieren, dann
klarer Export-Moment mit TuneMyMusic-Führung. Presets ersetzen undurchsichtige Slider;
Feinjustierung bleibt optional unter **Erweitert**. Archiv-Spread-Regeln sind im Backend
verankert. Nächster Schritt: PO-Re-Test auf Mobile und Desktop.

### PO-Nachreview (2026-07-07)

| Thema | Befund | Aktion |
|-------|--------|--------|
| **Zeitraum / Update-Runden** | Frage: echte Batch-Größe (z. B. 12 Reviews) vs. Heuristik ~20 | Copy erklärt jetzt beide Modi; Backend nutzt `update_batches.jsonl` exakt wenn vorhanden |
| **Label „Auswahl-Stil“** | Trifft Inhalt nicht — geht um Profil-Passung/Streuung | Umbenannt zu **Passung zum Musikprofil** |
| **Vielfalt-Hilfetext** | „Überraschungen“ / „weiter weg“ impliziert Ausschluss Naher | Neu: passende Neuheiten **plus** entferntere |
| **Ausgewogen-Hilfetext** | „Bekanntes“ passt nicht bei Neuheiten | Neu: überwiegend passend, etwas Abstand |
| **Stark fokussiert** | Mehrere Titel pro Album erwähnen | Hilfetext ergänzt |
| **Erweitert Abstand** | Playlist-Name zu nah am Folgeblock | CSS-Abstand erhöht |

---

## PR4 — Ergebnisliste (Hybrid-Zeilen, Kontext)

**Branch:** `cursor/playlist-pr4-results-c980`  
**Review-Datum:** 2026-07-03 (Agent + PO auf Integrations-Branch)

### Umgesetzt (Kurz)

- Hybrid-Zeilen mit Künstlerfoto, Review-Link, Track/Album-Zeile
- Optional: Künstler-Mosaik (max. 6 Bilder) über der Liste
- `artist_mbid` für zuverlässige Bild-Lookups
- Default-Namen: `Plattenradar` / `Platten-Archiv` + Datum; Export-Suffix `(2)` nur beim Download

### Feedback (Product Owner — siehe auch **Integration v2**)

| Kategorie | Befund |
|-----------|--------|
| **UX** | Mosaik (6 Kacheln) vs. Zeilen-Fotos — wirkt willkürlich; siehe Integration v2 §6. |
| **UX** | Rechts viel Leerraum in Zeilen; Wunsch: Erscheinungsjahr + Label. |
| **UI** | Lange Albumtitel nutzen Platz gut; kurze Zeilen wirken unausgewogen. |
| **Positiv** | Fotos in Zeilen grundsätzlich hilfreich; Review-Links sinnvoll. |

### Review-Checkliste (Agent)

| Kategorie | Fragen | Notizen |
|-----------|----------|---------|
| **UX** | Erkennt man sofort, warum ein Track in der Playlist ist? | Noch schwach — keine Passung/Rating in Zeile. |
| **UI** | Anschluss an Highlight-Kacheln / RecommendationList? | Teilweise (Fotos); weniger narrative Tiefe. |
| **Mobile** | Tabelle vs. Karten auf 390px? | Hybrid-Zeilen okay; Button-Leiste problematisch (v2). |
| **Ästhetik** | Fühlt sich die Seite wie Abschluss der Entdeckungsreise an? | Noch nicht — Formular bleibt sichtbar. |

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

| Thema | Status | Ziel |
|-------|--------|------|
| Emotionaler Anschluss an Aktuell/Entdecken | teilweise | v2 |
| TuneMyMusic-Export erklären + Kombi-Schritt | erledigt | v2 |
| Archiv-Pool-Steuerung vereinfachen | erledigt | v2 |
| Fokus-/Tiefen-Slider verständlich | erledigt (Presets) | v2 |
| Zeitraum/Update-Runden (mehr Optionen, Fallback-Copy) | erledigt | v2 |
| Archiv „Titel pro Album“ (Presets statt Slider) | erledigt | v2 |
| Default-Name `Plattenarchiv` (ohne Bindestrich) | erledigt | v2 |
| Archiv-Pool Anzeige vs. Limit 1000 | zurückgestellt (PO P3) | später |
| Künstler-Thumbnails (Größe, Initialen, kein Zoom) | erledigt | v2 |
| Kontextzeile Layout-Sprung Neuheiten/Archiv | erledigt | v2 |
| Export-Button-Gruppierung (Export vs. Remix) | erledigt | v2 |
| Künstler-Mosaik (6er) vs. Zeilen-Fotos | erledigt | v2 |
| Metadaten Jahr + Label in Ergebniszeilen | erledigt | v2 |
| Ergebnis als eigene Phase (Formular nach Generierung) | erledigt | v2 |
| Slider-Zwischenfeedback | erledigt (Presets + Erweitert) | v2 |
| Aktive Profil-Filter auf Playlist-Seite sichtbar | offen | später |
| Vorschau vor Generierung | bewusst nicht in v1 | — |

---

## Changelog

| Datum | PR | Änderung |
|-------|-----|----------|
| 2026-07-03 | PR1 | Erstreview: Mobile-Fix bestätigt, keine Regression |
| 2026-07-03 | PR2 | UX/UI-Review mit Screenshots (Desktop + Mobile, Neuheiten + Archiv) |
| 2026-07-03 | PR3 | UX/UI-Review Export-Flow, Ergebnisansicht, Remix; Screenshot Ergebnis Mobile |
| 2026-07-03 | Integration v2 | Product-Owner-Review auf `cursor/playlist-integration-c980`; Prioritäten für nächste Runde |
| 2026-07-03 | Integration v2 | Archiv-Feedback: Pool-Limit, Titel-pro-Album-Presets, Plattenarchiv, Thumbnails |
| 2026-07-03 | v2 | Implementierungsreview Phasen 1–4 auf `cursor/improve-playlist-v2` |
