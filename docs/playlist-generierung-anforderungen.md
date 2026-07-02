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

---

## Offene Punkte / noch zu ergänzen

- [ ] Archiv: konkrete UI für Auswahlbasis (Score-Schwelle vs. Top-N; kombinierbar?)
- [ ] Archiv: Benennung und Abgrenzung Album-Verteilung vs. Geschmacksstärke bei Neuheiten
- [ ] Track-Anzahl: Default und Obergrenze
- [ ] Weitere Details zu Neuheiten (UI, Defaults, Benennung der Steuerungen)
- [ ] Abgleich mit bestehender Implementierung und Design-Review

---

## Changelog (Nutzerinput)

| Datum | Inhalt |
|-------|--------|
| 2026-07-02 | Erstfassung: Übergeordnetes Ziel, zwei Modi, Neuheiten (Zeitraum, Zufall, Geschmacksstärke) |
| 2026-07-02 | Archiv: Auswahlbasis (Mindest-Score, Top-N), Album-Verteilung; gemeinsame Track-Anzahl (Obergrenze offen) |
