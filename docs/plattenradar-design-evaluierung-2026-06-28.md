# Plattenradar: Design-Evaluierung (Ist-Stand)

Status: Abgeschlossene Review  
Datum: 2026-06-28  
Basis: Live-Frontend (`http://127.0.0.1:5173`) mit echter API (`http://127.0.0.1:8000`), temporärem Musikprofil und Screenshots unter `frontend/screenshots/`

Dieses Dokument ergänzt
[`plattenradar-designrunde-layout-befunde.md`](plattenradar-designrunde-layout-befunde.md).
Dort stehen Zielbild, Richtungen und offene Layout-Fragen. Hier steht eine
Bewertung des **aktuell implementierten** Stands: was trägt schon, was bremst,
und welche Schritte als Nächstes sinnvoll sind.

## Methodik

- Desktop (1440×900) und Mobile (390×844) für `Aktuell` und `Entdecken`
- Zusätzlich: `Willkommen`, `Musikprofil`, `Playlists`, Mock-Referenz `aktuell-redesign.png`
- Bewertung aus Produktsicht: Scanbarkeit, Haltung, Vertrauen, Freude an der Nutzung
- Nicht bewertet: Backend-Performance im Detail, SEO, Accessibility-Audit (nur
  punktuelle Hinweise)

Screenshot-Dateien (Auszug):

| Datei | Inhalt |
|-------|--------|
| `live-aktuell-desktop.png` | Aktuell mit echten Empfehlungen |
| `live-entdecken-desktop.png` | Entdecken mit Rank-1-Lead + Filter |
| `live-aktuell-mobile.png` / `live-entdecken-mobile.png` | Mobile Varianten |
| `willkommen.png` | Landing ohne Profil |
| `live-musikprofil-desktop.png` | Profil-Wizard Schritt 1 |
| `live-playlists-desktop.png` | Playlist-Generator |
| `aktuell-redesign.png` | Mock-API-Referenz mit Highlight-Fotos |

---

## Gesamteindruck

Plattenradar hat in den letzten Wochen einen **klaren Sprung von Tool zu Produkt**
gemacht. Die warme Papier-Optik, die Serif-Überschriften und die editorialen
Highlight-Kacheln auf `Aktuell` transportieren das gewünschte Gefühl: indie-nah,
sorgfältig, persönlich – ohne Streaming-App- oder Portal-Ästhetik.

Gleichzeitig ist der Stand **zweigleisig**: `Aktuell` fühlt sich schon wie eine
kuratierte Startseite an, `Entdecken` noch wie eine funktionale Ergebnisliste,
`Musikprofil` und `Playlists` wie solide Werkzeuge. Das ist für die Entwicklung
nachvollziehbar, wirkt nach außen aber noch nicht wie ein durchgestaltetes
Gesamtprodukt.

Der größte funktionale Bruch im Moment: **Künstlerfotos**. Das Layout ist auf
Bild/Text-Kacheln vorbereitet, in der Live-Ansicht fehlen Fotos aber oft
komplett (leere Beige-Flächen auf `Aktuell`, reine Textkarten auf `Entdecken`).
Das untergräbt genau den visuellen Gewinn, für den das neue Layout gebaut wurde.

---

## Seitenweise Befunde

### Willkommen (`/`)

**Stärken**

- Starke Serif-Headline mit klarer Neugier-Frage; passt zum Produktversprechen.
- Copy erklärt plattentests.de und Plattenradar ohne Überladung.
- Zwei klare Einstiege (Profil erstellen / schon Profil) mit sauberer
  Button-Hierarchie (rot primär, Ghost sekundär).
- Viel Weißraum wirkt einladend, nicht leer.

**Schwächen**

- Seite ist rein typografisch; kein visueller Anker (kein Foto, kein
  Platten-Motiv, keine Mini-Vorschau).
- Navigation oben suggeriert vollen App-Umfang, obwohl ohne Profil kaum Inhalte
  erreichbar sind – kann verwirren.
- Mobile: Navigationszeile wird schnell eng; noch kein dediziertes
  Mobile-Menü.

**Bewertung:** Gute Landing, aber noch **Einstiegsseite**, nicht
**Vorfreude-Maschine**.

---

### Aktuell (`/aktuell`)

**Stärken**

- **Briefing-Header** (Kicker + große Headline + CTA) setzt persönlichen Ton;
  „Schön, dass du zurück bist“ trifft die Zielgruppe.
- **Highlight-Sektion** mit wechselnder Bild/Text-Anordnung ist der stärkste
  Design-Griff im ganzen Produkt: editorial, scanbar, nicht wie ein Ranking.
- Drei inhaltliche Rollen (Beste Passung / Kritikerfavorit / Außerhalb des
  Profils) geben Orientierung ohne Gamification.
- **Filter-Prelude** (Zeitraum, Chips, einklappbare Filter, Tag-Legende) trennt
  Kuratierung von der dichten Liste – logisch und ruhig.
- **Ranking-Liste** darunter ist kompakt; Rank-Badge, Tags, Auszug und
  dezenter Score funktionieren als Scan-Einheit.
- Save-Herz ist konsistent platziert (auch wenn noch deaktiviert).

**Schwächen**

- **Fotos in Live-Betrieb:** Highlight-Kacheln zeigen oft nur leere
  Beige-Flächen. Das wirkt wie unfertiges Layout, nicht wie bewusste
  Platzhalter-Ästhetik.
- **Zwei Geschwindigkeiten:** Oben großzügig/editorial, unten dicht/listig –
  der Übergang ist abrupt; die Liste fühlt sich nach „Backend-Ausgabe“ an.
- **CTA-Konkurrenz:** „Playlist aus Aktuell vorbereiten“ steht sehr prominent
  neben dem Briefing; auf Mobile konkurriert er mit der Headline um Aufmerksamkeit.
- **Filter-Dichte:** Preset-Pills + Toolbar + Details-Panel + Legende sind
  funktional stark, visuell aber schwer – besonders beim ersten Besuch nach dem
  Highlight-Moment.
- **Deaktivierte Herzen** ohne erklärenden Tooltip wirken wie kaputtes UI
  (Tooltip existiert im Code, ist aber leicht zu übersehen).
- **Mock vs. Live:** Die Playwright-Referenz mit Demo-Fotos zeigt das Zielbild;
  Live weicht davon stark ab → Erwartungsmanagement für Stakeholder schwierig.

**Bewertung:** **Beste Seite im Produkt.** Layout-Richtung stimmt; Foto-Pipeline
und Feinschliff an Übergängen sind der Engpass.

---

### Entdecken (`/entdecken`)

**Stärken**

- Klassischer **Seitenkopf** (Archiv-Eyebrow, Titel, erklärender Satz) passt
  zum Archiv-Kontext besser als ein Aktuell-Briefing.
- **Rank 1 vor dem Filter** ist eine gute redaktionelle Entscheidung: ein
  klarer Einstieg, bevor Werkzeuge folgen.
- Archiv-spezifische Kopfzeile („X Alben passen zu deinem Musikprofil …“) ist
  sachlich und hilfreich.
- Save-Herz jetzt auch hier – Konsistenz mit Aktuell.
- Geplante Foto-Kacheln im Listenrhythmus (Rank 1, dann ~alle sechs Plätze mit
  Fallbacks) sind konzeptionell richtig für lange Listen.

**Schwächen**

- **Visuell noch die alte Welt:** In Live-Screenshots wirkt Rank 1 wie eine
  normale Karte; Foto-Kacheln fehlen (langsamer Bild-Lookup / noch kein
  sichtbares Loading wie bei Highlights).
- **Strukturbruch nach Rank 1:** Filterband unterbrechen den Lesefluss; nach
  dem ersten Fundstück folgt sofort Werkzeug-UI statt weiterer Entdeckung.
- **Monotone Liste:** Ränge 02–20 sind nahezu identische Karten – ohne Fotos
  sehr lang und gleichförmig (868 Treffer verstärken das Gefühl).
- **Kein Briefing, aber auch kein visueller Anker** – im Vergleich zu Aktuell
  fehlt ein „Warum diese Reihenfolge?“-Moment.
- **Save-Profile-Prompt** zwischen Kopf und Inhalt addiert eine weitere horizontale
  Zone; auf Mobile stapeln sich viele Bänder.
- **Parität zu Aktuell unvollständig:** Gleiche Komponenten (Tags, Filter,
  Karten), aber anderer Rhythmus – wirkt wie zwei Produkte in einem Skin.

**Bewertung:** Funktional auf dem richtigen Weg, **visuell und emotional noch
nicht auf Augenhöhe mit Aktuell**.

---

### Musikprofil (`/musikprofil`)

**Stärken**

- Drei-Schritte-Fortschritt (Richtungen → Details → Filter) ist klar.
- Genre-Grid mit Mehrfachauswahl und rotem Auswahlzustand ist verständlich.
- Sidebar „Dein Profil“ gibt Orientierung während des Setups.
- Layout ruhig, keine Ablenkung.

**Schwächen**

- Wirkt noch **Formular**, nicht **Musik-Profil-Erlebnis** (keine Künstler- oder
  Stil-Beispiele, keine Vorschau „So könnten deine Empfehlungen aussehen“).
- Visuell abgekoppelt von den Ergebnisseiten – gleiche Tokens, aber wenig
  gemeinsame dramaturgische Elemente.
- Auf Mobile noch nicht separat optimiert geprüft; Grid könnte gedrungen wirken.

**Bewertung:** Solide Basis, **geringes emotionales Gewicht** – akzeptabel für
Wizard, aber nicht für „Wow, das ist mein Musik-Ich“.

---

### Playlists (`/playlists`)

**Stärken**

- Klare Zweispalten-Logik: Eingabe links, Ergebnis rechts („Danach“).
- Formularfelder sind verständlich benannt.
- Passt zur restlichen Typografie und Farbwelt.

**Schwächen**

- Sehr **utility-lastig**; keine Verbindung zu den schönen Ergebnis-Karten.
- Rechte Spalte leer bis zur Generierung – wenig Motivation.
- Kein visueller Bezug zu Aktuell/Entdecken (z. B. „Aus deinen aktuellen
  Highlights“).

**Bewertung:** Für einen Generator ausreichend; **kein Showcase** des neuen
Designs.

---

### Shell, Navigation, Querschnitt

**Stärken**

- Sticky Topbar mit Backdrop-Blur wirkt modern und ruhig.
- PR-Markenzeichen + Wortmarke sind wiedererkennbar.
- Aktiver Nav-Zustand (rote Unterstreichung) ist dezent.
- Farbpalette (Papier, Tinte, gedämpftes Rot, Gold-Akzent) hält die
  Anti-Streaming-App-Linie ein.
- Typografie-Kombination Display-Serif + UI-Sans ist stimmig.

**Schwächen**

- **Mobile Navigation:** Vier Hauptpunkte + Login in einer Zeile wird auf 390px
  gedrängt; kein Hamburger, keine Priorisierung.
- **Marke vs. Produkt:** „PR“-Monogramm ist funktional, aber noch nicht
  ausgereiftes Branding.
- **Einheitliche Seitenbreite** (max ~960px) gut für Lesbarkeit; Highlight-Kacheln
  nutzen die Breite besser als schmale Karten.

---

## Querschnittsthemen

### Künstlerbilder

| Aspekt | Befund |
|--------|--------|
| Technik | On-the-fly über API, nicht abhängig von vorbefülltem `data/`-Ordner |
| Live-Erlebnis | Oft keine sichtbaren Bilder; leere Flächen oder gar keine Foto-Kacheln |
| Ursache (wahrscheinlich) | Langsame sequenzielle Auflösung vieler Künstler; früher ein großer Batch; UI zeigt auf Entdecken erst Kacheln nach bestätigtem Bild |
| Design-Folge | Investition in Layout wird nicht ausgeschöpft |

**Empfehlung:** Bilder als **Produkt-Feature behandeln**, nicht als Dekoration –
mit Ladezuständen, Priorisierung (sichtbare Slots zuerst), Cache-Wahrnehmung und
klaren Fallbacks.

### Informationshierarchie

Was gut priorisiert ist: Artist/Album, Tags, Auszug.  
Was noch zu dominant wirkt: numerischer Score in der Meta-Zeile, Filter-Chips
vor Inhalt auf Entdecken.  
Was fehlt: sprachliche **Passungsbegründung** statt generischem „Passend“ /
„Sehr passend“ (im Code vorbereitet, im UI noch schwach sichtbar).

### Interaktive Platzhalter

- Save-Herz überall sichtbar, aber disabled → Vertrauensproblem.
- Entweder aktivieren (auch minimal: lokale Merkliste) oder visuell zurücknehmen
  bis launch-ready.

### Konsistenz Aktuell ↔ Entdecken

| Element | Aktuell | Entdecken |
|---------|---------|-----------|
| Kopf | Briefing | Klassischer Page-Header |
| Hero | 3 Highlights | Rank 1 (+ geplante Foto-Kacheln) |
| Filter | Nach Highlights | Nach Rank 1 |
| Liste | Dichte Karten | Dichte Karten (+ Foto-Rhythmus) |

Die Unterschiede sind **inhaltlich begründbar**, brauchen aber gemeinsame
Bausteine (Foto-Kachel, Meta-Zeile, Tag-Row), damit es wie ein Produkt wirkt.

---

## Stärken (konsolidiert)

1. **Klare visuelle Identität** – warm, editorial, nicht generisch SaaS.
2. **Aktuell-Highlights** – stärkstes Layout-Element; zeigt die Zielrichtung.
3. **Scanbare Empfehlungskarten** – Rank, Tags, Auszug, Link funktionieren.
4. **Filter-System** – mächtig und für Power-User wertvoll; einklappbar.
5. **Deutsche UI-Copy** – größtenteils natürlich, mit echter Haltung auf Aktuell.
6. **Architektur** – getrennte Seitenlogik (`aktuellPage`, `entdeckenPage`),
  wiederverwendbare `HighlightColumnCard`.
7. **Profil-Wizard** – verständlicher Einstieg für Neulinge.

---

## Schwächen (konsolidiert)

1. **Fotos kommen im UI oft nicht an** – größter Widerspruch zwischen Design und
   Erlebnis.
2. **Zwei Geschwindigkeiten** – editorial oben, Tabellengefühl unten.
3. **Entdecken noch zu monoton** ohne zuverlässige Foto-Kacheln.
4. **Filter- und Banner-Zonen** stapeln sich; erste Bildschirmhöhe zu wenig
   „Musik“.
5. **Mobile Navigation** nicht für kleine Viewports designt.
6. **Deaktivierte Aktionen** (Herz) wirken wie Bugs.
7. **Seiten unterscheiden sich** in Dramaturgie stärker als nötig.
8. **Playlists und Profil** hinken dem neuen Ergebnis-Design hinterher.

---

## Priorisierte nächste Schritte

Die Reihenfolge orientiert sich an Impact vs. Aufwand. Punkte 1–3 sind aus
Designsicht **blockierend**, bevor weiter „kosmetisch“ verfeinert wird.

### 1. Künstlerbilder zuverlässig sichtbar machen (P0)

- Slotweise Laden (bereits begonnen) **plus** sichtbares Loading in Foto-Kacheln
  auf beiden Seiten
- Primär sichtbare Slots zuerst (Rank 1, erste Highlight-Karten)
- Backend: parallele Auflösung im Batch prüfen (sequenziell ist zu langsam für
  5+ Künstler)
- Negative Cache im UI: kein endloses Beige – nach Timeout zurück zur
  Textkarte
- Akzeptanzkriterium: Auf Live-Daten innerhalb weniger Sekunden mindestens ein
  echtes Foto auf Aktuell und Entdecken

### 2. Entdecken-Foto-Rhythmus finalisieren (P0)

- Foto-Kacheln mit gleicher `HighlightColumnCard`-Qualität wie Aktuell
- Klare Regel: nur echte Bilder, kein leeres Beige-Feld in der Liste
- Alternierende Bildseite beibehalten
- Nach Rank-1-Lead: Filter visuell leichter (weniger Rahmen, kompaktere
  Prelude), damit der Einstieg nicht „abbricht“

### 3. Übergang Highlights → Liste auf Aktuell glätten (P1)

- Erste Listeneinträge visuell an Highlights anbinden (z. B. etwas mehr Luft,
  schwächerer Rahmen, optional erste List-Karte als „kleines Highlight“)
- Score in Meta-Zeile weiter zurücknehmen; Passungsbegründung prominenter
- Briefing-CTA auf Mobile unter die Copy, nicht daneben

### 4. Save / Vormerken entscheiden (P1)

- Option A: Minimale lokale Merkliste (Session) aktivieren
- Option B: Herz erst einblenden, wenn Feature ready
- Nicht: überall sichtbare tote Buttons

### 5. Mobile Navigation und erste Bildschirmhöhe (P1)

- Hamburger oder reduzierte Nav auf `<560px`
- Weniger vertikale Bänder vor dem ersten Inhalt (Save-Prompt, Filter)
- Aktuell/Entdecken: Ziel „ein Fundstück ohne Scrollen“ auf Mobile

### 6. Copy- und Begründungsfeinschliff (P2)

- `fitLabel` / Passungstexte weniger generisch (siehe Design-Brief)
- Entdecken: kurzer Satz unter „Alle Empfehlungen“, warum Archiv anders
  sortiert als Aktuell
- Willkommen: ein Satz mit konkretem Nutzen („In 2 Minuten zum ersten Fundstück“)

### 7. Musikprofil und Playlists anbinden (P2)

- Profil: Mini-Vorschau oder Beispiel-Tags nach Schritt 1
- Playlists: Verweis auf letzte Highlights / Top-Archiv-Treffer als Startpunkt
- Gemeinsame Kartenkomponente wo möglich

### 8. Design-Ops (P2)

- Playwright-Screenshots mit **Live-API** und Profil in CI (nicht nur Mock) — umgesetzt
- Referenzscreenshots für Aktuell + Entdecken + Mobile pflegen — umgesetzt
- Kurzes Kapitel in diesem Doc bei größeren Layout-Sprüngen aktualisieren — siehe unten

---

## Design-Ops: Screenshot-Referenzen (Stand 2026-06-28)

### Ziel

Layout-Regressionen auf **Aktuell**, **Entdecken** und **Mobile** früh erkennen — mit
echter API-Anbindung und gesetztem temporären Musikprofil, nicht nur gerouteten Mocks.

### Was läuft in CI

Job `visual-screenshots` in `.github/workflows/ci.yml`:

1. Startet die deterministische Visual-API (`scripts/visual_api_server.py`, Port `8010`)
2. Startet das Frontend mit `VITE_API_BASE_URL=http://127.0.0.1:8010` via `scripts/run_live_screenshots.py`
3. Regeneriert Referenz-PNGs auf Linux, committet sie bei Abweichung automatisch
   (gleiches Repo), und führt danach `frontend-screenshot-live` aus

Abgedeckte Screens:

| Referenzdatei | Route | Viewport |
|---------------|-------|----------|
| `aktuell-live-desktop.png` | `/aktuell` | Desktop 1280×900 |
| `aktuell-live-mobile.png` | `/aktuell` | Mobile 390×844 |
| `entdecken-live-desktop.png` | `/entdecken` | Desktop 1280×900 |
| `entdecken-live-mobile.png` | `/entdecken` | Mobile 390×844 |

Das Profil entspricht dem üblichen temporären Setup (`C001`–`C003`, Score-Filter ab
0.4). Die Fixture-API liefert genug Archiv- und Neuheiten-Daten sowie zwei
Künstlerfotos (The Notwist, Big Thief); ein Highlight bleibt bewusst text-only.

### Lokale Befehle

```bash
hatch run frontend-playwright-install
hatch run frontend-screenshot-live
```

Referenzbilder nach Layout-Änderungen bewusst aktualisieren:

```bash
# Manuell (Actions → "Update visual screenshots") oder lokal mit Docker:
hatch run frontend-screenshot-update-linux
hatch run frontend-screenshot-update
```

Auf dem Base-Repo committet der CI-Job `visual-screenshots` veraltete PNGs
automatisch nach. Nach dem ersten grünen Lauf `git pull`, um den Bot-Commit zu
holen.

Manuelle Mock-Screenshots (Willkommen, Playlists, Redesign-Mock) bleiben unter
`hatch run frontend-screenshot` in `frontend/screenshots/` (gitignored).

### Wann dieses Kapitel aktualisieren

- Neues Highlight- oder Ranking-Layout auf Aktuell/Entdecken
- Mobile-Navigation oder erste Bildschirmhöhe geändert
- Foto-Rhythmus oder Kartenvarianten (text-only vs. Foto-Kachel) angepasst
- Bewusst andere Fixture-Daten für stabilere Screenshots

Dann: Referenz-PNGs regenerieren, kurzen Absatz „Was sich geändert hat“ hier
ergänzen, Datum im Kapiteltitel anpassen.

---

## Was bewusst zurückgestellt werden kann

- Briefing-Header auf Entdecken (bewusst nicht gewünscht)
- Density-Cap für Fotos (bewusst verworfen)
- Große visuelle Experimente (Richtung 2/3 aus dem Layout-Brief) vor P0/P1
- Vollständiger Accessibility-Audit
- Brand-Redesign über das PR-Monogramm hinaus

---

## Kurzfazit

Das neue Layout auf **Aktuell** ist die richtige Design-Richtung: persönlich,
editorial, musiknah. Der Ist-Stand scheitert im Alltag noch an der **Lücke
zwischen Layout-Versprechen und Foto-Realität** und an der **noch unausgebauten
Entdecken-Dramaturgie**.

Die nächsten Implementierungsschritte sollten deshalb nicht primär neue
Layout-Ideen liefern, sondern:

1. Fotos und Ladezustände stabil machen,
2. Entdecken denselben visuellen Standard geben wie Aktuell (mit eigener
   Archiv-Logik),
3. tote UI-Elemente und Mobile-Reibung bereinigen.

Wenn diese drei Blöcke stehen, lohnt sich ein zweiter Feinschliff-Pass für
Typografie, Copy und Playlist/Profil-Anbindung.
