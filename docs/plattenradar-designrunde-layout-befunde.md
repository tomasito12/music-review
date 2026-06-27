# Plattenradar Designrunde: Layout-Befunde

Status: Working draft  
Datum: 2026-06-27  
Screenshot-Basis: `frontend/screenshots/`

Dieses Dokument sammelt die ersten Layout-Befunde für die nächste Designrunde von
Plattenradar.de. Es bewertet den aktuellen Frontend-Stand aus Produktsicht: Was
funktioniert bereits, was wirkt noch amateurhaft oder zu generisch, und welche
Richtung sollte ein Neulayout verfolgen?

## Design-Brief

### Zielgefühl

Plattenradar soll sich nach Musikentdeckung anfühlen: neugierig, lebendig,
persönlich und indie-nah. Die Seite darf mehr Energie und Haltung zeigen als der
aktuelle Stand, soll aber nicht laut, überladen oder beliebig werden.

Leitmotiv:

> Die Funktionalität steht. Jetzt sorgen wir dafür, dass es auch Spaß macht, das
> Tool zu nutzen.

### Produktversprechen

Plattenradar hilft Musikfans, gute Alben zu finden, die zu ihnen passen und
sonst leicht unter dem Radar bleiben. Besonders wichtig ist das Gefühl, dass
vergessene oder kurz beachtete Alben wieder hörbar werden.

Nach zehn Sekunden soll ungefähr hängen bleiben:

> Hier gibt es viele gute Alben, die ich noch nicht kenne, die aber wirklich zu
> mir passen könnten.

### Harte Prioritäten

- Funktion vor Optik, wenn es einen echten Trade-off gibt.
- Scanbarkeit vor reiner Atmosphäre.
- Wenig Umständlichkeit: möglichst wenig unnötige Klicks.
- Desktop zuerst, Mobile vorerst sauber und brauchbar halten.
- Bildloses Design muss stark funktionieren; Bilder sind ein mögliches späteres
  Enhancement, keine Voraussetzung.

### Ton Und Haltung

Die Oberfläche soll nach einem Musikfan mit Haltung klingen, der andere
Musikfans als Freunde betrachtet. Die Copy soll weniger generisch und weniger
KI-glatt wirken: musiknah, neugierig, freundlich, klar, aber nicht bemüht cool.

### Visuelle Leitplanken

- Indie, aber sorgfältig.
- Editorial, aber nicht Hochkultur.
- Professionell, aber nicht corporate.
- Persönlich, aber nicht künstlich.
- Energetisch, aber nicht marktschreierisch.

### Anti-Patterns

- Keine Portal-Überladung wie bei klassischen Musikseiten.
- Keine billige Lautstärke durch zu grelle Badges, Rankings oder CTA-Flächen.
- Keine Streaming-App-Optik.
- Kein Blog-Gefühl.
- Kein trockenes Archiv- oder Datenbankgefühl.
- Keine Navigation, die zugunsten von Charakter unklarer wird.

### Erster Referenzscreen

Der erste neue Referenzscreen sollte `Aktuell` sein. Dort treffen die wichtigsten
Designfragen zusammen: persönliche Rückkehrer-Ansprache, neue Rezensionen,
Top-Empfehlungen, Empfehlungskarten, Dichte, Ranking, Score, Review-Auszug und
perspektivisch Vormerken/Playlist.

## Layout-Richtungen

Die folgenden Richtungen sind keine fertigen Designs, sondern mögliche
Entwurfsrahmen. Sie können kombiniert werden, sollten aber zuerst getrennt
gedacht werden, damit die Unterschiede sichtbar bleiben.

### Richtung A: Indie Editorial

Plattenradar wirkt wie eine reduzierte, bildarme Musikmagazin-Seite: starke
Typografie, gute Überschriften, klare Abschnitte, hochwertige Textauszüge und
bewusst gesetzte Akzentflächen. Die Musik steht als redaktionelles Fundstück im
Vordergrund.

Stärken:

- Passt gut zum Qualitätswunsch und zur Referenz `visions.de`.
- Kann auch ohne Bilder funktionieren, wenn Typografie und Textauszüge stark
  genug sind.
- Hilft, die aktuelle App-Template-Wirkung zu überwinden.

Risiken:

- Kann zu hochkulturell oder zu magazinig wirken.
- Kann zu textlastig werden, wenn die Scanbarkeit nicht hart geprüft wird.

Geeignet für:

- Top-Empfehlungen auf `Aktuell`.
- Review-Auszüge als neugierig machende Teaser.
- Eine stärkere, weniger generische Textstimme.

### Richtung B: Personal Radar

Plattenradar wirkt wie eine persönliche Musikmeldung: "Schön, dass du zurück
bist, hier ist neu, was zu dir passen könnte." Der Screen erklärt den aktuellen
Review-Batch, hebt Nähe zum Musikprofil hervor und macht nächste Aktionen leicht.

Stärken:

- Trifft die Entscheidung, dass `Aktuell` die eigentliche Home-Seite für
  Rückkehrer ist.
- Macht Personalisierung sichtbarer.
- Funktioniert gut für E-Mail-Rückkehrer und später Mobile.

Risiken:

- Kann künstlich wirken, wenn die Ansprache zu pseudo-persönlich wird.
- Braucht gute Copy-Logik für Fälle mit wenigen oder schwachen Treffern.

Geeignet für:

- `Aktuell` als ersten Referenzscreen.
- Begrüßung, Zeitraum, Batch-Zusammenfassung und Top-Fundstücke.
- Spätere Erfassung des Vornamens, falls die persönliche Ansprache ausgebaut
  wird.

### Richtung C: Fundstück-Archiv

Plattenradar wirkt wie ein gut kuratiertes, schnelles Stöberwerkzeug für
vergessene gute Alben. Die Oberfläche bleibt dichter und stärker listenartig,
aber bekommt mehr Rhythmus, bessere Karten und eine weniger trockene Sprache.

Stärken:

- Respektiert, dass die Funktion und das Finden von Musik im Vordergrund stehen.
- Passt gut zu `Entdecken` und zur gewünschten Desktop-Dichte.
- Vermeidet zu große Einzelkarten und hält viele Treffer erfassbar.

Risiken:

- Kann wieder zu archivisch oder nüchtern werden.
- Braucht klare visuelle Hierarchie, damit es nicht nach Datenbank aussieht.

Geeignet für:

- `Entdecken`.
- Normale Empfehlungslisten mit vielen ähnlich passenden Treffern.
- Vier bis sechs erfassbare Empfehlungen pro Desktop-Blickfeld.

### Vorläufige Empfehlung

Für den ersten Entwurf sollte `Personal Radar` die Hauptstruktur liefern,
ergänzt durch `Indie Editorial` für die hervorgehobenen Top-Empfehlungen und
`Fundstück-Archiv` für die normale Liste. So entsteht ein `Aktuell`-Screen, der
persönlich startet, musikalische Neugier erzeugt und trotzdem scanbar bleibt.

## Aktuell-Redesign-Plan

### Ziel Des Referenzscreens

`Aktuell` wird die erste neu gestaltete Referenzseite. Sie soll zeigen, wie sich
Plattenradar als Produkt nach dem Redesign anfühlt: persönlich, neugierig,
indie-nah und deutlich weniger generisch, aber weiterhin schnell scanbar und
funktional.

Der Screen soll beantworten:

- Was ist seit dem letzten Zeitraum neu?
- Wie nah liegen die neuen Rezensionen an meinem Musikprofil?
- Welche zwei bis drei Alben sollte ich mir zuerst anschauen?
- Welche weiteren Empfehlungen kann ich schnell überfliegen?
- Was kann ich direkt tun: Rezension öffnen, vormerken, Playlist vorbereiten?

### Nicht-Ziele Für Den Ersten Entwurf

- Kein vollständiges Redesign der gesamten App.
- Keine finale Mobile-Strategie.
- Keine rechtlich unsichere Cover-Nutzung.
- Keine neue Bildpipeline als Voraussetzung.
- Keine komplette Neuentwicklung der Empfehlungslogik.
- Keine optische Lösung, die Ranking oder Score wichtiger macht als Musik und
  Neugier.

### Seitenstruktur

Der neue `Aktuell`-Screen sollte aus fünf klaren Bereichen bestehen.

1. Persönliches Briefing

Der Einstieg ersetzt die nüchterne Ergebnis-Überschrift durch eine persönliche
Kurzmeldung. Beispielrichtung:

> Schön, dass du zurück bist. In den letzten zwei Wochen sind 28 neue Rezensionen
> dazugekommen. Drei davon liegen ziemlich nah an deinem Musikprofil.

Der Text soll je nach Datenlage variieren:

- Gute Treffer: "Hier sind die stärksten neuen Fundstücke für dich."
- Wenige Treffer: "Nicht viel lag diesmal genau auf deiner Linie, aber diese
  Alben könnten sich lohnen."
- Keine starken Treffer: "Diesmal gab es keine sicheren Treffer. Wenn du etwas
  Neues ausprobieren möchtest, starte hier."

2. Batch-Zusammenfassung

Direkt unter dem Briefing sollte eine kurze, scanbare Zusammenfassung stehen:

- Zeitraum, zum Beispiel `letzte 2 Wochen`.
- Anzahl neuer Rezensionen.
- Anzahl relevanter Treffer.
- Optional: Nähe zum Profil als sprachliches Signal, nicht als dominanter Score.

Das Ziel ist Orientierung, nicht Statistik-Dashboard.

3. Top-Fundstücke

Zwei bis drei Empfehlungen werden als hervorgehobene Karten inszeniert. Diese
Karten dürfen größer und editorialer sein als die normale Liste.

Inhaltliche Priorität:

- Artist und Album.
- Stil-Tags, die den Bezug zum Profil zeigen.
- Review-Auszug mit maximal etwa zwei Sätzen.
- Kurze Passungsbegründung.
- Sekundärer Score oder Nähe-Indikator.
- Aktionen: Rezension öffnen, vormerken.

Top-Fundstücke sollen nicht wie Siegerplätze wirken. Sie sind eher persönliche
Startpunkte: "Hier lohnt sich der erste Klick."

4. Normale Empfehlungsliste

Unter den Top-Fundstücken folgt eine dichtere, gut scanbare Liste der weiteren
Empfehlungen. Diese Liste übernimmt die `Fundstück-Archiv`-Logik:

- mehrere Treffer pro Blickfeld erfassbar,
- Artist/Album stark,
- Tags und Auszug sichtbar,
- Rang und Score dezent,
- klare Aktionen ohne Überladung.

Zielgröße für Desktop: ungefähr vier bis sechs Empfehlungen im sichtbaren
Bereich erfassbar, abhängig von Viewport und Top-Bereich.

5. Werkzeugleiste Und Filter

Zeitraum, Filterzusammenfassung und Profilanpassung bleiben erreichbar, sollen
aber nicht den Einstieg dominieren.

Empfohlene Richtung:

- Zeitraum als kompakte Auswahl im Briefing- oder Toolbar-Bereich.
- Filterchips als Statuszeile.
- Detaillierte Filter weiterhin einklappbar.
- Profilbearbeitung sichtbar, aber nicht lauter als die Empfehlungen.

### Empfehlungskarten

Die Kartenhierarchie wird angepasst.

Primär:

- Artist.
- Album.
- Stil-Tags.
- Review-Auszug.

Sekundär:

- Passungsbegründung.
- Wertung.
- Review-Jahr oder Veröffentlichungsjahr, falls verfügbar.
- Score.
- Rang oder Listenposition.

Aktionen:

- `Rezension öffnen` bleibt Pflicht.
- `Vormerken` wird als neue Produktidee im Layout vorbereitet.
- `Zur Playlist hinzufügen` kann später aus `Vormerken` entstehen und muss im
  ersten visuellen Entwurf nicht vollständig implementiert sein.

Der Score darf sichtbar bleiben, aber nicht als Hauptargument. Eine gute Karte
soll eher sagen: "Das klingt nach dir", nicht: "Score 0.87".

### Passungsbegründung

Die aktuelle Passung wirkt noch zu generisch. Für den ersten Entwurf sollte sie
sprachlich konkreter werden, auch wenn die Logik zunächst einfach bleibt.

Mögliche Muster:

- "Trifft mehrere deiner ausgewählten Stilrichtungen."
- "Nahe an deinem Profil, aber mit etwas mehr Experiment."
- "Passt wegen `Post-Punk`, `Noise Rock` und hoher Wertung."
- "Nicht ganz dein Zentrum, aber ein interessanter Ausreißer."

Wichtig: Die Begründung soll hilfreich klingen, nicht wie Modellmechanik.

### Copy-Richtung

Die Copy ist Teil des Redesigns. Sie soll weniger dröge und weniger generisch
sein.

Zielton:

- musiknah,
- freundlich,
- neugierig,
- direkt,
- mit Haltung,
- nicht künstlich kumpelhaft,
- nicht werblich.

Zu vermeiden:

- "Empfehlungen werden anhand deines Profils berechnet."
- "Hier sind deine Top-Scores."
- "Optimiere deine Präferenzen für bessere Resultate."

Besser:

- "Neue Rezensionen, die nah an deinem Geschmack liegen."
- "Ein paar Fundstücke sind diesmal ziemlich nah dran."
- "Nicht dein sicherstes Terrain, aber vielleicht genau deshalb spannend."

### Visuelle Richtung

Für `Aktuell` wird eine Kombination empfohlen:

- `Personal Radar` für Briefing und Rückkehrer-Ansprache.
- `Indie Editorial` für die zwei bis drei Top-Fundstücke.
- `Fundstück-Archiv` für die normale Empfehlungsliste.

Konkrete visuelle Maßnahmen:

- stärkere typografische Hierarchie im Briefing,
- weniger gleichförmige Boxen,
- Top-Karten mit anderer Geometrie oder stärkerer Fläche,
- dezentere Ranking-Darstellung,
- Tags als rhythmisches Element,
- rote Akzente pointiert statt flächig,
- genug Dichte in der normalen Liste.

### Zustände

Der erste Entwurf sollte mindestens diese Zustände berücksichtigen:

1. Kein Profil

Keine pseudo-personalisierten Inhalte. Klar erklären, dass `Aktuell` erst mit
Musikprofil sinnvoll wird. Optional ein klar markierter Vorgeschmack, aber kein
Fake-Personalisierungsgefühl.

2. Profil vorhanden, Treffer vorhanden

Standardfall mit persönlichem Briefing, Top-Fundstücken und Liste.

3. Profil vorhanden, wenige Treffer

Keine enttäuschende Leere. Die Seite erklärt ehrlich, dass diesmal wenig nah am
Profil lag, bietet aber interessante Ausreißer an.

4. Ladezustand

Der Screen sollte nicht hart springen. Ein ruhiger Ladezustand reicht, aber die
Struktur des kommenden Inhalts sollte erkennbar bleiben.

5. Fehlerzustand

Fehlercopy freundlich und klar. Kein technischer Ton, aber auch kein
Verharmlosen.

### Daten Und Produktfragen

Für den ersten visuellen Entwurf können vorhandene Daten genutzt werden. Einige
Fragen sollten parallel geprüft werden:

- Gibt es genug Informationen, um die Anzahl neuer Reviews im Zeitraum sauber zu
  kommunizieren?
- Können Treffer in `Top-Fundstücke` und normale Liste getrennt werden, ohne
  fachlich falsche Relevanz zu behaupten?
- Welche Daten sind für eine bessere Passungsbegründung verfügbar:
  Stilüberschneidungen, Community-Nähe, Wertung, Score, Review-Kontext?
- Wie kann `Vormerken` später technisch modelliert werden?
- Soll der Vorname für persönlichere Ansprache in einem späteren Profil-/Konto-
  Schritt ergänzt werden?

### Umsetzungsschritte

1. `Aktuell`-Screen im bestehenden Frontend isoliert überarbeiten.
2. Neue Struktur in kleinere Komponenten teilen:
   `AktuellBriefing`, `TopRecommendationGrid`, `RecommendationCard`,
   `RecommendationListToolbar`.
3. Empfehlungskarte zuerst layoutseitig umbauen, ohne die API zu ändern.
4. Top-Fundstücke zunächst aus den ersten zwei bis drei Empfehlungen ableiten,
   solange keine eigene fachliche Top-Logik existiert.
5. Score und Rang visuell zurücknehmen.
6. Copy-Zustände für gute, wenige und schwache Treffer einführen.
7. Screenshot-Suite erweitern oder aktualisieren, sodass der neue `Aktuell`-
   Referenzscreen zuverlässig geprüft wird.
8. Danach Designreview mit Screenshots durchführen.

### Prüfkriterien

Ein erster Entwurf ist besser als der aktuelle Stand, wenn:

- `Aktuell` sofort persönlicher und weniger generisch wirkt.
- die Seite mehr Lust auf neue Musik macht,
- Artist, Album, Stil-Tags und Review-Auszug schneller erfassbar sind,
- Score und Ranking sichtbar bleiben, aber nicht dominieren,
- man ohne Nachdenken erkennt, welche Alben die ersten Klicks verdienen,
- die normale Liste weiterhin dicht und scanbar bleibt,
- die Copy nach Musikfan mit Haltung klingt,
- der Screen auch ohne Bilder nicht leer oder amateurhaft wirkt,
- die Funktionalität gegenüber dem aktuellen Stand nicht schlechter wird.

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

## Interviewrunden

Ziel der Interviewrunden ist nicht, fertige Layout-Lösungen abzufragen. Die
Runden sollen herausarbeiten, welche Wirkung Plattenradar haben soll, welche
Vergleiche hilfreich sind und welche visuellen Richtungen sich falsch anfühlen.
Die Antworten werden hier festgehalten und danach in konkrete Designprinzipien
übersetzt.

Vorgehen:

1. Pro Runde nur ein Thema behandeln.
2. Antworten möglichst in Alltagssprache aufnehmen, nicht in Design-Vokabular
   übersetzen, bevor die Aussage klar ist.
3. Nach jeder Runde die wichtigsten Erwartungen, Ablehnungen und offenen Fragen
   festhalten.
4. Aus den Antworten konkrete Layout-Implikationen ableiten.

Geplante Runden:

- Runde 1: Grundgefühl und erste Produktwirkung.
- Runde 2: Vergleichsprodukte, Referenzen und Anti-Referenzen.
- Runde 3: Startseite, Navigation und Seiten-Dramaturgie.
- Runde 4: Empfehlungskarten, Ranking und Musikdetails.
- Runde 5: Mobile Nutzung, Dichte und Alltagstauglichkeit.
- Runde 6: Abschlussprinzipien für das Neulayout.

### Runde 1: Grundgefühl Und Erste Produktwirkung

Status: ausgewertet  
Datum: 2026-06-27

Leitfrage:

> Wie soll sich Plattenradar anfühlen, wenn jemand die Seite zum ersten Mal
> öffnet?

Antworten:

- Der aktuelle Stand wirkt zu ruhig. Musik ist nicht ruhig, sondern vermittelt
  Emotion, Energie und Neugier. Diese Neugier ist zentral, weil Nutzerinnen und
  Nutzer auf Plattenradar gehen, um neue Musik zu entdecken.
- Das Layout darf nicht nur zweckmäßig beim Finden von Musik helfen, sondern
  muss auch Spaß machen. Ein zu ruhiges Tool erfüllt zwar die Aufgabe, fühlt sich
  aber nicht nach Entdeckung an.
- Mehr Energie darf nicht auf Kosten der Informationen gehen. Plattenradar soll
  lebendiger werden, ohne unübersichtlich oder inhaltlich dünn zu wirken.
- Musikmagazin ist eine wichtige Qualitätsreferenz, aber Plattenradar kann und
  soll kein klassisches Musikmagazin sein. Magazine wie `Visions` werden wegen
  hochwertigem Aufbau und starkem Layout bewundert, haben aber den Vorteil
  guter Bilder.
- Das Fehlen von Bildern ist einer der größten visuellen Nachteile. Albumcover
  würden das Layout sofort aufwerten, sind aber rechtlich riskant und sollen
  wegen Abmahnrisiko nicht leichtfertig verwendet werden.
- Eine Alternative könnten freie Künstlerfotos oder anderes offen lizenziertes
  Bildmaterial sein. Das wäre ein großes eigenes Feature mit neuer Datenpipeline.
  Es müsste nicht jedes Album und nicht jede Karte bebildert werden; einzelne
  visuelle Akzente könnten schon reichen.
- Plattenradar ist faktisch ein Archiv, soll sich aber nicht wie Archivarbeit
  anfühlen. "Archiv" klingt schnell langweilig, mühsam oder qualvoll. Die
  Nutzung soll Spaß machen.
- Es soll keine Streaming-App und kein Blog sein.
- "Persönlicher Scout" trifft einen Teil der Idee, klingt aber noch zu
  langweilig. Persönlich soll Plattenradar trotzdem sein: Die Seite soll Menschen
  direkt ansprechen und ihnen zeigen, dass die Empfehlungen wirklich für sie
  gedacht sind.
- Für mehr Persönlichkeit könnte zusätzlich zur E-Mail auch der Vorname erfasst
  werden. Dann wären Begrüßungen wie "Hallo Jürgen, hier sind neue Rezensionen,
  die gut zu dir passen" möglich.
- Nach zehn Sekunden soll jemand denken: Hier gibt es viele gute Alben, die in
  Vergessenheit geraten sind, aber es wert sind, wieder gehört zu werden. Musik,
  die gesellschaftlich vielleicht nur kurz Aufmerksamkeit hatte, soll neu
  entdeckt werden können.
- Kein klar formulierter Anti-Eindruck wurde genannt. Implizit soll Plattenradar
  aber nicht langweilig, mühsam, beliebig, rechtlich riskant oder wie eine
  generische Streaming-/Blog-/Archivseite wirken.

Erste Auswertung:

- Die zentrale Produktspannung lautet: Plattenradar braucht mehr Energie und
  Neugier, darf aber nicht zur lauten, inhaltsarmen Oberfläche werden.
- "Musikmagazin" ist weniger ein Produkttyp als ein Qualitätsmaßstab: hochwertig,
  sorgfältig, visuell reizvoll. Die konkrete Lösung muss ohne klassische
  Magazinressourcen wie Fotoshootings oder Coverstrecken funktionieren.
- Die visuelle Langeweile hängt stark am fehlenden Bildmaterial. Das Neulayout
  muss daher zwei Pfade gleichzeitig berücksichtigen: ein starkes Layout ohne
  Bilder als v1-Pflicht und optionale offene Bildquellen als spätere
  Aufwertung.
- Der Archivcharakter ist inhaltlich wertvoll, aber emotional gefährlich. Das
  Layout sollte nicht "Datenbestand durchsuchen" vermitteln, sondern "vergessene
  gute Musik wieder ans Licht holen".
- Persönlichkeit ist ein wichtiges Differenzierungsmerkmal. Die Empfehlungen
  sollen nicht allgemein wirken, sondern wie eine persönliche Auswahl.

Layout-Implikationen:

- Mehr sichtbare Energie einführen: stärkere Kontraste, mutigere Typografie,
  rhythmischere Karten, markantere Rangzahlen, pointiertere Zwischenüberschriften
  und weniger große monotone Leerflächen.
- Informationsdichte bewusst erhalten: Empfehlungskarten müssen weiterhin
  Wertung, Quelle, Stil, Passung und Begründung tragen können. Die Energie darf
  aus Hierarchie und Rhythmus kommen, nicht aus reiner Dekoration.
- Bildloses Design als Kernanforderung behandeln. Cover oder Künstlerfotos
  dürfen nicht Voraussetzung für ein gutes Layout sein.
- Optionales Bildmaterial als späteres Enhancement denken: einzelne freie
  Künstlerfotos oder visuelle Akzentplätze für Top-Empfehlungen, nicht zwingend
  flächendeckende Bebilderung jeder Karte.
- "Archiv" im UI sprachlich und visuell anders rahmen: eher Fundstücke,
  Wiederentdeckungen, Ausgrabungen, persönliche Auswahl oder Radar als
  trockenes Archiv.
- Personalisierung sichtbarer machen: Begrüßung, persönliche Batch-Texte,
  Formulierungen wie "für dich" und eventuell Erfassung eines Vornamens prüfen.
- Die erste Seite sollte schneller vermitteln, dass Plattenradar gute, teils
  vergessene Alben wieder hörbar macht. Dieser Gedanke sollte als emotionaler
  Kern in Hero-Copy, Ergebnislisten und leeren Zuständen auftauchen.

### Runde 2: Vergleichsprodukte, Referenzen Und Anti-Referenzen

Status: ausgewertet  
Datum: 2026-06-27

Leitfrage:

> Welche visuellen Referenzen und Anti-Referenzen helfen, die richtige Richtung
> für Plattenradar einzugrenzen?

Antworten:

- Es gibt keine klaren einzelnen Referenzen oder Anti-Referenzen, die direkt als
  Vorbild dienen sollen.
- Plattenradar soll eine Mischung aus `indie/alternativ/handgemacht` und
  `hochwertig/editorial/professionell` werden.
- Das Indie-Gefühl ist wichtig, weil die Musik selbst und die Zielgruppe aus
  diesem Umfeld kommen. Plattenradar soll nicht nach Hochkultur wirken.
- Gleichzeitig darf Indie nicht billig, unfertig oder beliebig aussehen.
- `plattentests.de` ist als Quelle wichtig, aber nicht als visuelle Referenz.
  Die Seite wirkt zu überladen.
- `laut.de` wirkt in der Aufmachung eher billig und sollte nicht als Richtung
  dienen.
- `visions.de` wirkt aufgeräumter und gefällt besser. Der visuelle Eindruck ist
  cooler und näher an der gewünschten Richtung.
- Bei `visions.de` tragen Bilder stark zur Wirkung bei. Das verweist erneut auf
  die Schwierigkeit, dass Plattenradar aktuell ohne Cover oder Künstlerfotos
  auskommen muss.
- Das Indie-Gefühl entsteht bei Musikmagazinen teilweise durch die Artists und
  Bildsprache. Plattenradar muss dieses Gefühl anders erzeugen, wenn keine
  Bilder verfügbar sind.

Erste Auswertung:

- Die Zielrichtung ist kein glattes Premium-Produkt und kein roher Indie-Blog,
  sondern eine glaubwürdige Mischung: zugänglich, etwas kantig, musiknah, aber
  sorgfältig gestaltet.
- `Indie` beschreibt hier weniger eine visuelle Mode als eine Haltung:
  persönlich, neugierig, nicht zu corporate, nicht zu elitär.
- `Professionell` beschreibt die Ausführung: klare Hierarchie, gute Abstände,
  saubere Typografie, Vertrauen und redaktionelle Sorgfalt.
- Überladung ist ein klares Risiko. Plattenradar darf wegen vieler Daten,
  Tags, Scores und Filter nicht in eine dichte Portal-Optik kippen.
- Billigkeit ist ebenfalls ein klares Risiko. Rote Akzente, Boxen, Badges und
  Rankings müssen bewusst gestaltet werden, damit sie nicht wie Anzeigen- oder
  Boulevard-UI wirken.
- `visions.de` ist als Stimmungsreferenz interessant, aber nicht direkt
  übertragbar, weil Plattenradar weniger Bildmaterial hat und stärker aus Daten
  und Empfehlungen besteht.

Layout-Implikationen:

- Designrichtung: `indie, aber sorgfältig`; `editorial, aber nicht Hochkultur`;
  `professionell, aber nicht corporate`.
- Weniger Portal-Dichte: keine überladenen Seiten mit zu vielen gleich lauten
  Modulen, Teasern und Nebeninformationen.
- Keine billige Lautstärke: Akzentfarbe, Buttons und Rankings pointiert
  einsetzen, nicht flächig oder marktschreierisch.
- Mehr Coolness über Typografie, Rhythmus und Komposition erzeugen, nicht über
  dekorative Effekte.
- Bildlose Layouts müssen die Funktion von Bildern teilweise ersetzen:
  typografische Hero-Elemente, starke Nummern, Zitate, kontrastierende Flächen,
  ungewöhnlichere Kartenzuschnitte und redaktionelle Gruppierungen.
- Plattenradar sollte die Quelle `plattentests.de` respektvoll sichtbar machen,
  aber nicht deren visuelle Dichte oder Seitenstruktur übernehmen.
- Die Gestaltung sollte sich eher an einer aufgeräumten Musikmagazin-Haltung
  orientieren als an klassischen Musikportalen.

### Runde 3: Startseite, Navigation Und Seiten-Dramaturgie

Status: ausgewertet  
Datum: 2026-06-27

Leitfrage:

> Welche Rolle sollen Startseite, Navigation und die verschiedenen Hauptseiten
> im neuen Layout spielen?

Antworten:

- Die Startseite ist grundsätzlich schon relativ gut. Sie muss nicht stark
  umgebaut werden.
- Die Startseite soll vor allem erklären, warum es Plattenradar gibt. Diese
  Erklärung kann noch geschärft werden, aber die aktuelle Richtung ist in
  Ordnung.
- Nach einem gespeicherten Profil soll es keine klassische Startseite mehr als
  Standard-Landeort geben. Nutzerinnen und Nutzer sollen direkt bei `Aktuell`
  landen.
- `Aktuell` soll für Rückkehrer stärker persönlich und situativ ansprechen:
  zum Beispiel "Schön, dass du zurück bist" oder "In den letzten zwei Wochen
  kamen ein paar gute Alben für dich raus".
- Die Ansprache auf `Aktuell` soll auch mit negativen oder schwächeren Fällen
  umgehen können: Wenn es zuletzt keine sehr gut passenden Alben gab, könnte die
  Seite trotzdem neugierig machen, etwa mit "Wenn du mal was Neues ausprobieren
  möchtest, hör doch hier rein".
- Bei der Navigation ist Funktion wichtiger als Charakter. Sie darf mehr
  Charakter bekommen, solange die Bedienbarkeit und Orientierung nicht darunter
  leiden.
- Ohne Profil ergeben `Aktuell`, `Entdecken` und `Playlists` nur eingeschränkt
  Sinn. Ohne gespeichertes oder temporäres Musikprofil sollten keine
  personalisierten Daten angezeigt werden.

Erste Auswertung:

- Die eigentliche Bühne des Produkts ist nicht die allgemeine Startseite,
  sondern die personalisierte Rückkehrseite `Aktuell`.
- Die Startseite muss Vertrauen und Verständnis schaffen, nicht die ganze
  visuelle Energie tragen.
- `Aktuell` braucht eine stärkere redaktionelle Logik: eine persönliche
  Kurzmeldung zur aktuellen Review-Lage, nicht nur eine Ergebnisliste.
- Ein guter `Aktuell`-Screen muss mehrere Zustände gestalten: viele passende
  neue Reviews, wenige passende Reviews, keine starken Treffer, experimentelle
  Alternativen.
- Navigation soll nicht zum Design-Selbstzweck werden. Charakter ist willkommen,
  aber nur als Unterstützung der Orientierung.
- Gate-Zustände ohne Profil bleiben notwendig. Sie sollten klar erklären, dass
  Personalisierung erst nach dem Musikprofil möglich ist.

Layout-Implikationen:

- Startseite nur behutsam schärfen: stärkere Copy, klarerer Nutzen, eventuell
  ein kleiner Vorgeschmack, aber kein radikaler Umbau.
- Für eingeloggte oder profilierte Nutzer `Aktuell` als eigentliche Home-Seite
  behandeln.
- `Aktuell` braucht einen personalisierten Hero-/Briefing-Bereich mit
  Rückkehrbegrüßung, Zeitraum, Anzahl neuer relevanter Reviews und ein bis zwei
  hervorgehobenen Empfehlungen.
- Für schwache Treffer eigene Copy- und Layout-Zustände entwerfen, damit die
  Seite nicht leer oder enttäuschend wirkt.
- Navigation schlicht und belastbar halten. Charakter eher über Typografie,
  aktiven Zustand, kleine Layoutdetails und konsistente Sprache einbringen als
  über verspielte Navigationselemente.
- Ohne Profil keine pseudo-personalisierten Inhalte anzeigen. Stattdessen
  ehrliche Gate-Zustände mit klarem Weg zum Musikprofil und eventuell einem
  nicht-personalisierten Vorgeschmack, der klar als Beispiel markiert ist.

### Runde 4: Empfehlungskarten, Ranking Und Musikdetails

Status: ausgewertet  
Datum: 2026-06-27

Leitfrage:

> Was muss eine Empfehlungskarte leisten, damit aus einer Empfehlung echte
> Neugier auf Musik wird?

Antworten:

- Eine Empfehlungskarte soll zuerst vermitteln: Die Genres passen zu mir, das
  klingt spannend, das kenne ich noch nicht, da möchte ich reinhören.
- Die Karte soll Anreiz geben, sich mit dieser Musik zu beschäftigen.
- Die wichtigsten Informationen sind Artist, Album, Stil-Tags und der
  Review-Auszug. Der Review-Auszug ist besonders wichtig, weil er Neugier
  schafft.
- Die Rangfolge ist nicht das wichtigste Element. Es geht nicht darum, einen
  Gewinner zu küren.
- Im Archiv sind Score-Unterschiede zwischen den besten Treffern oft so klein,
  dass eine harte Rangliste wenig Sinn ergibt. Die Sortierung soll erkennbar
  bleiben, aber Rankingplätze sollten nicht zu stark dramatisiert werden.
- Im Archiv soll Ranking vor allem Orientierung geben: Die Liste ist absteigend
  sortiert und man versteht, wo man sich gerade befindet.
- Bei Neuerscheinungen ist Ranking ebenfalls nicht zentral, aber es ist
  relevanter zu zeigen, wie viele Alben aus einem neuen Review-Batch in der Nähe
  des eigenen Musikgeschmacks liegen.
- Für `Aktuell` wäre eine subtile Distanz- oder Nähe-Logik hilfreich: Wie nah
  sind die neuen Rezensionen am eigenen Profil?
- Ein Score-Wert darf sichtbar sein, soll aber nicht im Vordergrund stehen.
- Die Erklärung der Passung muss klarer werden. Aktuell wirkt sie zu generisch.
- Eine Karte darf ungefähr zwei Sätze Text haben. Das schafft Neugier, ohne zu
  viel zu werden.
- Top-Empfehlungen sollen bei Neuerscheinungen anders aussehen. Zwei bis drei
  Top-Empfehlungen dürfen hervorgehoben werden und stärker Neugier erzeugen.
- Direkt an der Karte sollte man die Rezension öffnen können.
- Album vormerken ist interessant.
- Zur Playlist hinzufügen ist ebenfalls spannend. Besonders wertvoll wäre eine
  gezielte Playlist-Erstellung aus vorgemerkten Alben, nicht nur eine automatisch
  generierte Zufalls- oder Gesamtplaylist.

Erste Auswertung:

- Empfehlungskarten sind kein Ranking-Widget, sondern der zentrale Moment der
  Musikentdeckung.
- Das wichtigste Versprechen einer Karte lautet nicht "Platz 1", sondern
  "klingt nach dir und lohnt sich zu entdecken".
- Stil-Tags und Review-Auszug tragen emotional mehr als Score und Rang.
- Ranking bleibt als Orientierung nützlich, darf aber nicht die Wahrnehmung der
  Musik dominieren.
- `Aktuell` und `Entdecken` brauchen unterschiedliche Kartenlogik:
  `Aktuell` darf Top-Fundstücke und Batch-Nähe stärker inszenieren, während
  `Entdecken` eher eine hochwertige, gut scanbare Fundstückliste braucht.
- Die Passungsbegründung ist ein eigenes UX-Thema. Sie muss konkreter, weniger
  generisch und weniger technisch werden.
- Vormerken und gezielte Playlist-Erstellung könnten aus der Empfehlungsliste
  einen echten Workflow machen: entdecken, merken, später als Playlist hören.

Layout-Implikationen:

- Kartenhierarchie ändern: Artist, Album, Stil-Tags und Review-Auszug vor Rang
  und Score stellen.
- Ranking dezent halten: kleine Positionsmarker, Abschnittslogik oder
  Listenorientierung statt großer Siegernummern, besonders im Archiv.
- Für `Aktuell` eine Top-Auswahl mit zwei bis drei hervorgehobenen Karten
  gestalten. Diese Karten dürfen größer, editorialer und erklärender sein.
- Für `Entdecken` eher gleichwertige Fundstückkarten gestalten, weil viele
  Treffer ähnlich passend sein können.
- Score sichtbar, aber sekundär darstellen. Besser als Detail oder Tooltip
  behandeln, nicht als Hauptbadge.
- Passung als Text verbessern: statt generischem "passt zu deinem Profil" eher
  konkrete Gründe aus Stil-Tags, ausgewählten Präferenzen, Wertung oder
  Review-Kontext ableiten.
- Review-Auszüge auf etwa zwei Sätze begrenzen und typografisch so setzen, dass
  sie wie ein neugierig machender redaktioneller Teaser wirken.
- Kartenaktionen prüfen: `Rezension öffnen`, `Vormerken`, `Zur Playlist
  hinzufügen`. Der wichtigste neue Workflow wäre eine Playlist aus vorgemerkten
  Alben.
- Die Playlist-Funktion sollte perspektivisch nicht nur automatisch generieren,
  sondern auch kuratierte Nutzerentscheidungen aufnehmen.

### Runde 5: Mobile Nutzung, Dichte Und Alltagstauglichkeit

Status: ausgewertet  
Datum: 2026-06-27

Leitfrage:

> Für welche Nutzungssituation soll das nächste Layout zuerst optimiert werden,
> und wie dicht darf die Oberfläche werden?

Antworten:

- Desktop steht zunächst im Vordergrund. Erst wenn die Desktop-Funktionalität
  und das Desktop-Layout stehen, soll eine schöne mobile Version entworfen
  werden.
- Eine App ist perspektivisch denkbar, aber nicht Teil des ersten
  Layout-Schritts.
- Mobile soll im ersten Moment anzeigbar sein und nicht schlecht aussehen. Eine
  eigene konkrete Mobile-Designrunde soll später folgen.
- Ob Mobile eine vollständige Version sein soll, ist noch offen. Denkbar wäre
  eher: neue Empfehlungen checken, vormerken, vielleicht ein Hinweis auf eine
  spätere App.
- Ein wichtiger mobiler Use Case ist das schnelle Prüfen neuer Rezensionen nach
  einer E-Mail-Benachrichtigung: Man bekommt eine Mail, dass neue Rezensionen
  online sind, und möchte diese auf Plattenradar.de anschauen.
- Bei der Dichte braucht es einen Kompromiss. Es soll nicht so wenig Inhalt
  sichtbar sein, dass man nach drei Karten schon weiterklicken muss.
- Die aktuelle Größenordnung von etwa 20 Empfehlungen wirkt grundsätzlich nicht
  schlecht.
- Auf einen Blick sollten ungefähr vier bis sechs Empfehlungen erfassbar sein,
  bevor es zu voll wird.
- Ob zu wenig Information oder zu viel Dichte schlimmer ist, ist schwer zu
  entscheiden. Hier muss das Layout einen guten Kompromiss finden.
- Mobil besonders wichtig: schnell die neuesten Rezensionen sehen.
- Das Musikprofil soll mobil zunächst eher nicht vollständig im großen
  Setup-Prozess optimiert werden. Kleine Anpassungen sind denkbar, der große
  Setup-Prozess darf erstmal desktopfreundlicher bleiben.

Erste Auswertung:

- Das nächste Neulayout sollte desktop-first sein, aber nicht mobile-blind.
- Mobile ist vorerst ein stabiler, gut aussehender Begleitmodus, nicht die
  primäre Entwurfsfläche.
- Der wichtigste mobile Produktmoment ist `Aktuell`: neue Rezensionen aus einer
  Benachrichtigung heraus schnell prüfen und gegebenenfalls vormerken.
- Die gewünschte Dichte spricht gegen sehr große, isolierte Einzelkarten als
  Standard. Plattenradar braucht genug Atmosphäre, aber weiterhin eine
  listenartige Scanbarkeit.
- Vier bis sechs erfassbare Empfehlungen pro Desktop-Blickfeld sind eine gute
  Zielgröße für Listen- oder Grid-Entwürfe.
- Mobile Profilbearbeitung darf reduziert gedacht werden. Das senkt die
  Komplexität der ersten Layout-Runde.

Layout-Implikationen:

- Desktop-Referenzscreen zuerst entwerfen, insbesondere `Aktuell` und
  Empfehlungskarten.
- Mobile weiterhin responsiv sauber halten, aber noch keine vollständige
  mobile Produktstrategie erzwingen.
- Für Mobile später eine eigene Runde planen, besonders für Benachrichtigungen,
  neue Reviews, Vormerken und mögliche App-Übergänge.
- Empfehlungsliste nicht zu stark vereinzelnen: Top-Karten dürfen größer sein,
  aber die normale Liste muss mehrere Treffer schnell erfassbar machen.
- Desktop-Dichte testen mit dem Ziel, etwa vier bis sechs Empfehlungen im
  sichtbaren Bereich erfassen zu können, ohne dass die Seite überladen wirkt.
- Kartenaktionen wie `Vormerken` sind mobil wahrscheinlich wichtiger als
  komplexe Filter- oder Profilbearbeitung.
- Das Musikprofil auf Mobile zunächst lesbar und punktuell bearbeitbar halten;
  der vollständige Setup-Flow kann später separat optimiert werden.

### Runde 6: Abschlussprinzipien Für Das Neulayout

Status: ausgewertet  
Datum: 2026-06-27

Leitfrage:

> Welche Prinzipien sollen das Redesign führen, wenn es konkrete Trade-offs gibt?

Antworten:

- Drei Regeln für das neue Layout:
  1. Leute sollen Spaß haben, nach Musik zu suchen.
  2. Die Funktion muss im Vordergrund stehen. Wenn es einen Trade-off zwischen
     Funktion und Optik gibt, ist eher die Funktion wichtiger.
  3. Die Nutzung soll seamless und angenehm zu navigieren sein: wenig Klicken,
     wenig Umständlichkeit.
- Bei der Abwägung zwischen Atmosphäre und Scanbarkeit ist Scanbarkeit wichtiger.
  Es geht darum, Musik zu finden. Atmosphäre kann dazu beitragen, soll aber nicht
  im Vordergrund stehen.
- Im Redesign darf die zugrunde liegende Funktionalität auf keinen Fall kaputt
  gehen.
- Mutig verändert werden dürfen Layout, Farbe, Strukturgeometrie und
  gegebenenfalls die Einbindung von Bildern, wenn das möglich ist.
- Welche Seite als erster Referenzscreen neu entworfen wird, kann aus
  programmiertechnischen und UI-Gesichtspunkten entschieden werden.
- Ein besserer Entwurf wäre daran erkennbar, dass die Ansprache nicht mehr so
  dröge wirkt. Text und Layout sollen cooler und verständlicher werden.
- Die Oberfläche soll nicht nach KI-generiertem Produkttext klingen, sondern
  nach einem Musikfan mit Haltung, der andere Musikfans als Freunde betrachtet.
- Das Layout soll ebenfalls Haltung ausstrahlen und nicht langweilig sein.
- Leitmotiv für das Redesign:

> Die Funktionalität steht. Jetzt sorgen wir dafür, dass es auch Spaß macht, das
> Tool zu nutzen.

Erste Auswertung:

- Das Redesign ist kein reines Verschönerungsprojekt. Es soll die vorhandene
  Funktion emotional zugänglicher machen.
- Funktionalität bleibt die harte Grenze. Atmosphäre, Farbe und visuelle
  Eigenständigkeit sind wichtig, aber sie dürfen Orientierung, Scanbarkeit und
  Workflows nicht verschlechtern.
- Die Textstimme ist Teil des Designs. Plattenradar braucht nicht nur andere
  Karten, sondern eine andere Ansprache: weniger generisch, weniger KI-glatt,
  mehr Musikfan mit Haltung.
- Die Nutzerbeziehung soll freundschaftlich wirken, nicht distanziert oder
  belehrend.
- Mut darf vor allem in Layout, Farbe, Geometrie und visueller Dramaturgie
  liegen, nicht in versteckter Navigation oder komplizierteren Workflows.

Layout-Implikationen:

- Erster Referenzscreen sollte `Aktuell` sein, weil dort Rückkehrer-Ansprache,
  neue Rezensionen, Top-Empfehlungen, Kartenhierarchie, Dichte und mögliche
  Vormerken-Aktionen zusammenkommen. Danach kann die isolierte Empfehlungskarte
  als wiederverwendbares Kernobjekt verfeinert werden.
- Designentscheidungen immer gegen Funktion testen: Kann man schneller passende
  Musik finden? Sind wichtige Informationen leichter erfassbar? Braucht man
  weniger Klicks?
- Mehr Atmosphäre über Hierarchie, Rhythmus, Farbe und Sprache schaffen, nicht
  über zusätzliche Hürden oder dekorative Ablenkung.
- Copy als eigenes Redesign-Material behandeln. Zielton: musiknah,
  freundlich, neugierig, mit Haltung, aber nicht bemüht cool.
- Layout darf deutlich mutiger werden: andere Kartenformate, stärkere
  Abschnittsdramaturgie, prägnantere Farben und optional Bildplätze für spätere
  freie Bildquellen.
- Scanbarkeit als Qualitätskriterium festlegen. Auch ein atmosphärischer Screen
  muss schnell zeigen, welche Alben interessant sind und was man als Nächstes
  tun kann.

### Runde 7: Feedback Zum Aktuell-Referenzentwurf (Nacharbeiten)

Status: ausgewertet  
Datum: 2026-06-27

Screenshots:

- `frontend/screenshots/aktuell-redesign.png` (aktueller Referenzstand)

Antworten / Beobachtungen aus den Feedback-Runden:

- Der Aktuell-Referenzscreen wirkt insgesamt stimmig; Briefing, Top-Fundstücke
  und Listenkarten sind deutlich ruhiger als im ersten Entwurf.
- Stil-Tags mit Farbskala und Profil-Ring werden als hilfreich wahrgenommen;
  die Legende unter der Filterleiste trägt ohne zu dominieren.
- Vormerken als Herz oben rechts spart Platz und passt zur Karte.
- Drei-Zeilen-Vorschau mit `[...]` am Wortende ist gewünscht und responsiv
  umgesetzt.
- In den Karten fehlten noch **Veröffentlichungsdatum** und **Plattenlabel**
  in der Meta-Zeile (wie auf der Streamlit-Seite).
- Der Ladehinweis „Empfehlungen werden aktualisiert“ war ein Bug (hängender
  Reload-State) und wurde in die Toolbar integriert.

Umsetzung nach Runde 7:

- Meta-Zeile ergänzt: `TT.MM.JJJJ` (Fallback Jahr), Rating, Score,
  `Plattenlabel: …` — analog `recommendation_card_meta_parts` in Streamlit.
- `release_date` aus der API wird im Frontend gemappt.

### Runde 8: Analyse Aktuell-Stand Und Offene Punkte

Status: Analyse nach positivem Zwischenfeedback  
Datum: 2026-06-27

**Was gut trägt**

- Klare Hierarchie: Briefing → Filter/Legende → Top-Fundstücke → Restliste.
- Karten sind scanbar: Titel-Link, Meta, Tags, Vorschau, Herz-Aktion.
- Typografie konsolidiert: Serif nur noch für große Seitenüberschriften, Sans
  in Karten und UI.
- Funktionale Informationsdichte ohne erklärende „Passt wegen …“-Texte.

**Was als Nächstes Sinn machen könnte (ohne Scope-Sprengung)**

| Priorität | Thema | Anmerkung |
|-----------|--------|-----------|
| Hoch | Vormerken aktivieren | Herz ist Platzhalter; kuratierte Playlist war Interview-Wunsch |
| Mittel | Meta-Zeile bei schmalen Karten | Viele Segmente können umbrechen; ggf. zweizeilig oder kürzere Labels |
| Mittel | Entdecken angleichen | Aktuell ist Referenzscreen; Archiv-Liste noch älterer Stil |
| Niedrig | Filter-Panel einklappbar | Toolbar wirkt noch „boxig“, wenn Panel offen ist |
| Niedrig | Highlight-Beschriftungen | „Beste Passung“ / „Kritikerfavorit“ — optional kürzer oder weg |

**Designprinzipien-Check**

- Funktion vor Dekoration: erfüllt.
- Scanbarkeit vor Atmosphäre: erfüllt.
- Musikfan-Ton im Briefing: erfüllt; Meta-Zeile bleibt sachlich (gewollt).
- Keine KI-glatter Erklärprosa auf Karten: erfüllt.

**Fazit**

Der Aktuell-Referenzentwurf ist für eine Desktop-Referenzrunde reif genug, um
als Vorlage für Entdecken und spätere Mobile-Runde zu dienen. Die größten
verbleibenden Lücken sind Produktlogik (Vormerken/Playlist) und konsistente
Übertragung auf weitere Screens — nicht grundsätzliches Layout.

## Arbeitsnotiz

Die aktuelle UI sollte nicht verworfen werden. Sie ist als funktionale Grundlage
wertvoll. Die nächste Runde sollte vor allem eine stärkere visuelle Sprache
darüberlegen: mehr Rhythmus, mehr Editorialität, mehr Musikgefühl und weniger
generische App-Boxen.
