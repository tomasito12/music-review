# Plattenradar Designrunde: Layout-Befunde

Status: Working draft  
Datum: 2026-06-27  
Screenshot-Basis: `frontend/screenshots/`

Dieses Dokument sammelt die ersten Layout-Befunde für die nächste Designrunde von
Plattenradar.de. Es bewertet den aktuellen Frontend-Stand aus Produktsicht: Was
funktioniert bereits, was wirkt noch amateurhaft oder zu generisch, und welche
Richtung sollte ein Neulayout verfolgen?

## Screenshot-Set

Die aktuelle Runde basiert auf diesen Screenshots:

- `frontend/screenshots/willkommen.png`
- `frontend/screenshots/musikprofil.png`
- `frontend/screenshots/aktuell.png`
- `frontend/screenshots/entdecken.png`
- `frontend/screenshots/playlists.png`
- `frontend/screenshots/entdecken-mobile.png`

Erzeugt mit:

```shell
PLAYWRIGHT_BASE_URL=http://127.0.0.1:5174 hatch run frontend-screenshot
```

## Kurzfazit

Das aktuelle Layout ist solide, lesbar und deutlich besser als ein roher
Prototyp. Es hat eine ruhige Farbwelt, gute typografische Ansätze und eine klare
Navigation. Es wirkt aber noch zu sehr wie ein gut gemeintes App-Template:
rechteckige Karten, viel ungenutzter Weißraum, wenig editorialer Rhythmus, wenig
visuelle Überraschung und kaum musikalische Atmosphäre.

Die wichtigste Designaufgabe ist deshalb nicht "mehr Dekoration", sondern eine
stärkere visuelle Dramaturgie: Plattenradar sollte sich weniger wie ein
Formular-/Dashboard-Frontend und mehr wie ein kuratierter Einstieg in Musik
anfühlen.

## Was Bereits Gut Funktioniert

### Klare Grundstruktur

Die Hauptnavigation ist verständlich: `Aktuell`, `Entdecken`, `Playlists` und
`Musikprofil` bilden eine nachvollziehbare Informationsarchitektur. Man versteht
schnell, welche Bereiche das Produkt anbietet.

### Ruhige, warme Basis

Die gebrochene Papierfarbe, das dunkle Blau-Schwarz und der rote Akzent geben
dem Produkt eine erwachsene, nicht grelle Grundstimmung. Das passt besser zu
Plattentests, Archiv, Rezensionen und Musikentdeckung als ein sehr buntes
Streaming-App-Design.

### Gute typografische Richtung

Die Serifenschrift in den großen Überschriften ist eine gute Entscheidung. Sie
verschiebt die Anmutung weg vom reinen Software-Tool und näher an Magazin,
Feuilleton und Rezension.

### Onboarding Ist Verständlich

Der Einstieg erklärt in wenigen Sätzen, warum ein Musikprofil gebraucht wird.
Die Call-to-Action ist klar und nicht überladen. Das Profil-Setup zeigt außerdem
gut, dass Plattenradar zuerst grobe Richtungen und dann detailliertere Stile
abfragt.

### Mobile Basis Ist Stabil

Die mobile Ansicht bricht nicht auseinander. Abstände, Button-Größen und
Lesbarkeit sind grundsätzlich okay. Das ist eine gute technische Grundlage für
die nächste Layout-Iteration.

## Was Noch Nicht Gut Funktioniert

### Zu Viel Gleichförmiger Weißraum

Viele Seiten bestehen aktuell aus einem Header, einer einzelnen Karte und sehr
viel leerer Fläche. Das wirkt unfertig, obwohl die UI technisch sauber ist. Auf
Desktop entsteht dadurch der Eindruck, dass dem Produkt Inhalt oder Haltung
fehlt.

Besonders auffällig ist das auf `Aktuell`, `Entdecken` und `Playlists`, solange
noch kein Profil vorhanden ist. Alle drei Seiten nutzen fast dieselbe
rechteckige Gate-Karte. Das ist verständlich, aber visuell sehr monoton.

### Die Startseite Hat Zu Wenig Bühne

Der Willkommen-Screen hat gute Copy, aber keine starke visuelle Komposition. Der
Textblock steht links oben im Raum, ohne Gegengewicht, ohne redaktionelles
Element und ohne klares Gefühl von "hier beginnt eine Musikreise".

Dadurch fühlt sich die Seite sachlich und korrekt an, aber noch nicht wie eine
Website, die neugierig auf Alben macht.

### Die Marke Wirkt Noch Generisch

Das runde `PR`-Logo ist funktional, aber austauschbar. Zusammen mit der sehr
klassischen Topbar entsteht eher der Eindruck einer frühen SaaS-App als einer
eigenständigen Musikmarke.

Das muss nicht zwingend ein großes Logo-Projekt werden. Schon eine mutigere
Wortmarke, eine charakteristischere Header-Komposition oder ein prägnanteres
typografisches Motiv könnten helfen.

### Karten Und Panels Sind Zu Sehr Standard-UI

Das Profil-Setup, die Gate-Zustände und die geplanten Ergebnislisten arbeiten
viel mit Boxen, Borders und gleichmäßigen Grids. Das ist sauber, aber noch nicht
besonders. Es fehlt eine gestalterische Idee, die aus den Daten etwas
Kuratierteres macht.

Gerade bei Empfehlungen sollte eine Karte nicht nur Daten anzeigen, sondern Lust
auf ein Album machen. Ohne Cover braucht Plattenradar dafür stärkere
typografische Karten, bessere Rang-Dramaturgie, Zitate, Akzentflächen,
redaktionelle Gruppierungen oder andere visuelle Ersatzmaterialien.

### Das Produkt Zeigt Noch Zu Viel Mechanik

Begriffe wie Score, Passung, Filter, Gewichtung und Ranking sind nützlich, aber
sie können schnell nach Daten-Tool klingen. Die aktuelle UI macht diese Mechanik
noch relativ sichtbar. Für Musikfans sollte stärker im Vordergrund stehen:
"Warum könnte mich das interessieren?" und "Worauf soll ich als Nächstes
klicken?"

### Die Navigation Ist Klar, Aber Noch Nicht Charaktervoll

Die Topbar ist lesbar und praktisch. Sie wirkt aber sehr konventionell:
Logo links, Links mittig, Konto rechts. Das ist nicht falsch, trägt aber kaum
zur Identität bei. Auf Mobile nimmt die Navigation relativ viel Raum ein und
fühlt sich schon früh etwas gedrängt an.

### Profil-Setup Wirkt Noch Nach Formular

Die Stilrichtungsauswahl ist verständlich, aber die Kacheln sind sehr neutral.
Für eine Musikseite könnten die Richtungen stärker wie kuratierte Kapitel
wirken: mit kurzen Beschreibungen, Beispielen, Tonalität oder einer
visuellen Gewichtung nach Wichtigkeit.

## Diagnose

Der aktuelle Stand hat ein gutes Informationsdesign, aber noch kein starkes
Art-Direction-System. Die UI beantwortet gut, was man tun kann. Sie beantwortet
noch weniger gut, wie sich Plattenradar anfühlt.

Das Amateurhafte kommt vermutlich nicht von einzelnen schlechten Details,
sondern aus der Summe dieser Muster:

- zu viele gleichartige Rechtecke,
- zu wenig visuelle Spannung zwischen großen und kleinen Elementen,
- zu wenig bewusst gesetzte Asymmetrie,
- zu wenig musikbezogene Textur oder Editorialität,
- zu wenig Unterschied zwischen Onboarding-, Gate- und Ergebniszuständen,
- zu wenig "Hero"-Momente für die eigentliche Empfehlung.

## Richtung Für Das Neulayout

### 1. Mehr Magazin, Weniger Dashboard

Plattenradar sollte die Rezension als redaktionelles Material behandeln. Ohne
Albumcover können Typografie, Review-Auszüge, Rankingzahlen, Quellenhinweise und
Stil-Tags die visuelle Hauptrolle übernehmen.

Mögliche Leitidee:

> Eine persönliche Musikspalte, die täglich neue Fundstücke aus dem
> Plattentests-Archiv nach vorne holt.

### 2. Stärkere Seiten-Dramaturgie

Jede Hauptseite sollte einen eigenen visuellen Zweck haben:

- `Willkommen`: große Bühne, klare Produktidee, emotionaler Einstieg.
- `Aktuell`: tägliche oder wöchentliche Auswahl, fast wie eine persönliche
  Ausgabe.
- `Entdecken`: Archiv-Explorer, tiefer und sammlerischer.
- `Playlists`: handlungsorientiert, näher an "jetzt hören".
- `Musikprofil`: Werkstatt, aber mit mehr Musikgefühl als Formulargefühl.

### 3. Weniger Leere Gate-Zustände

Die Zustände ohne Profil sollten nicht wie leere Fehlseiten wirken. Sie könnten
als Teaser funktionieren:

- kurze Erklärung, was nach dem Profil sichtbar wird,
- Beispiel für eine Empfehlungskarte,
- kleine Liste möglicher Fundstücke oder Stilrichtungen,
- klarer nächster Schritt.

### 4. Empfehlungskarten Als Zentrales Designobjekt

Die Empfehlungskarte sollte das wichtigste Layout-Element werden. Sie muss ohne
Cover stark genug sein. Zu testen wären:

- größere Album-/Artist-Typografie,
- Ranking als grafisches Element statt kleiner Nebeninformation,
- Review-Auszug prominenter,
- Fit-Signal als verständliche Begründung statt nur Score,
- Tags als rhythmisches Element,
- stärkere Unterscheidung zwischen Top-Fundstücken und der vollständigen Liste.

### 5. Mehr Charakter In Der Marke

Die Marke braucht ein wiedererkennbares Motiv. Das kann typografisch gelöst
werden, ohne Icons oder Bildmaterial zu brauchen:

- eine mutigere Wortmarke,
- ein charakteristischer Umgang mit Nummern und Rankings,
- rote Linien oder Stempel-artige Akzente,
- editorialere Zwischenüberschriften,
- eine bewusstere Kombination aus Serif und Sans.

## Offene Fragen Für Die Designrunde

- Soll Plattenradar eher wie ein Musikmagazin, ein persönlicher Scout oder ein
  Archivwerkzeug wirken?
- Wie prominent darf Plattentests als Quelle im Layout auftreten?
- Welche Information überzeugt am meisten zum Reinhören: Review-Auszug,
  Stil-Tags, Passungsbegründung, Wertung oder Neuheit?
- Wie viel Ranking ist motivierend, bevor es zu technisch wirkt?
- Braucht die Startseite dauerhaft eine eigene Bühne, oder ist sie nur ein
  Einstieg für neue Nutzer?
- Welche Seiten sollen bewusst ruhig bleiben, und welche brauchen mehr visuelle
  Energie?

## Nächste Designschritte

1. Drei alternative Layout-Richtungen skizzieren: `Magazin`, `Radar/Scout`,
   `Archiv`.
2. Für jede Richtung zuerst die Empfehlungskarte entwerfen, nicht die komplette
   App.
3. Danach eine starke `Aktuell`-Seite als Referenzscreen bauen.
4. Erst anschließend Navigation, Profil-Setup und Playlists an diese Richtung
   angleichen.
5. Die leeren Zustände separat gestalten, damit sie nicht wie unfertige Seiten
   wirken.

## Arbeitsnotiz

Die aktuelle UI sollte nicht verworfen werden. Sie ist als funktionale Grundlage
wertvoll. Die nächste Runde sollte vor allem eine stärkere visuelle Sprache
darüberlegen: mehr Rhythmus, mehr Editorialität, mehr Musikgefühl und weniger
generische App-Boxen.
