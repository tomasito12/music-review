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

## Interview-Runde — offene Details

*Die folgenden Fragen sammeln Lücken, bevor Design oder Implementierung starten. Antworten können schrittweise in dieses Dokument einfließen.*

### Block A — Neuheiten: Zeitraum

1. Wie soll „weiter in die Vergangenheit“ **konkret** steuerbar sein — Anzahl **Update-Runden** (wie heute), **Kalenderzeitraum**, oder beides?
2. Was ist der **sinnvolle Default** — nur letzte Runde oder z. B. die letzten 2–3 Runden?
3. Soll der Nutzer **sehen**, wie viele Alben/Tracks im gewählten Zeitraum verfügbar sind, bevor er generiert?

### Block B — Neuheiten & Archiv: Geschmack / Verteilung

4. Sollen **Geschmacksstärke** (Neuheiten) und **Album-Verteilung** (Archiv) als **eine gemeinsame UI-Metapher** erscheinen (z. B. Slider „Fokus ↔ Entdecken“) oder bewusst getrennt benannt bleiben?
5. Bei „stark nach Geschmack“: Wie viele Titel pro Album sind **realistisch maximal** (3–4 fest, oder dynamisch)?
6. Soll es einen expliziten Button **„Nochmal mischen“** geben (gleiche Einstellungen, neue Zufallsziehung)?

### Block C — Archiv: Auswahlbasis

7. **Mindest-Score** und **Top-N** — soll der Nutzer **eine** Methode wählen, oder sollen beide kombinierbar sein?
8. Falls Top-N: welche Presets sind dir wichtig — 500 / 1000 / 2000, oder freie Eingabe?
9. Gibt es einen **Mindest-Score**, den du fachlich als sinnvollen Default hättest (z. B. nur „sehr gute“ Alben)?

### Block D — Track-Anzahl & Defaults

10. **Default-Anzahl** Tracks pro Playlist — 20, 30, 50?
11. **Obergrenze** — eher 50 (Streamlit), 100 (React heute), oder anderer Wert? Warum?
12. Presets (20 / 30 / 50) statt freier Zahl — ja oder nein?

### Block E — Playlist-Name & Export

13. Bei zweiter Generierung am selben Tag: bevorzugst du Suffix **`(2)`**, **Uhrzeit**, oder **manuelle Pflicht**?
14. Soll **CSV** der empfohlene Standard-Export sein (wegen Playlist-Name), mit TXT als Alternative?
15. Welcher **Streaming-Dienst** ist für deine Zielgruppe primär (Deezer, Spotify, …) — für TuneMyMusic-Anleitung und Link?

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

- [ ] Archiv: konkrete UI für Auswahlbasis (Score-Schwelle vs. Top-N; kombinierbar?)
- [ ] Archiv: Benennung und Abgrenzung Album-Verteilung vs. Geschmacksstärke bei Neuheiten
- [ ] Track-Anzahl: Default und Obergrenze
- [ ] UX: konkrete UI-Konzepte pro Modus (ohne Überladung)
- [ ] UX: TuneMyMusic-Übergang (Schritte, Copy, visuelle Hierarchie)
- [ ] Playlist-Name: modus-spezifische Defaults; Idempotenz-Suffix bei Mehrfach-Generierung
- [ ] Export: React-CSV an TuneMyMusic-Format anbinden (Playlist name); TXT-Grenze in UI kommunizieren
- [ ] Weitere Details zu Neuheiten (UI, Defaults, Benennung der Steuerungen)
- [ ] Design: Ergebnisdarstellung (Cards vs. Liste, Künstler-Mosaik, Kontextzeile)
- [ ] Interview-Runde: offene Fragen in Block A–H klären

---

## Changelog (Nutzerinput)

| Datum | Inhalt |
|-------|--------|
| 2026-07-02 | Erstfassung: Übergeordnetes Ziel, zwei Modi, Neuheiten (Zeitraum, Zufall, Geschmacksstärke) |
| 2026-07-02 | Archiv: Auswahlbasis (Mindest-Score, Top-N), Album-Verteilung; gemeinsame Track-Anzahl (Obergrenze offen) |
| 2026-07-02 | UX-Leitplanken: klar, intuitiv, wenig aber aufklärender Text; modus-spezifische UI ohne Überladung; TuneMyMusic-Übergang mit einbeziehen; Nutzung soll Freude machen |
| 2026-07-02 | Playlist-Name: Nutzereingabe; Defaults Neuheiten/Archiv + Datum; Recherche TXT vs. CSV (Name nur in CSV); Idempotenz-Vorschlag (Modus + Datum + optional Suffix) |
| 2026-07-02 | Design-Richtung: Freude ohne Funktionsverlust; Entwurf (Cards, Fotos, Mosaik, Export-Flow); Interview-Runde Block A–H |
