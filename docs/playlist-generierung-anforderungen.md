# Playlist-Generierung — Anforderungen (Nutzerinput)

Status: In Arbeit — Sammlung aus Produktdiskussion  
Datum: 2026-07-02  
Hinweis: Dieses Dokument hält den **Nutzerinput** strukturiert fest, damit nichts im Chat-Kontext verloren geht. Noch **keine** Umsetzung oder Design-Finalisierung.

Verwandte Dokumente:

- [`playlists-evaluierung-2026-06-30.md`](playlists-evaluierung-2026-06-30.md) — abgeschlossene Design-Review der bestehenden Playlist-Seite
- TuneMyMusic-Export bleibt unverändert (bewusste Entscheidung)

---

## Übergeordnetes Ziel

Die Website ist live und funktioniert gut. Der Fokus liegt auf der **Verbesserung bestehender Features**, insbesondere der **Playlist-Generierung**.

Kernabsicht:

- Nutzer sollen Musik nicht nur **schnell finden**, sondern auch **schnell ausprobieren** können.
- Ergebnis: eine Playlist, die sich **leicht in Streaming-Dienste** (Spotify, Deezer, …) übernehmen lässt.
- Der Export über den Zwischendienst **TuneMyMusic** soll **nicht geändert** werden — das ist derzeit der einfachste Weg.
- Verbesserungen betreffen den **Weg dorthin**: schöner, besser, funktionaler.

---

## Scope dieser Diskussion

### Zwei manuelle Modi (heute)

1. **Neuheiten** — Playlist aus den neuesten Reviews (neue Musik)
2. **Archiv** — Playlist aus dem Archiv

### Explizit nicht im Scope (jetzt)

- Automatische Generierung und Versand von Playlists (geplant für die Zukunft)

---

## Modus: Neuheiten (neue Musik)

### Typischer Use Case

Ein Familienmitglied hat nicht genug Zeit, ständig die neuesten Reviews zu lesen. Es gibt ein neues Update von plattentests.de — und jetzt soll **manuell** eine neue Playlist erstellt werden.

### Dimension 1: Zeitraum / Aktualität

Der Nutzer entscheidet, **auf welcher zeitlichen Basis** die Playlist entsteht:

| Option | Beschreibung | Wirkung |
|--------|--------------|---------|
| **Nur letzte Review-Runde** | Playlist basiert nur auf dem neuesten Review-Patch | Wirklich die neueste Musik; Auswahl eher begrenzt; weniger Treffer im eigenen Geschmack — dafür mehr Gelegenheit, **über den eigenen Geschmack hinaus** zu entdecken und den Horizont zu erweitern |
| **Weiter in die Vergangenheit** | Wie weit zurück, entscheidet der Nutzer | Größerer Pool; **Überlappung** mit früheren Review-Runden ist **nicht schlimm** — wiederholtes Hören hilft, die Musik besser kennenzulernen |

### Zufallselement

- Vorgeschlagene Tracks stammen normalerweise aus den **Highlights** der Reviews.
- **Nicht jeder** Highlight-Titel wird übernommen — es gibt eine **zufällige Auswahl** zwischen diesen Highlight-Songs.
- Selbst bei Überlappung in den Playlists (z. B. gleiche Review-Runden) können **andere Tracks desselben Albums** gewählt werden.
- Das wird als **positiv** gesehen (Abwechslung bei wiederholtem Generieren).

### Dimension 2: Geschmacksstärke

Der Nutzer entscheidet, **wie stark** seine persönliche Geschmackspräferenz die Playlist prägt:

| Stärke | Beschreibung | Mögliche Konsequenz |
|--------|--------------|---------------------|
| **Stark an den eigenen Geschmack angepasst** | Playlist soll **sehr gut** zum Geschmack des Nutzers passen | Bestimmte Alben können mit **vielen Titeln** vertreten sein; ggf. nicht nur Highlights, sondern auch **Titel außerhalb der Highlights** |
| **Weit explorieren** | Breitere, explorative Auswahl | Oft **nur ein Track pro Album** in der Playlist |

---

## Modus: Archiv

### Besonderheit gegenüber Neuheiten

Im Archiv gibt es **tausende Alben** mit einem **sehr hohen Gesamt-Score**. Die zentrale Frage ist: **Wie wählt man zwischen diesen aus?**

### Dimension 1: Auswahlbasis (Album-Pool)

Mögliche Steuerungen für den Nutzer — wie groß / wie gut der zugrunde liegende Album-Pool sein soll:

| Option | Beschreibung |
|--------|--------------|
| **Mindest-Score** | Alle Alben, die **mindestens** einen bestimmten Score-Wert haben |
| **Top-N-Alben** | Feste Obergrenzen als Idee, z. B. **Top 500**, **Top 1000** oder **Top 2000** Alben |

*(Konkrete UI, Defaults und ob mehrere Varianten kombinierbar sind — noch offen.)*

### Dimension 2: Album-Verteilung in der Playlist

Zusätzlich soll der Nutzer angeben können, **wie die Playlist zusammengesetzt** sein soll:

| Option | Beschreibung | Wirkung |
|--------|--------------|---------|
| **Alben klar überrepräsentiert** | Bestimmte Alben stehen deutlich im Vordergrund | Mehrere Titel pro Album möglich, z. B. **drei oder vier Stücke** — Nutzer kann sich **stärker mit dem Album** beschäftigen |
| **Ein Song pro Album** | Breite Streuung über viele Alben | Playlist eher als **Überblick / Entdeckung** über viele Alben hinweg |

Diese Album-Verteilungs-Logik ist **konzeptionell verwandt** mit der Geschmacksstärke bei Neuheiten (viele Titel vs. ein Titel pro Album), gilt im Archiv aber im Kontext des **großen Score-Pools**.

---

## Gemeinsam für Neuheiten und Archiv

### Anzahl der Songs in der Playlist

- Der Nutzer soll in **beiden Modi** angeben können, **wie viele Songs** die Playlist enthalten soll.
- **Obergrenze** für die Track-Anzahl: noch **nicht festgelegt**.

### Unterschiedliche Einstellungen je Modus

- **Neuheiten** und **Archiv** haben **jeweils eigene, passende Steuerungen** (siehe oben).
- Die Oberfläche darf dadurch **nicht überladen** wirken — trotz unterschiedlicher Optionen pro Modus.

---

## UX- und Design-Leitplanken (gesamter Playlist-Flow)

Ziel: Der Nutzer soll sich **gehoben** fühlen und **genau wissen**, was er tut.

| Leitplanke | Beschreibung |
|------------|--------------|
| **Klarheit** | Schön und übersichtlich; intuitive Bedienung |
| **Wenig Text** | So wenig Text wie möglich — aber **aufklärend**: jede Anzeige soll dem Nutzer sofort verständlich machen, was zu tun ist |
| **Modus-spezifisch, nicht überfrachtet** | Nur die Einstellungen zeigen, die zum gewählten Modus (Neuheiten / Archiv) passen |
| **Freude am Werkzeug** | Die Nutzung soll **schön**, **intuitiv** und **Spaß** machen — nicht wie ein technisches Export-Tool wirken |
| **Gesamter Weg** | Dieselben Qualitätsansprüche gelten für **Generierung** und für den **Übergang zu TuneMyMusic** (Anleitung, Export-Schritte, Ergebnisdarstellung) |

Technisch bleibt TuneMyMusic der Export-Weg; **Erlebnis und Erklärung** auf unserer Seite sollen deutlich besser werden.

---

## Playlist-Name und Export (Nutzerinput + Ist-Stand)

### Nutzeranforderung

- Der Nutzer soll den **Namen der Playlist eingeben** können.
- **Default-Namen** (Vorschlag des Nutzers), jeweils **mit Datum**:
  - **Neuheiten:** `Plattenradar Neuheiten YYYY-MM-DD`
  - **Archiv:** `Plattenradar Archiv YYYY-MM-DD`
- Frage: Reicht das **Datum allein** für **Idempotenz** (eindeutige, wiedererkennbare Playlists)? → siehe Vorschlag unten.

### Recherche: Playlist-Name über TuneMyMusic

| Exportweg | Playlist-Name übertragbar? | Anmerkung |
|-----------|----------------------------|-----------|
| **CSV-Datei** | **Ja** | TuneMyMusic erwartet Spalten u. a. `Track name`, `Artist name`, **`Playlist name`** — damit landen Titel in einer benannten Playlist im Zieldienst |
| **TXT-Datei** | **Nein** | Format ist nur `Künstler - Titel` pro Zeile; **kein** Namensfeld |
| **Freitext (Copy & Paste)** | **Nein** | Wie TXT: reine Trackliste; der Playlist-Name wird **in TuneMyMusic** beim Import vergeben |

**Fazit:** Automatische Playlist-Benennung im Streaming-Dienst ist nur über **CSV-Upload** zuverlässig möglich. Bei TXT/Freitext dient der Name bei uns vor allem für **Anzeige**, **Download-Dateiname** und Nutzer-Orientierung — im Zieldienst muss der Nutzer den Namen in TuneMyMusic setzen (oder CSV wählen).

### Ist-Stand im Code (Stand Review 2026-07-02)

| Komponente | Verhalten |
|------------|-----------|
| **Backend** (`playlist_export.py`) | CSV korrekt im TuneMyMusic-Format mit `Playlist name`; TXT nur `Artist - Title` |
| **Streamlit** | Namensfeld vorhanden; Default aktuell generisch `Plattenradar YYYY-MM-DD` (noch **nicht** modus-spezifisch) |
| **React-Frontend** | Namensfeld vorhanden; Default `Plattenradar YYYY-MM-DD`; API-Request mit `format: "txt"` |
| **React CSV-Download** | Clientseitig `Artist,Album,Track` — **abweichend** vom TuneMyMusic-CSV des Backends, **ohne** Playlist-Name (Lücke zur Nutzeranforderung) |

*(Noch keine Umsetzung — nur dokumentiert.)*

### Idempotenz: Ist nur das Datum genug?

**Nein, nicht allein** — aus Produkt- und Praxis-Sicht:

| Szenario | Problem mit nur `Plattenradar … YYYY-MM-DD` |
|----------|-----------------------------------------------|
| Zwei Generierungen am **selben Tag**, **gleicher Modus** | Gleicher Default-Name → Kollision / doppelte Playlist im Dienst oder Verwechslung |
| Neuheiten **und** Archiv am selben Tag | Ohne Modus im Namen nicht unterscheidbar |
| Bewusst **neue** Playlist vs. **Ersetzen** | Datum sagt nicht, ob es die 1. oder 3. Liste des Tages ist |

**Vorschlag für Default-Namen (noch nicht umgesetzt):**

1. **Modus im Namen** (Nutzerwunsch): `Plattenradar Neuheiten 2026-07-02` bzw. `Plattenradar Archiv 2026-07-02` — trennt die beiden Modi am selben Tag.
2. **Bei erneuter Generierung am selben Tag** (optional, UX zu klären):
   - Suffix ` (2)`, ` (3)` … **oder**
   - kurze Uhrzeit ` 14:30` **oder**
   - Nutzer passt den Namen manuell an (Feld bleibt editierbar).
3. **In der UI kurz erklären:** Für **automatischen Playlist-Namen** im Streaming-Dienst → **CSV** nutzen; bei **Freitext/TXT** Name in TuneMyMusic eingeben.

**Empfehlung:** Modus + Datum als Default; bei zweiter Generierung am selben Tag mit unverändertem Namen Suffix `(2)` anbieten oder vorausfüllen — so bleibt der Name lesbar und Konflikte werden seltener.

---

## Design-Richtung: Freude ohne Funktionsverlust (Nutzerinput)

### Ausgangslage (Design-Review)

Die Playlist-Seite wirkt aktuell **formal und rein funktional** — sie erfüllt den Job, weckt aber **wenig Freude**. Im Vergleich zu **Aktuell** und **Entdecken** fehlt der emotionale, kuratorische Moment (Kacheln, Fotos, Passung).

### Leitprinzip (explizit vom Nutzer)

> **Funktion zuerst, Design im Dienst der Funktion** — nicht umgekehrt.  
> Solange die Funktion klar bleibt, soll das Erlebnis **so gut wie möglich** sein.

### Design-Vorschlag (Entwurf, noch nicht umgesetzt)

Ziel: **Natürlicher Abschluss** der Entdeckungsreise — nicht „Export-Werkzeug“, sondern „deine Playlist ist fertig“.

#### 1. Formular (vor der Generierung)

- **Eine klare Spalte / ein klarer Flow** — keine leere „Danach“-Sidebar, die nichts tut.
- Modus als **zwei große, verständliche Karten**: „Neuheiten“ / „Archiv“ — darunter nur die passenden Optionen.
- Steuerungen mit **kurzen Labels + einem Satz Hilfe** (z. B. Geschmacksstärke: „Viel von wenigen Alben“ vs. „Breit streuen“).
- Optional: **Mini-Vorschau** (3 Highlight-Kacheln aus dem gewählten Pool) statt leerer Fläche — Vorfreude ohne volle Generierung.

#### 2. Ergebnis (nach der Generierung)

- Statt HTML-Tabelle: **kompakte Track-Liste** im Stil von Aktuell/Entdecken (kleinere Recommendation-Cards).
- **Künstlerfotos** als Kacheln oder neben jedem Track — wo Bilder fehlen, dezenter Platzhalter (wie elsewhere in der App).
- **Kontextzeile** über der Liste: z. B. „30 Titel · Neuheiten · letzte 2 Update-Runden · stark nach Geschmack“.
- Badges: **Highlight** vs. **Albumtrack** (`source_kind`), optional Rating/Passung — Vertrauen ohne Score-Lektion.
- **Primäraktion sichtbar:** Export (Text kopieren / CSV) — danach Details.

#### 3. Künstler-Kacheln (optional, als Akzent)

- **Mosaik aus Künstlerfotos** der Playlist (z. B. 6–12 eindeutige Künstler) — emotionaler „Cover“-Moment für die generierte Liste.
- Nicht jeder Track braucht ein Foto in der Liste; das Mosaik reicht als Stimmungsanker.
- Auf Mobile: kleineres Mosaik oder horizontal scrollbare Reihe.

#### 4. TuneMyMusic-Übergang

- Nach Generierung: **aufklappbare, nummerierte Schritte** (Streamlit-Vorbild).
- Export-Buttons klar gruppiert; Hinweis: **CSV = Playlist-Name automatisch**, **Text = Name in TuneMyMusic**.
- Kurzer Success-Moment nach „Text kopieren“.

#### 5. Was bewusst vermieden wird

- Keine rein dekorative Animationen, die den Export-Flow verzögern.
- Keine Versteckung wichtiger Optionen hinter zu viel „Design“.
- Keine 1:1-Kopie des Streamlit-Layouts — Anbindung an Plattenradar-CI (Aktuell/Entdecken).

---

## Interview-Runde — beantwortet & Entscheidungen

### Block A — Neuheiten: Zeitraum ✅

| # | Frage | Nutzerantwort | Entscheidung (UX / Produkt) |
|---|--------|---------------|-----------------------------|
| **A1** | Steuerung „weiter zurück“ | Unsicher — Update-Runden **oder** Kalender denkbar; Kalender fühlt sich nach **wenig Mehrwert** an → **Entscheidung an UX überlassen** | **Nur Update-Runden** (kein Kalender in v1). Begründung: passt zu plattentests.de-Logik („Update-Runde“), ist auf Aktuell schon etabliert, weniger UI-Komplexität, kein zweites Zeitmodell. Bestehende Stufen **1 / 4 / 8 Runden** beibehalten oder leicht erweitern (z. B. zusätzlich „2 Runden“) — **kein** Kalenderzeitraum. |
| **A2** | Default beim Öffnen | **Nur letzte Runde** | ✅ Übernommen: Default = **1 Update-Runde**. |
| **A3** | Pool-Größe vor Generierung anzeigen? | Unsicher, was „24 Alben“ bedeutet (passend zum Profil vs. alle Veröffentlichungen); funktional **vernachlässigbar** → **Entscheidung an UX überlassen** | **Optional, eine Zeile — nur wenn klar formuliert.** Anzeige bezieht sich auf den **personalisierten Pool** (Alben aus gewählten Runden, die nach Profil/Filter für die Playlist infrage kommen), **nicht** auf die Gesamtzahl aller Neuerscheinungen. Copy-Vorschlag: *„In den letzten 4 Runden: 24 Alben passen zu deinem Profil.“* Keine Album-Liste vor dem Klick (das wäre Vorschau — separates Thema). **Priorität: nice-to-have** (P2); wenn technisch aufwendig, weglassen — Nutzer sieht Mehrwert als gering. |

**Block A — Kurzfassung für Umsetzung:**

- Zeitraum: Dropdown **Update-Runden** (1 / 4 / 8 …), Default **1**
- Kein Kalender in v1
- Pool-Hinweis: optional, eine Zeile, klar „passend zu deinem Profil“

---

### Block B — Geschmack / Verteilung ✅

| # | Frage | Nutzerantwort | Entscheidung (UX / Produkt) |
|---|--------|---------------|-----------------------------|
| **B4** | Gemeinsame Metapher oder getrennt? | **Neuheiten:** „Fokus ↔ Entdecken“ passt gut. **Archiv:** bewusst **anders** — Steuerung über **Top-N** oder **Mindest-Score** (wie viele Alben überhaupt eine Rolle spielen). Gleiche **visuelle Sprache** (eine Komponenten-Familie), aber **nicht** derselbe Begriff/Mechanismus. Top-N eher **kein** Slider; Score-Schwelle **kann** Slider sein, wenn er zur Metrik passt. **„Fokus ↔ Entdecken“ im Archiv kein Sinn:** bei Top-1000 liegen Scores oft dicht beieinander (z. B. 0,90–0,96) — das sind ohnehin ähnlich starke Alben, kein echtes „Entdecken“ über Qualitätsspanne. | **Zwei getrennte Steuerungen im Archiv:** (1) **Album-Pool** — Top-N *oder* Mindest-Score (Details Block C); UI passend zur Metrik: **Presets/Chips** für Top-N (500 / 1000 / 2000), **Slider** für Score mit sinnvollen Stufen/Labels. (2) **Titel pro Album** — eigene, klar benannte Steuerung (z. B. „**Breit streuen**“ ↔ „**Alben vertiefen**“), gleiche visuelle Familie wie Neuheiten-Slider, aber **eigene Copy**. **Neuheiten:** ein Slider **„Fokus ↔ Entdecken“** (ersetzt heutiges „Fokus“-Dropdown + implizite Geschmackslogik). |
| **B5** | Max. Titel pro Album bei starker Ausrichtung / Überrepräsentation | Unentschieden — **Entscheidung an UX**; konkretes Design weniger wichtig als **intuitiv und schön** | **Dynamisch im Algorithmus, für den Nutzer als Endpunkt sichtbar:** Steuerung „breit“ ≈ **max. 1 Titel pro Album**; „vertiefen“ ≈ **bis zu 4 Titel pro Album** (weicher Cap, nicht harte Nutzerzahl). Kein separates Zahlenfeld — die B4-Steuerung reicht. Backend nutzt bestehende Slot-/Gewichtungslogik; Cap 4 verhindert dominante Einzelalben bei 30+ Track-Playlists. |
| **B6** | Button „Nochmal mischen“? | **Ja** — ausdrücklich gewünscht | ✅ **Must-have:** Sekundäraktion nach Generierung (und optional neben Primärbutton): gleiche Einstellungen, **neue Zufallsziehung**, ohne Formular-Reset. |

**Block B — Kurzfassung für Umsetzung:**

| Modus | Steuerung 1 | Steuerung 2 (falls nötig) |
|-------|-------------|---------------------------|
| **Neuheiten** | Slider **Fokus ↔ Entdecken** | — |
| **Archiv** | **Album-Pool:** Top-N (Chips) *oder* Mindest-Score (Slider) — siehe Block C | **Titel pro Album:** „Breit streuen“ ↔ „Alben vertiefen“ (gleiche UI-Familie, andere Labels) |
| **Beide** | Button **„Nochmal mischen“** | Max. ~4 Titel/Album bei „vertiefen“, ~1 bei „breit“ (intern) |

**Produktlogik Archiv (vom Nutzer):** Hohe Score-Dichte im Top-Pool → kein pseudo-„Entdecken“ über Qualität; deshalb **eigene Metaphern** statt Fokus/Entdecken.

---

### Block C — Archiv: Auswahlbasis ✅

| # | Frage | Nutzerantwort | Entscheidung (UX / Produkt) |
|---|--------|---------------|-----------------------------|
| **C7** | Mindest-Score **oder** Top-N — eine Wahl, kombinierbar, oder nur intern? | **Keine starke Meinung** (a/b/c offen) — **klare Empfehlung aus UX-Sicht erwünscht** | **Eine Steuerung in v1: „Top-N aus deinem persönlichen Ranking“** — kein separater Mindest-Score-Slider. Begründung: `overall_score` ist **profilabhängig**; 0,8 bedeutet je nach Nutzer/Filter etwas anderes; die Score-Verteilung im Pool ist unbekannt und oft eng (v. a. bei strengen Filtern). **Top-N auf bereits gefiltertem, geranktem Pool** ist für Nutzer verständlicher als eine abstrakte Score-Schwelle. Mindest-Score höchstens **später** als Experten-Option. |
| **C8** | Top-N-Presets 500 / 1000 / 2000? | **Nicht pauschal** — bei restriktiven Filtern gibt es vielleicht gar nicht 2000 Alben; feste Presets passen schlecht | **Keine festen 500/1000/2000-Presets.** Stattdessen **adaptiver Slider**: Maximum = **Anzahl passender Alben** nach Profil/Filter (`pool_size`). Optional **Schnellwahl-Chips** relativ zum Pool: z. B. **50 · 200 · Alle** (deaktiviert/angepasst, wenn Pool kleiner). Freie Zahleneingabe **ohne** angezeigtes Maximum vermeiden; wenn Eingabe, dann mit sichtbarem Cap: *„max. 347“*. |
| **C9** | Sinnvoller Default? | Eher **Top 200** als Top 1000; Mindest-Score ~0,8 unsicher; **Auswahl hängt von verfügbarer Pool-Größe ab** | Default: **`min(200, pool_size)`** — entspricht API-Default `archive_limit=200` und Nutzer-Tendenz. Bei kleinem Pool (z. B. 45 Alben) Default = 45 (= alle). Kontextzeile: *„347 Alben passen zu deinem Profil — Playlist aus den Top 200.“* |

**Block C — Kurzfassung für Umsetzung:**

| Element | Empfehlung |
|---------|------------|
| **Steuerung** | Slider „**Wie viele Top-Alben?**“ — Bereich ca. **20 … pool_size** (Untergrenze bei sehr kleinem Pool anpassen) |
| **Anzeige** | Immer **Zahl + Pool-Kontext**: *„Top **200** von **347** passenden Alben“* |
| **Schnellwahl** | Chips **50 · 200 · Alle** (relativ, nicht absolut) |
| **Kein** Mindest-Score in v1 | Score-Schwelle intern über Ranking + Filter abgedeckt |
| **Default** | `min(200, pool_size)` |
| **Technik-Hinweis** | UI braucht **pool_size** vor Generierung (z. B. aus Archiv-Empfehlungs-Count oder leichtem API-Feld) — erst dann Slider-Maximum sinnvoll setzen |

**Nutzer-Insight (übernommen):** Visualisierung muss von **tatsächlich verfügbarem Pool** abhängen, nicht von pauschalen Archiv-Zahlen.

---

### Block D — Track-Anzahl ✅

| # | Frage | Nutzerantwort | Entscheidung (UX / Produkt) |
|---|--------|---------------|-----------------------------|
| **D10** | Default-Anzahl | **30 passt**; keine starke Meinung | ✅ **Default = 30** — passt zum Use Case „schnell ausprobieren“ (~1–1,5 h Hören), API/Streamlit/React-Ist, und typischer Playlist-Länge. |
| **D11** | Unter- und Obergrenze | **5 bis 100** klingt nicht schlecht; unsicher wegen Streaming-Limits | ✅ **Bereich 5–100** (API hat bereits `ge=1, le=100`; Untergrenze **5** beibehalten). **Kein hartes Streaming-Limit** im relevanten Bereich: TuneMyMusic Free erlaubt bis **500 Tracks** pro Transfer; Spotify/Deezer/Tidal erlauben deutlich mehr. 100 ist für „Reinhören“ schon lang — als Obergrenze ok, kein Grund höher zu gehen. |
| **D12** | Presets vs. freie Zahl | Keine starke Meinung — **Empfehlung nach Projektkriterien** | **Presets zuerst, feine Eingabe optional** (nicht umgekehrt). |

**Block D — Kurzfassung für Umsetzung:**

| Element | Empfehlung |
|---------|------------|
| **Primär-UI** | Chips **20 · 30 · 50** — Default **30** aktiv |
| **Sekundär** | Link/Chip **„Eigene Anzahl“** → kompaktes Feld oder Stepper (**5–100**, Cap sichtbar) |
| **Nicht** | Nacktes Number-Input (wirkt technisch, wie heute in React) |
| **Nicht** | Reiner Slider 5–100 (unpräzise, wenig Mehrwert) |
| **Kontext** | Kurzer Hinweis unter den Chips, wechselt dezent: *„30 Titel — gut zum Reinhören“* / ab 50: *„Längere Hörsession“* |
| **Validierung** | Wenn Pool kleiner als Wunschanzahl → bestehende Warnung beibehalten/verbessern |

**Begründung (Nutzerkriterien):** Funktion im Vordergrund — drei schnelle, verständliche Wahlen decken 90 % der Fälle ab; Power-Nutzer können 5–100 wählen, ohne die Oberfläche zu überladen. Schön und intuitiv, ohne Design um der Design willen.

---

### Block E — Playlist-Name & Export ✅

| # | Frage | Nutzerantwort | Entscheidung (UX / Produkt) |
|---|--------|---------------|-----------------------------|
| **E13** | Zweite Playlist am selben Tag | **a)** Suffix **`(2)`** | ✅ Bei erneuter Generierung mit gleichem Basisnamen: automatisch **` (2)`**, **` (3)`** … anhängen. Erste Generierung ohne Suffix. Nutzer kann Name weiterhin manuell überschreiben. |
| **E14** | Standard-Export | **a)** CSV empfohlen | ✅ **CSV als Primäraktion** (Playlist-Name automatisch im Zieldienst). **Text kopieren** und TXT-Download sekundär — mit Kurzhinweis: *„CSV = Name automatisch · Text = schneller Paste, Name in TuneMyMusic“*. React-CSV auf TuneMyMusic-Format mit `Playlist name` umstellen (Backend-Vorbild). |
| **E15** | Streaming-Dienst für Anleitung | **Korrektur: generisch** (nicht Deezer/Spotify-spezifisch) | ✅ **Generische TuneMyMusic-Anleitung** — Upload/Freitext, Zieldienst **vom Nutzer in TuneMyMusic gewählt**. Keine dienst-spezifischen Pfade als Default; ein Link zu TuneMyMusic (Upload/Transfer) reicht. |

**Hinweis (Nutzer, Nachsatz ggf. abgeschnitten):** TuneMyMusic **ist** der Streaming-Übertragungsweg — Nutzer lädt Datei/Text bei TuneMyMusic hoch und wählt dort den **Zieldienst** (Deezer, Spotify, …). Unsere UI erklärt den Weg **bis TuneMyMusic** und nennt **Deezer + Spotify** als übliche Ziele — kein direkter API-Export zu Streaming-Diensten.

**Block E — Kurzfassung für Umsetzung:**

- Default-Namen: `Plattenradar Neuheiten|Archiv YYYY-MM-DD`; bei Wiederholung Suffix `(2)` …
- Export-Hierarchie: **CSV zuerst** → Text/TXT
- TuneMyMusic-Anleitung: generisch + **Deezer & Spotify** als Ziel-Beispiele

---

## Interview-Runde — offene Details (Block F–H)

*Block A–E beantwortet. Block F–H folgen.*

### Block F — Design & Ergebnisdarstellung

16. Ergebnis: **volle Recommendation-Cards** (wie Entdecken) oder **schlankere Track-Zeilen** mit kleinem Foto?
17. **Künstler-Mosaik** oben — ja, nein, oder nur bei ausreichend vielen Bildern?
18. Welche Infos pro Track sind **Pflicht**: Künstler, Album, Titel — dazu Rating, Passungstext, Review-Link, Highlight-Badge?
19. Soll eine **Vorschau vor Generierung** (Mini-Kacheln) eingebaut werden, oder reicht das Ergebnis nach Klick?

### Block G — Profil, Einstieg, Mobile

20. Sollen **aktive Profil-Filter** auf der Playlist-Seite sichtbar sein (Chips wie auf Entdecken)?
21. Sprung von **Aktuell/Entdecken** — sollen Einstellungen (Quelle, Zeitraum) **vorausgefüllt und sichtbar** sein?
22. Mobile: Priorität — zuerst **Layout fixen**, dann verschönern — einverstanden?

### Block H — Scope & Priorität

23. Was ist **Must-have für v1** dieser Verbesserung vs. **nice-to-have**?
24. Soll nur das **React-Frontend** verbessert werden, oder parallel **Streamlit**?
25. Gibt es noch einen Punkt, den du **vergessen** haben könntest — z. B. Favoriten, gespeicherte Playlists, Teilen?

---

## Offene Punkte / noch zu ergänzen

- [x] Archiv Auswahlbasis: adaptiver Top-N-Slider (Default min(200, pool)); kein Mindest-Score v1
- [x] Archiv vs. Neuheiten: getrennte Metaphern (Block B)
- [ ] Neuheiten: Slider Fokus ↔ Entdecken; Archiv: Titel-pro-Album-Steuerung
- [ ] „Nochmal mischen“ als Must-have
- [x] Track-Anzahl: 5–100, Default 30, Chips 20/30/50 + optionale Eigene
- [ ] Interview Block E–H: noch offen
- [ ] UX: konkrete UI-Konzepte pro Modus (ohne Überladung)
- [ ] UX: TuneMyMusic-Übergang (Schritte, Copy, visuelle Hierarchie)
- [x] Playlist-Name: modus-Defaults; Suffix (2) bei Mehrfach-Generierung
- [x] Export: CSV primär; TuneMyMusic-Anleitung Deezer + Spotify
- [ ] Export: React-CSV an TuneMyMusic-Format anbinden (Umsetzung)
- [ ] Interview Block F–H: noch offen
- [ ] Weitere Details zu Neuheiten (UI, Defaults, Benennung der Steuerungen)
- [ ] Design: Ergebnisdarstellung (Cards vs. Liste, Künstler-Mosaik, Kontextzeile)
- [ ] Neuheiten Zeitraum: nur Update-Runden (Default 1); Pool-Hinweis optional (P2)

---

## Changelog (Nutzerinput)

| Datum | Inhalt |
|-------|--------|
| 2026-07-02 | Erstfassung: Übergeordnetes Ziel, zwei Modi, Neuheiten (Zeitraum, Zufall, Geschmacksstärke) |
| 2026-07-02 | Archiv: Auswahlbasis (Mindest-Score, Top-N), Album-Verteilung; gemeinsame Track-Anzahl (Obergrenze offen) |
| 2026-07-02 | UX-Leitplanken: klar, intuitiv, wenig aber aufklärender Text; modus-spezifische UI ohne Überladung; TuneMyMusic-Übergang mit einbeziehen; Nutzung soll Freude machen |
| 2026-07-02 | Playlist-Name: Nutzereingabe; Defaults Neuheiten/Archiv + Datum; Recherche TXT vs. CSV (Name nur in CSV); Idempotenz-Vorschlag (Modus + Datum + optional Suffix) |
| 2026-07-02 | Design-Richtung: Freude ohne Funktionsverlust; Entwurf (Cards, Fotos, Mosaik, Export-Flow); Interview-Runde Block A–H |
| 2026-07-02 | Interview Block A: Default 1 Runde; UX-Entscheid nur Update-Runden (kein Kalender); Pool-Hinweis optional, „passend zu Profil“ |
| 2026-07-02 | Interview Block B: Neuheiten Fokus↔Entdecken; Archiv getrennt (Pool Top-N/Score + Titel/Album); Cap ~4 dynamisch; „Nochmal mischen“ ja |
| 2026-07-02 | Interview Block C: adaptiver Top-N-Slider (pool_size); Default min(200,pool); Chips 50/200/Alle; kein Mindest-Score v1 |
| 2026-07-02 | Interview Block D: 5–100, Default 30; Chips 20/30/50 + optionale Eigene; TuneMyMusic bis 500 ok |
| 2026-07-02 | Interview Block E: Suffix (2); CSV primär; TuneMyMusic-Anleitung Deezer + Spotify |
