# Plattenradar v1: Produkt- und API-Schnitt

Konsolidierte Produktspezifikation und Entscheidungslog für das Produktinterview, UX-Konzept und den späteren API-Schnitt.

Stand: 2026-06-22

## Konsolidierte v1-Spezifikation

### Produktziel

Plattenradar v1 macht aus den Daten von plattentests.de einen persönlichen Musik-Assistenten mit explorativen Review-Werkzeugen.

Das Kernversprechen lautet:

> Plattenradar hilft musikinteressierten plattentests.de-Lesern mit wenig Zeit, aus dem großen Review-Archiv und aus wöchentlichen Neuerscheinungen genau die Musik zu finden und anzuhören, die zu ihrem Geschmack passt.

Der Kern ist nicht "mehr Daten anzeigen", sondern "passende Musik hörbar machen".

### Zielgruppe

Primäre Nutzer sind zunächst der Projektbetreiber und sein Freundeskreis. Die App ist ein Hobbyprojekt mit professionellem Anspruch und soll zeigen, wie weit eine hochwertige Website mit KI-Unterstützung als Einzelperson gebaut werden kann.

Gedankliche Zielgruppe ist die Leserschaft von plattentests.de: musikinteressierte, neugierige Hörer mit Freude an Rezensionen, Referenzen und Entdeckungen. Die Anwendung muss nicht von Anfang an für Tausende Nutzer skaliert sein, soll sich aber so anfühlen, dass sie perspektivisch für die plattentests.de-Community relevant werden könnte.

### Kernprobleme

Plattenradar ergänzt plattentests.de, ersetzt es aber nicht. plattentests.de bleibt die redaktionelle und kulturelle Basis; Plattenradar wertet diese Daten systematisch und persönlich aus.

V1 löst zwei Kernprobleme:

1. **Vergangene Musik neu entdecken**
   Das Review-Archiv reicht bis 1999 zurück. Viele relevante Alben aus der Zeit vor dem eigenen Einstieg als Leser bleiben unentdeckt. Plattenradar macht diese Perlen anhand des eigenen Geschmacks sichtbar.

2. **Neue Rezensionen effizient hörbar machen**
   Neue Rezensionen sollen nicht nur gelesen, sondern schnell als relevante Musikauswahl hörbar werden. Kurzfristig passiert das über manuelle Playlist-Exports; automatische Zustellung bleibt ein späteres Feature.

### V1-Funktionsumfang

Unverzichtbar für v1:

- Geschmacksprofil-Schritt 1 bis 3 auf Basis der bestehenden Logik,
- Archivempfehlungen aus dem gesamten lokalen Bestand,
- neueste Rezensionen bzw. Empfehlungen auf Basis neuer Rezensionen,
- Playlist-Erzeugung und TXT-/CSV-Export,
- Profil speichern,
- Profil laden,
- Konto anlegen,
- klare Empfehlungskarten mit subtiler Erklärbarkeit.

Nicht v1-pflichtig:

- automatische Playlist-Zustellung,
- Playlist-Historie,
- gespeicherte RecommendationSets,
- "Merken", "Ausblenden" oder "Schon gehört",
- komplexe Kontoverwaltung,
- Social Features,
- echte Wochenbatches, solange `first_seen_at` / `scraped_at` fehlen.

Der bestehende Entdecken-Hub ist keine Pflichtfunktion, sondern eine aktuelle Navigationslösung. Die fachlichen Ziele dahinter müssen erreichbar bleiben, die Kachelstruktur selbst darf ersetzt werden.

### User Flow

Der erste Nutzerfluss soll nicht mit Registrierung starten.

Empfohlener v1-Flow:

1. Nutzer öffnet Plattenradar.
2. Nutzer erstellt ein temporäres Geschmacksprofil über Schritt 1 bis 3.
3. Nutzer sieht zuerst Archivempfehlungen als Aha-Moment.
4. Auf der Archivempfehlungsseite sind klare Folgeaktionen sichtbar:
   - Profil speichern,
   - neue Rezensionen ansehen,
   - Playlist erzeugen,
   - Geschmack/Filter anpassen.
5. Nach dem Aha-Moment wird Kontoerstellung als Nutzenangebot platziert: Profil speichern und später wiederverwenden.

Login bleibt jederzeit erreichbar, damit wiederkehrende Nutzer direkt ihr gespeichertes Profil laden können.

### Hauptbereiche

V1-Hauptbereiche:

- **Profil:** Geschmacksprofil anzeigen, bearbeiten, speichern und laden.
- **Archiv entdecken:** persönliche Empfehlungen aus dem gesamten Review-Bestand.
- **Neue Rezensionen:** neue Reviews personalisiert sortiert und bewertet.
- **Playlists:** manuelle Playlist-Erzeugung und Export.
- **Einstellungen:** Konto, E-Mail und spätere Benachrichtigungs-/Automatisierungsoptionen.

Archiv entdecken und Neue Rezensionen bleiben getrennte Bereiche, teilen sich aber Karten-, Ranking- und Erklärlogik.

### Profil- und Account-Modell

Wichtige Unterscheidung:

- **Temporäres Geschmacksprofil:** entsteht nach Schritt 1 bis 3, ohne Anmeldung.
- **Gespeichertes Profil:** ist einem Nutzerkonto zugeordnet und kann geladen, geändert und später für Automatisierung verwendet werden.

Auth-v1:

- einfache E-Mail-und-Passwort-Lösung,
- kein separater Benutzername,
- keine Registrierung als Einstiegshürde,
- Passwort-Hashing und saubere Sessions trotz kleinem Nutzerkreis.

Empfohlenes Profilmodell:

- Backend/API modelliert `TasteProfile` als eigene Ressource mit `id`, `name`, `user_id` und `is_default`.
- V1-UI startet mit einem Default-Profil.
- Das Datenmodell erlaubt mehrere Profile pro Nutzer, damit spätere Profilvarianten und Playlist-Konfigurationen nicht verbaut werden.
- Login überschreibt nie automatisch ein temporäres Profil.

Wenn ein Nutzer mit temporärem Profil einloggt, fragt die UI explizit:

- aktuelles Profil speichern,
- gespeichertes Profil laden,
- temporär weiterarbeiten.

### Filter- und Preset-Modell

Alle bestehenden Filter bleiben v1-pflichtig und werden gespeichert. Die neue UI stellt aber Grundmodi vor Expertenfilter.

Grundsatz:

> Grundmodi sind die primäre Bedienebene; alle bestehenden Filter bleiben als Expertenfilter verfügbar und gespeichert.

Alle Filterwerte sind Teil des Geschmacksprofils:

- `year_min`,
- `year_max`,
- `rating_min`,
- `rating_max`,
- `score_min`,
- `score_max`,
- `community_spectrum_crossover`,
- `overall_weight_alpha`,
- `overall_weight_beta`,
- `overall_weight_gamma`,
- `plattenlabel_selection`,
- `sort_mode`,
- `serendipity`,
- `community_weights_raw`.

Reine UI-Zustände wie aufgeklappte Panels, aktuelle Seitennummern oder lokale Widget-Keys werden nicht gespeichert.

V1-Presets:

| Preset | `score_min` | Rating | Gewichtung | Besonderheit |
| --- | ---: | --- | --- | --- |
| Treffsicher | 0.50 | 6-10 | 0.60 / 0.20 / 0.20 | strenge Stilpassung, Breite neutral |
| Ausgewogen | 0.40 | 6-10 | 0.50 / 0.25 / 0.25 | Default |
| Entdeckerisch | 0.25 | 6-10 | 0.50 / 0.25 / 0.25 | stilistisch offener, kein Zufall |
| Kritikerlieblinge | 0.40 | 8-10 | 0.35 / 0.45 / 0.20 | Wertung wichtiger |
| Vielschichtig | 0.40 | 6-10 | 0.45 / 0.20 / 0.35 | `crossover = 0.75` |

Presets setzen einmal konkrete Reglerwerte. Sobald der Nutzer Werte manuell ändert, ist das Profil benutzerdefiniert. Gespeichert werden die Werte, nicht zwingend der aktive Preset.

### Empfehlungserklärungen

Erklärbarkeit ist wichtig, aber nicht die Kernfunktionalität. Die Musik und die Empfehlung stehen im Vordergrund.

Grundsatz:

> Plattenradar erklärt Empfehlungen subtil, visuell und geschmacklich, nicht als technische Score-Lektion.

V1-Erklärung:

- passende Genre-/Community-Tags werden dezent hervorgehoben,
- eine kurze Legende erklärt die Hervorhebung,
- technische Begriffe bleiben intern,
- Scorebestandteile werden nicht prominent auf jeder Karte erklärt.

Interne Begriffe wie `purity_raw`, `breadth_raw`, `overall_weight_gamma` oder `community_spectrum_norm` bleiben aus der normalen UI heraus. Nutzersprache muss später anhand der Formeln weiter geschärft werden.

### Playlist-Export

Playlist-Erzeugung ist in v1 synchron:

1. Nutzer klickt "Playlist erzeugen".
2. Plattenradar berechnet Vorschläge.
3. Nutzer erhält direkt TXT- oder CSV-Download.

V1 unterstützt zwei Quellen:

- `archive`,
- `new_reviews`.

Playlist-Exports werden in Plattenradar nicht dauerhaft gespeichert. Nach dem Export lebt die Playlist im Musikdienst oder in TuneMyMusic weiter. Automatisierung wird im Datenmodell mitgedacht, aber nicht gebaut.

### Ergebnislisten

Empfehlungen dürfen intern vollständig berechnet werden, aber die API liefert paginierte Ausschnitte.

V1-Regeln:

- Endpunkte unterstützen `limit` und `offset`.
- Response enthält `total`, `limit`, `offset` und `items`.
- Default ist deterministisch.
- `RecommendationSet` ist ein Response-Modell, keine gespeicherte Ressource.
- Keine Persistenz einzelner Empfehlungseinträge in v1.

Die Zufallskomponente wird als separater Listenmechanismus behandelt:

- UI-Arbeitsname: **Liste variieren**.
- Sie ist nicht Teil der Geschmacks-Presets.
- Sie wirkt auf die Rangliste, nicht auf die Grunddefinition des Geschmacksprofils.

### Neueste Rezensionen und Batches

Kurzfristig nutzt v1 "letzte X Rezensionen", weil ein echtes Rezensions- oder Discovery-Datum fehlt.

Perspektivisch soll die Pipeline speichern, wann Plattenradar eine Rezension erstmals gesehen hat:

- `first_seen_at`,
- `scraped_at`.

Damit werden später echte Wochenbatches, Batch-Fit und automatische Playlist-Zustellung möglich.

### API-Ressourcen

Vorgesehene Ressourcen:

- `User`,
- `TasteProfile`,
- `TasteFilterSettings`,
- `Review`,
- `Recommendation`,
- `RecommendationSet` als Response-Modell,
- `WeeklyBatchFit` später,
- `PlaylistExport` als transienter Response-Typ.

Spätere Ressourcen:

- `PlaylistSubscription`,
- `EmailDelivery`,
- `ScheduledPlaylistRun`,
- `UserAlbumState`,
- `RecommendationFeedback`.

### Aktueller API-Schnitt v1

Der aktuelle FastAPI-Schnitt ist ein privater HTTP-Vertrag für ein zukünftiges Frontend. Er ist nicht als öffentliche Entwickler-API gedacht. Streamlit funktioniert weiterhin ohne HTTP und ruft die Python-Services direkt auf.

Lokaler Start:

```bash
hatch run api --host 127.0.0.1 --port 8000
```

Interaktive Doku:

- `http://127.0.0.1:8000/docs`

Health:

- `GET /health`

Auth und aktueller Nutzer:

- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `GET /v1/me`
- `GET /v1/me/taste-profile`
- `PUT /v1/me/taste-profile`

Presets:

- `GET /v1/presets`
- `GET /v1/taste-filter-ui`

Empfehlungen:

- `POST /v1/recommendations/archive`
- `POST /v1/recommendations/new-reviews`

Playlist:

- `POST /v1/playlists/export`

#### `GET /health`

Zweck: einfacher lokaler Check, ob der API-Server läuft.

Beispiel-Response:

```json
{
  "status": "ok",
  "service": "plattenradar-api"
}
```

#### `GET /v1/presets`

Zweck: liefert die konfigurierten Grundmodi für Filter und Gewichtungen.

Response: Liste von Presets mit `id`, `label`, `subtitle`, `description`, `icon` und `filter_settings`.

Beispiel-Ausschnitt:

```json
[
  {
    "id": "balanced",
    "label": "Ausgewogen",
    "subtitle": "Der beste Startpunkt",
    "description": "Gute Mischung aus Stilpassung, Wertung und Vielschichtigkeit.",
    "icon": "sliders-horizontal",
    "filter_settings": {
      "rating_min": 6.0,
      "rating_max": 10.0,
      "score_min": 0.4,
      "score_max": 1.0,
      "community_spectrum_crossover": 0.5,
      "overall_weight_alpha": 0.5,
      "overall_weight_beta": 0.25,
      "overall_weight_gamma": 0.25,
      "sort_mode": "deterministic",
      "serendipity": 0.0
    }
  }
]
```

#### `GET /v1/taste-filter-ui`

Zweck: liefert die semantische UI-Konfiguration für die Filterseite. Dieser Endpunkt ist der Vertrag für das spätere Frontend: Es muss technische Felder wie `overall_weight_alpha` nicht selbst benennen, sondern bekommt Gruppen, Labels, kurze Hilfetexte und die Expertenfilter-Markierung aus der API.

Response: Objekt mit `default_preset_id`, `preset_display`, `preset_display_hint` und `groups`.

Beispiel-Ausschnitt:

```json
{
  "default_preset_id": "balanced",
  "preset_display": "selection_cards",
  "preset_display_hint": "Presets erscheinen als mittelgroße Auswahlkarten mit Icon, Titel und kurzem Erklärungssatz. Sie setzen die darunterliegenden Regler einmalig.",
  "groups": [
    {
      "id": "core_fit",
      "label": "Passung",
      "description": "Grenzt ein, wie nah Alben an deinem Musikprofil liegen.",
      "controls": [
        {
          "id": "style_fit",
          "label": "Stilpassung",
          "description": "Legt fest, wie stark ein Album zu deinen gewählten Stilrichtungen passen muss.",
          "kind": "range",
          "fields": ["score_min", "score_max"],
          "expert": false
        }
      ]
    }
  ]
}
```

#### `POST /v1/auth/register`

Zweck: registriert einen Nutzer per E-Mail und Passwort. Optional kann direkt ein temporäres Geschmacksprofil gespeichert werden.

Beispiel-Request:

```json
{
  "email": "alice@example.com",
  "password": "secret123",
  "profile": {
    "selected_communities": ["C001"],
    "community_weights_raw": {
      "C001": 1.0
    },
    "filter_settings": {
      "rating_min": 6.0,
      "score_min": 0.4
    }
  }
}
```

Beispiel-Response:

```json
{
  "access_token": "session-token",
  "token_type": "bearer",
  "user": {
    "slug": "alice",
    "email": "alice@example.com"
  }
}
```

#### `POST /v1/auth/login`

Zweck: meldet einen Nutzer per E-Mail und Passwort an und gibt einen Bearer-Token zurück.

Beispiel-Request:

```json
{
  "email": "alice@example.com",
  "password": "secret123"
}
```

Response-Struktur: wie Registrierung.

#### `GET /v1/me`

Zweck: liefert den aktuell authentifizierten Nutzer.

Header:

```http
Authorization: Bearer <access_token>
```

Beispiel-Response:

```json
{
  "slug": "alice",
  "email": "alice@example.com"
}
```

#### `GET /v1/me/taste-profile`

Zweck: lädt das gespeicherte Geschmacksprofil des aktuellen Nutzers.

Beispiel-Response:

```json
{
  "profile": {
    "schema_version": 1,
    "name": "Standardprofil",
    "selected_communities": ["C001"],
    "community_weights_raw": {
      "C001": 1.0
    },
    "filter_settings": {
      "rating_min": 6.0,
      "rating_max": 10.0,
      "score_min": 0.4,
      "score_max": 1.0
    }
  }
}
```

Wenn noch kein Profil gespeichert ist:

```json
{
  "profile": null
}
```

#### `PUT /v1/me/taste-profile`

Zweck: ersetzt das gespeicherte Geschmacksprofil des aktuellen Nutzers.

Request-Body: ein `TasteProfile`.

Response-Struktur: wie `GET /v1/me/taste-profile`.

#### Gemeinsames `TasteProfile`

Empfehlungs- und Playlist-Endpunkte akzeptieren weiterhin ein temporäres `profile` im Request. Gespeicherte Profile können über die Auth-Endpunkte geladen und vom Frontend als `profile` in Empfehlungs-Requests weitergereicht werden.

Minimalbeispiel:

```json
{
  "selected_communities": ["C001"],
  "community_weights_raw": {
    "C001": 1.0
  },
  "filter_settings": {
    "rating_min": 6.0,
    "rating_max": 10.0,
    "score_min": 0.4,
    "score_max": 1.0,
    "sort_mode": "deterministic",
    "serendipity": 0.0
  }
}
```

#### `POST /v1/recommendations/archive`

Zweck: berechnet persönliche Archivempfehlungen aus dem gesamten lokalen Review-Bestand.

Profilregel:

- Gast-Requests müssen `profile` im Body senden.
- Eingeloggte Requests dürfen `profile` weglassen; dann nutzt die API das gespeicherte Geschmacksprofil des aktuellen Nutzers.
- Wenn `profile` trotz Login im Body steht, gewinnt dieses temporäre Profil nur für diese Anfrage und überschreibt nichts.

Beispiel-Request:

```json
{
  "profile": {
    "selected_communities": ["C001"],
    "community_weights_raw": {
      "C001": 1.0
    },
    "filter_settings": {
      "rating_min": 6.0,
      "score_min": 0.4
    }
  },
  "limit": 20,
  "offset": 0
}
```

Beispiel-Response-Struktur:

```json
{
  "source": "archive",
  "total": 123,
  "limit": 20,
  "offset": 0,
  "generated_at": "2026-06-24T15:30:00+00:00",
  "items": [
    {
      "rank": 1,
      "review_id": 12345,
      "artist": "Artist",
      "album": "Album",
      "overall_score": 0.87,
      "source": "archive",
      "url": "https://www.plattentests.de/...",
      "year": 2024,
      "release_date": "2024-01-19",
      "rating": 8.0,
      "rating_effective": 8.0,
      "labels": "Label",
      "text_excerpt": "Kurzer Rezensionstext...",
      "score_display": "87% Fit",
      "playlist_available": true,
      "has_tracks": true,
      "matched_tags": [
        {
          "id": "C001",
          "label": "Indie Rock",
          "affinity": 0.91,
          "matched": true
        }
      ],
      "explanation_signals": {
        "matched_community_count": 2,
        "primary_matched_labels": ["Indie Rock", "Post-Punk"],
        "fit_level": "high"
      }
    }
  ]
}
```

#### `POST /v1/recommendations/new-reviews`

Zweck: berechnet persönliche Empfehlungen aus den neuesten Rezensionen. Kurzfristig bedeutet "neueste" die höchsten Review-IDs bzw. die letzten `newest_count` Einträge.

Profilregel: wie bei Archivempfehlungen. Die API berechnet immer gegen genau ein Profil: entweder temporär im Body oder gespeichert über den Bearer Token.

Beispiel-Request:

```json
{
  "profile": {
    "selected_communities": ["C001"],
    "community_weights_raw": {
      "C001": 1.0
    },
    "filter_settings": {
      "rating_min": 6.0,
      "score_min": 0.0
    }
  },
  "newest_count": 30,
  "limit": 20,
  "offset": 0
}
```

Response-Struktur: wie Archivempfehlungen, aber mit `"source": "new_reviews"`.

#### `POST /v1/playlists/export`

Zweck: erzeugt synchron eine transient nutzbare Playlist als TuneMyMusic-TXT oder CSV. Der Export wird nicht gespeichert.

Profilregel: wie bei Empfehlungen. Playlist-Exports speichern kein Profil und keine Playlist; sie verwenden nur das für diese Anfrage aufgelöste Geschmacksprofil.

Beispiel-Request:

```json
{
  "source": "new_reviews",
  "profile": {
    "selected_communities": ["C001"],
    "community_weights_raw": {
      "C001": 1.0
    },
    "filter_settings": {
      "rating_min": 6.0,
      "score_min": 0.0
    }
  },
  "playlist_name": "Plattenradar 2026-06-24",
  "target_count": 30,
  "taste_exponent": 1.0,
  "selection_strategy": "stratified",
  "format": "txt",
  "newest_count": 30,
  "archive_limit": 200
}
```

Beispiel-Response-Struktur:

```json
{
  "source": "new_reviews",
  "name": "Plattenradar 2026-06-24",
  "format": "txt",
  "filename": "Plattenradar-2026-06-24.txt",
  "content_type": "text/plain",
  "content": "Artist - Song\nOther Artist - Other Song",
  "items": [
    {
      "review_id": 12345,
      "artist": "Artist",
      "album": "Album",
      "track_title": "Song",
      "source_kind": "highlight",
      "score_weight": 0.12,
      "raw_score": 0.87
    }
  ]
}
```

#### Spätere API-Bereiche

Noch nicht gebaut:

- `GET /v1/taste-profiles`
- `POST /v1/taste-profiles`
- `GET /v1/taste-profiles/{profile_id}`
- `PUT /v1/taste-profiles/{profile_id}`
- `POST /v1/taste-profiles/{profile_id}/make-default`
- `GET /v1/reviews/{review_id}`
- optional: `GET /v1/reviews?query=&artist=&year_min=&year_max=`

Spätere Profilregeln:

- Request kann ein temporäres `profile` enthalten.
- Request kann ein `profile_id` enthalten.
- Ohne beides nutzt die API bei eingeloggten Nutzern das Default-Profil.
- Bei Gästen ist ein `profile` im Request erforderlich.

### API-Smoke-Test

Der lokale API-Schnitt kann gegen echte lokale Daten geprüft werden:

```bash
hatch run api --host 127.0.0.1 --port 8000
hatch run api-smoke
```

Der Smoke-Test prüft:

- `GET /health`,
- `GET /v1/presets`,
- `POST /v1/recommendations/archive`,
- `POST /v1/recommendations/new-reviews`,
- `POST /v1/playlists/export`.

### Service-Schicht

Vor FastAPI sollte die fachliche Logik aus Streamlit in Services überführt werden:

- `TasteProfileService`,
- `RecommendationService`,
- `ReviewService`,
- `PlaylistExportService`,
- `AccountService`.

Migrationsziel:

- Berechnungen aus `pages/` herauslösen, sofern sie nicht reine UI sind.
- DTO-/Schema-Aufbereitung von HTML-Rendering trennen.
- Karteninhalte als JSON liefern, nicht als HTML-Strings.
- Streamlit kann während der Migration dieselben Services konsumieren.

### Nächste technische Meilensteine

Empfohlene Reihenfolge:

1. Pydantic-/Domain-Modelle für `TasteFilterSettings`, `TasteProfile`, `Recommendation`, `PlaylistExport`.
2. Preset-Konfiguration als Code oder JSON/YAML-Konfiguration.
3. Empfehlungslogik aus `pages/recommendations_pool.py` in einen Service ziehen.
4. Neueste-Reviews-Ranking in denselben Service integrieren.
5. Playlist-Export-Service stabilisieren.
6. Tests für Profile, Presets, Empfehlungen und Playlist-Export.
7. Danach FastAPI-Endpunkte.

## Offene Punkte

- Preset-Werte gegen echte Beispielprofile kalibrieren.
- Finale Begriffe für Stilpassung, Liste variieren und Fokus vs. Breite finden.
- Formeln gemeinsam in Nutzersprache übersetzen.
- Plattenlabel-Expertenfilter visuell einordnen.
- Auth technisch konkretisieren: Passwort-Hashing, Session/Cookie, Reset-Fluss.
- `first_seen_at` / `scraped_at` in der Pipeline planen.
- Neues Frontend erst nach Service-/API-Schnitt konkret planen.

## Entscheidungslog

Die folgenden Abschnitte dokumentieren die chronologische Herleitung der Spezifikation. Die konsolidierte v1-Spezifikation oben ist die aktuelle Arbeitsgrundlage.

## Ziel

Plattenradar v1 soll aus den Daten von plattentests.de einen persönlichen Musik-Assistenten machen: Nutzer sollen passende Musik aus dem großen Review-Archiv entdecken und neue relevante Rezensionen automatisch als hörbare Auswahl erhalten.

## Interviewstatus

- Runde 1: Produktkern beantwortet und verdichtet.
- Runde 2: Onboarding und Geschmacksprofil beantwortet und verdichtet.
- Runde 3: Account, Speicherung, E-Mail und Playlist-Zustellung beantwortet und verdichtet.
- Runde 4: Zielseiten, Navigation und erster Erfolgsfluss beantwortet und verdichtet.
- Runde 5: Bestehende Streamlit-Funktionalität, Scope und Migrationshaltung beantwortet und verdichtet.
- API-/Datenmodell-Spezifikation v0 ergänzt.
- Entscheidungsrunden zu Auth, Filtern, Erklärbarkeit, Playlist-Export, Ergebnislisten und Presets ergänzt.

## Runde 1: Produktkern

### Wichtigster Nutzer

Primäre Nutzer sind zunächst der Projektbetreiber selbst und sein Freundeskreis. Plattenradar ist ein Hobbyprojekt, aber mit professionellem Anspruch: Es soll zeigen, wie weit eine hochwertige Website mit KI-Unterstützung als Einzelperson gebaut werden kann.

Als gedankliche Zielgruppe steht die Leserschaft von plattentests.de im Mittelpunkt: musikinteressierte, neugierige, eher nerdige Hörer, die Freude an Rezensionen, Referenzen und Entdeckungen haben. Die Anwendung muss nicht von Anfang an für Tausende Nutzer skaliert sein, soll sich aber so anfühlen, dass sie perspektivisch auch für die plattentests.de-Community relevant werden könnte.

Langfristige Möglichkeit: Plattenradar könnte zu einem ergänzenden Angebot rund um plattentests.de werden oder sogar gemeinsam mit plattentests.de betrieben werden.

### Was Plattenradar besser machen soll als plattentests.de

Plattenradar soll plattentests.de nicht ersetzen, sondern ergänzen. plattentests.de bleibt die kulturelle und redaktionelle Basis; Plattenradar nutzt diese Daten systematisch, um daraus persönliche Musikentdeckung zu machen.

Zwei Kernprobleme sollen gelöst werden:

1. **Vergangene Musik neu entdecken**
   Seit 1999 sind sehr viele Rezensionen entstanden. Viele relevante Alben aus der Zeit vor dem eigenen Einstieg als Leser bleiben unentdeckt. Plattenradar soll helfen, solche vergessenen oder nie gehörten Perlen sichtbar zu machen.

2. **Neue Rezensionen effizient hörbar machen**
   plattentests.de veröffentlicht typischerweise wöchentlich neue Rezensionen. Nutzer mit wenig Zeit sollen nicht jede Rezension lesen müssen, sondern automatisch eine relevante Auswahl der neuen Musik erhalten, idealerweise als Playlist oder playlistnahes Exportformat.

Der zentrale Mehrwert liegt nicht nur im Hinweis auf spannende Künstler oder Alben, sondern darin, Musik schnell ausprobieren zu können. Playlist-Generierung ist deshalb kein Randfeature, sondern ein wichtiger Bestandteil des Nutzungserlebnisses.

### Wichtigster Aha-Moment

Der wichtigste Aha-Moment entsteht, wenn die vorgeschlagene Musik wirklich zum Geschmack des Nutzers passt. Wenn die Empfehlungen nicht passen, trägt die gesamte Website nicht.

Produktversprechen:

> Plattenradar kennt meinen Musikgeschmack gut genug, um mir aus alten und neuen plattentests.de-Rezensionen hörenswerte Musik vorzuschlagen.

### Hauptrolle der Anwendung

Plattenradar ist in v1 eher ein persönlicher Musik-Assistent als ein reines Review-Dashboard.

Das Dashboard bleibt wichtig, weil Nutzer Musikgeschmäcker, Profile, Rezensionen und Referenzen explorieren wollen. Die Hauptbewegung ist aber persönlich: Die Anwendung soll helfen, neue oder vergessene Musik zu finden, die zum eigenen Geschmack passt.

Arbeitsdefinition:

> Ein persönlicher Musik-Assistent mit explorativen Review-Werkzeugen.

### Nutzungshäufigkeit

Für neue Rezensionen soll die Nutzung möglichst passiv und automatisiert sein. Nutzer sollen Plattenradar nicht regelmäßig aktiv öffnen müssen, nur um zu prüfen, ob neue relevante Rezensionen erschienen sind. Stattdessen ist eine automatisch erzeugte Auswahl oder Playlist zentral, die zum Beispiel per E-Mail erreichbar ist.

Für Archiv-Entdeckung ist die Nutzung eher gelegentlich: Wenn musikalische Flaute herrscht oder Nutzer aktiv neue Musik suchen, besuchen sie Plattenradar und generieren eine passende Playlist oder Empfehlungsauswahl aus dem Backkatalog.

## Abgeleitete Produktthese v1

Plattenradar v1 hilft musikinteressierten plattentests.de-Lesern mit wenig Zeit, aus dem riesigen Review-Archiv und aus wöchentlichen Neuerscheinungen genau die Musik zu finden und anzuhören, die zu ihrem Geschmack passt.

Der Kern ist nicht "mehr Daten anzeigen", sondern "passende Musik hörbar machen".

## Erste Anforderungen

### Muss in v1 geklärt werden

- Nutzer müssen ihren Musikgeschmack ausdrücken können.
- Plattenradar muss daraus ein verständliches Geschmacksprofil ableiten.
- Empfehlungen müssen sowohl neue Rezensionen als auch Archivmaterial abdecken.
- Empfehlungen müssen direkt in eine hörbare Form überführbar sein, mindestens als Playlist-Export oder playlistnahe Liste.
- Neue Rezensionen sollen automatisiert verarbeitet und für Nutzerprofile ausgewertet werden können.
- Nutzer sollen perspektivisch per E-Mail erreichbar sein, insbesondere für Benachrichtigungen und Playlist-Zustellung.
- Nutzer sollen Empfehlungen ohne vorherige Anmeldung erzeugen können, aber nicht ohne vorherige Geschmacksangaben.
- Gespeicherte Profile und automatische E-Mail-/Playlist-Zustellung setzen einen angemeldeten Nutzer voraus.

### Noch offen

- Welches Playlist-Zielformat ist für v1 ausreichend?
- Welche Rolle spielen Streaming-Dienste direkt in v1?
- Wie viel Exploration braucht die Oberfläche zusätzlich zum Assistentenfluss?
- Wie genau sieht der Übergang von temporärem Geschmacksprofil zu gespeichertem Nutzerprofil aus?
- Welche Account-Variante passt zu v1: Magic Link per E-Mail, Passwort, OAuth oder etwas Einfacheres?
- Welche gespeicherten Profildaten existieren bereits im Code und müssen in ein künftiges Backend-Modell übernommen werden?
- Wie wird ein neues Frontend die bestehende Streamlit-Funktionalität vollständig, aber besser strukturiert abbilden?
- Welche API-Ressourcen und Endpunkte braucht die v1, damit das neue Frontend nicht an Streamlit gekoppelt ist?

## Runde 2: Onboarding und Geschmacksprofil

### Empfehlungen erst nach Geschmacksangaben

Ein neuer Nutzer soll nicht ohne eigene Angaben personalisierte Empfehlungen erhalten. Personalisierung ohne Eingabe wäre fachlich nicht glaubwürdig. Es kann zwar öffentliche Inhalte wie aktuelle Rezensionen geben, aber das wäre kein eigentlicher Mehrwert gegenüber plattentests.de.

Für personalisierte Empfehlungen braucht der Nutzer zuerst ein Geschmacksprofil. Dieses Profil meint nicht zwingend ein Benutzerkonto, sondern die fachliche Beschreibung des Musikgeschmacks.

Wichtige Unterscheidung:

- **Temporäres Geschmacksprofil:** Der Nutzer durchläuft die bestehende Schritt-1-/Schritt-2-/Schritt-3-Logik, gibt Musikrichtungen und Gewichtungen an und kann danach Empfehlungen erzeugen.
- **Gespeichertes Nutzerprofil:** Der Nutzer meldet sich an oder registriert sich, damit seine Präferenzen dauerhaft geladen, verändert und für spätere Automatisierungen verwendet werden können.

Der schwierige Produkt- und UX-Punkt ist der Übergang zwischen diesen Zuständen. Die Anwendung muss jederzeit klar anbieten:

- ein neues Geschmacksprofil zu erstellen,
- ein bestehendes Profil zu laden,
- ein temporäres Profil nach erfolgreichem Ausprobieren zu speichern,
- ein gespeichertes Profil später zu ändern.

### Geschmacksbeschreibung

Die Mechanik zur Beschreibung des Musikgeschmacks ist bereits implementiert und soll nicht neu erfunden werden. Sie besteht aus einem mehrstufigen Prozess mit Musikrichtungen, Gewichtungen und daraus berechneten Empfehlungsgewichten.

Produktplanung soll sich daher nicht primär mit einer neuen Geschmackslogik beschäftigen, sondern mit:

- verständlicher Führung durch den bestehenden Prozess,
- besserer Erklärung der Gewichtungen,
- klarerem Erwartungsmanagement,
- sauberer Einbettung in Onboarding, Profil und Empfehlungsergebnis.

### Mehrere Geschmacksprofile

Für v1 ist pro Nutzer zunächst ein Geschmacksprofil vorgesehen. Mehrere Profile pro Nutzer sind ein mögliches späteres Feature, zum Beispiel für unterschiedliche Stimmungen, Kontexte oder Musikmodi.

V1-Entscheidung:

> Ein Nutzer hat genau ein aktives gespeichertes Geschmacksprofil.

Später denkbar:

- Standardprofil,
- ruhige Musik,
- Sport/Laufen,
- Archivsuche,
- neue Rezensionen,
- Genre- oder Jahrzehntprofile.

### Präzision vs. Entdeckung

Die Spannung zwischen "nur sehr passende Musik" und "mehr Entdeckung, aber höheres Risiko für unpassende Vorschläge" soll nicht fest durch das Produkt entschieden werden. Nutzer sollen diese Balance über Filter, Gewichtungen und vorhandene Optionen selbst steuern können.

Wichtig ist, dass die UI diese Stellschrauben besser erklärt. Nutzer sollen verstehen, was passiert, wenn sie strenger oder offener filtern.

Produktanforderung:

> Plattenradar muss erklären, wie Gewichtungen und Filter die Empfehlungen beeinflussen, ohne die Nutzer mit technischer Logik zu überfordern.

### Erklärbarkeit der Empfehlungen

Nachvollziehbarkeit ist wichtig und passt zum Anspruch des Projekts als Data-Science-Portfolio. Plattenradar soll nicht nur Empfehlungen ausgeben, sondern zeigen, warum etwas empfohlen wurde.

Bestehende Elemente:

- Empfehlungen enthalten Labels zu Musikrichtungen.
- Labels, die zu den Nutzerpräferenzen passen, werden visuell hervorgehoben.

Aktuelles Problem:

- Die Erklärung ist zu subtil.
- Die Bedeutung der hervorgehobenen Labels ist nicht ausreichend beschrieben.

Ziel:

> Plattenradar soll als Beispiel für erklärbare Data Science funktionieren: Nutzer verstehen grob, warum ein Album in ihrer Auswahl landet, und Arbeitgeber können erkennen, dass hinter dem Projekt mehr steckt als eine einfache Liste.

## Abgeleitete UX-Anforderungen aus Runde 2

- Der erste Nutzerfluss startet mit Geschmacksangaben, nicht mit Registrierung.
- Anmeldung wird als Speichern, Wiederverwenden und Automatisieren des Profils erklärt.
- Die Anwendung braucht klare Zustände: kein Profil, temporäres Profil, gespeichertes Profil, geladenes Profil.
- Empfehlungen dürfen erst nach einem fachlichen Geschmacksprofil erscheinen.
- Playlist-Zustellung per E-Mail ist nur für angemeldete Nutzer verfügbar.
- Die bestehende Schritt-1-/Schritt-2-/Schritt-3-Logik bleibt fachliche Grundlage.
- V1 unterstützt ein gespeichertes Profil pro Nutzer.
- Die UI muss Gewichtungen, Filter und Empfehlungserklärungen deutlich besser vermitteln.

## Runde 3: Account, Speicherung, E-Mail und Playlist-Zustellung

### Login und Identität

Für v1 soll es keinen separaten Benutzernamen geben müssen. E-Mail liegt nahe, weil dieselbe Adresse später auch für Playlist-Zustellung und Benachrichtigungen verwendet werden kann.

Die genaue Auth-Variante ist noch offen und soll später technisch beraten werden. Denkbare Varianten:

- E-Mail mit Magic Link,
- E-Mail und Passwort,
- OAuth über externe Anbieter,
- eine bewusst einfache frühe Lösung für den kleinen Nutzerkreis.

Produktseitig ist wichtiger als die konkrete Technik:

> Ein Account dient nicht dem Einstieg, sondern dem Speichern, Wiederverwenden und Automatisieren eines Geschmacksprofils.

### Zeitpunkt der Speicheraufforderung

Der Zeitpunkt, an dem Plattenradar zum Speichern auffordert, ist ein zentraler UX-Knackpunkt.

Mögliche Speicherpunkte:

- direkt nach Erstellung des Geschmacksprofils,
- nach den ersten Archivempfehlungen,
- nach den ersten Empfehlungen zu aktuellen Rezensionen,
- wenn der Nutzer eine Playlist erzeugen oder automatische Zustellung aktivieren möchte,
- auf einer Übersichts-/Menüseite nach dem Profilprozess.

Der Nutzer soll vermutlich früh die Möglichkeit zum Speichern sehen, aber die App darf den eigentlichen Aha-Moment nicht durch Registrierung blockieren.

Offene Flow-Frage:

> Was passiert unmittelbar nach dem Geschmacksprofil?

Drei denkbare Zielrichtungen:

1. **Archiv-Aha zuerst:** "Das sind die besten Empfehlungen aus den letzten 25 Jahren."
2. **Aktuelles zuerst:** "Das sind die besten neuen Rezensionen für dich."
3. **Auswahlseite zuerst:** Der Nutzer entscheidet zwischen Archiv entdecken, neue Rezensionen ansehen, Playlist erzeugen oder Profil speichern.

Diese Entscheidung ist für den neuen Frontend-Flow wichtiger als die technische Auth-Frage.

### Gespeicherte Daten

Welche Profildaten genau gespeichert werden, ist bereits durch die bestehende Implementierung vorgeprägt und soll später aus dem Code abgeleitet werden.

Zu prüfen:

- Welche Gewichtungen und Filter existieren aktuell?
- Welche Werte sind notwendig, um Empfehlungen reproduzierbar neu zu berechnen?
- Welche Werte sind reine UI-Zustände und müssen nicht dauerhaft gespeichert werden?
- Gibt es bereits gespeicherte Empfehlungsergebnisse oder nur Profilparameter?

V1-Arbeitshypothese:

> Gespeichert wird zunächst das fachliche Geschmacksprofil, nicht zwingend jede generierte Empfehlungshistorie.

### Automatische Playlist-Zustellung

Playlist-Zustellung ist ein wichtiges Zukunftsfeature, muss aber nicht vollständig in v1 umgesetzt sein. Es soll architektonisch mitgedacht werden.

Naheliegende frühe Variante:

- Plattenradar erzeugt eine Textdatei oder CSV-Datei mit Track-/Albuminformationen.
- Diese Datei wird per E-Mail zugestellt oder als Download angeboten.
- Der Nutzer importiert sie manuell in einen Dienst wie TuneMyMusic.

TuneMyMusic ist relevant, weil der Dienst Playlist-Transfers zwischen Streaming-Anbietern unterstützt und auch Schnittstellen für URLs, Textdateien oder einfachen Text bietet.

Langfristig denkbar:

- weniger manueller Export/Import,
- direktere Integration mit Streaming-Diensten,
- automatisierte Playlist-Erstellung,
- bessere Rückmeldung, welche Tracks erfolgreich gefunden wurden.

Produktentscheidung für v1:

> Playlist-Automatisierung muss im Modell vorbereitet werden, kann aber zunächst als manueller Export gedacht werden.

### Wöchentliche Empfehlungen bei schwachen Batches

Wenn es in einer Woche keine stark passenden neuen Rezensionen gibt, soll nicht einfach keine Mail kommen. Es gibt immer eine relativ beste Auswahl.

Die E-Mail oder Wochenansicht soll die Qualität des aktuellen Review-Batches einordnen können, zum Beispiel:

- diese Woche passt besonders gut,
- diese Woche ist eher mau,
- wir haben trotzdem die besten 20 bis 30 Empfehlungen ausgewählt,
- bei Bedarf wurden die Filter etwas weicher interpretiert.

Neue Produktanforderung:

> Plattenradar sollte pro wöchentlichem Review-Batch eine Einschätzung erzeugen, wie gut die neuen Rezensionen zum Nutzerprofil passen.

Das schafft Transparenz und schützt vor falschen Erwartungen.

## Abgeleitete UX- und API-Anforderungen aus Runde 3

- Accounts sollten in v1 ohne Benutzernamen auskommen.
- Die konkrete Auth-Methode bleibt offen und wird später technisch entschieden.
- Speichern ist ein Nutzenangebot, kein Pflichtschritt vor der ersten Empfehlung.
- Der Flow nach dem Geschmacksprofil ist die zentrale UX-Entscheidung.
- Gespeicherte Profildaten müssen aus der bestehenden Empfehlungslogik abgeleitet werden.
- Playlist-Zustellung soll als späterer Job/Export mitgedacht werden.
- Ein erstes Playlistformat kann Text oder CSV sein.
- Wöchentliche Empfehlungsläufe brauchen eine Qualitäts- oder Fit-Einschätzung pro Nutzerprofil.

## Runde 4: Zielseiten, Navigation und erster Erfolgsfluss

### Erster Ergebnisbildschirm nach dem Geschmacksprofil

Nach Erstellung des Geschmacksprofils soll der erste überzeugende Ergebnisbildschirm die Archivempfehlungen zeigen.

Begründung:

- Das Archiv-Aha zeigt sofort, was Plattenradar gegenüber plattentests.de zusätzlich leistet.
- Der Nutzer bekommt nicht nur aktuelle Inhalte, sondern eine persönliche Auswahl aus vielen Jahren Review-Geschichte.
- Der erste Nutzenmoment wird emotional stärker: "Hier sind vergessene oder unbekannte Alben, die zu mir passen."

V1-Entscheidung:

> Nach dem Geschmacksprofil führt Plattenradar zuerst zu persönlichen Archivempfehlungen.

Direkt auf dieser Seite sollten weitere Aktionen sichtbar sein:

- Profil speichern,
- neue Rezensionen ansehen,
- Playlist erzeugen,
- Filter/Geschmack anpassen.

### Hauptbereiche der App

Für das neue Frontend zeichnen sich diese Hauptbereiche ab:

1. **Profil**
   Geschmacksprofil anzeigen, bearbeiten, speichern und später laden.

2. **Neue Rezensionen**
   Neue plattentests.de-Rezensionen, sortiert und bewertet anhand des Nutzerprofils.

3. **Archiv entdecken**
   Empfehlungen aus dem gesamten lokalen Review-Bestand.

4. **Playlists**
   Manuelle Playlist-Erzeugung und perspektivisch Verwaltung automatischer Playlist-Zustellung.

5. **Einstellungen**
   Konto, E-Mail, Benachrichtigungen und möglicherweise regelmäßige Playlist-Konfiguration.

Offen bleibt, ob Playlist-Konfiguration als eigener Hauptbereich oder als Teil der Einstellungen geführt wird. Für v1 kann Playlists ein eigener sichtbarer Bereich sein, weil "passende Musik hörbar machen" ein Kernversprechen ist.

### Archiv und neue Rezensionen

Archivempfehlungen und neue Rezensionen sind fachlich verwandt, sollen aber im Produkt als getrennte Bereiche behandelt werden.

Grund:

- Die Nutzerabsicht ist unterschiedlich.
- Archiv heißt: "Ich suche neue Musik aus 25 Jahren."
- Neue Rezensionen heißt: "Was ist diese Woche relevant für mich?"
- Die Berechnung kann ähnlich sein, aber die Oberfläche darf diese Modi klar trennen.

V1-Entscheidung:

> Archiv entdecken und Neue Rezensionen sind zwei getrennte Bereiche, nutzen aber gemeinsame Karten-, Ranking- und Erklärlogik.

### Empfehlungskarten

Die bestehende Empfehlungskarte ist bereits implementiert und soll als funktionaler Ausgangspunkt gelten. Aus dem Streamlit-Prototyp ergibt sich folgender Mindestinhalt:

- Rang/Position,
- Künstler und Album,
- Link zur plattentests.de-Rezension,
- Release-Datum oder Jahr,
- plattentests.de-Wertung, bei fehlender Wertung mit Annahme,
- Empfehlungsscore,
- Plattenlabel,
- Community-/Genre-Tags mit Gewichtungsfarbe,
- Hervorhebung der Tags, die zu den Nutzerpräferenzen passen,
- kurzer Rezensionstext-Ausschnitt.

Für das neue Frontend ist nicht nur der Inhalt wichtig, sondern auch die Verständlichkeit:

- Was bedeutet der Score?
- Warum ist ein Tag hervorgehoben?
- Warum steht dieses Album auf diesem Rang?
- Welche Aktion kann der Nutzer als Nächstes ausführen?

Zusätzliche denkbare Aktionen pro Karte:

- zur Playlist hinzufügen,
- ausblenden,
- "passt" / "passt nicht" markieren,
- Rezension öffnen,
- später anhören.

Diese Aktionen sind nicht automatisch v1-Pflicht, sollten aber beim Komponentendesign mitgedacht werden.

### Streamlit als Prototyp, nicht Zieloberfläche

Die bestehende Streamlit-App ist ein funktionaler Prototyp, soll aber durch ein sauber gebautes Frontend abgelöst werden. Ziel ist nicht, Streamlit kosmetisch zu perfektionieren, sondern die vorhandenen Funktionen zu verstehen, fachlich zu sichern und in eine bessere Produktstruktur zu überführen.

Aktuell im Prototyp sichtbar:

- Start,
- Konto / Konto anlegen,
- Einstieg,
- Genre / Stil,
- Filter,
- Entdecken-Hub,
- Empfehlungen,
- Neueste Rezensionen,
- Playlist erzeugen.

Problem:

- Die Funktionalität ist vorhanden, aber der Flow ist nicht klar genug.
- Nutzerführung, visuelle Hierarchie und Übergänge zwischen Profil, Empfehlungen, Speichern und Playlists müssen neu gedacht werden.

V1-Ziel:

> Das neue Frontend soll die bestehende Funktionalität nicht verlieren, sondern als klareren Assistentenfluss mit stabilen Hauptbereichen neu organisieren.

## Abgeleitete UX-Anforderungen aus Runde 4

- Nach dem Geschmacksprofil kommt zuerst die Archivempfehlungsseite.
- Archivempfehlungen werden zum ersten Aha-Moment.
- Neue Rezensionen und Archivempfehlungen bleiben getrennte Hauptbereiche.
- Beide Empfehlungsbereiche teilen sich Karten-, Ranking- und Erklärungskomponenten.
- Playlists erhalten einen sichtbaren Produktbereich, auch wenn automatische Zustellung später kommt.
- Das neue Frontend muss die vorhandene Streamlit-Funktionalität funktional abdecken.
- Die Empfehlungskarte braucht verständlichere Erklärungen und klarere nächste Aktionen.

## Runde 5: Funktionsumfang, Scope und Migrationshaltung

### Unverzichtbare v1-Funktionen

Die neue App soll die bereits implementierten Kernfunktionen nicht verlieren. Für v1 unverzichtbar sind:

- Geschmacksprofil-Schritt 1 bis 3,
- Archivempfehlungen,
- neueste Rezensionen bzw. Empfehlungen auf Basis neuer Rezensionen,
- Playlist-Erzeugung und Playlist-Export,
- Profil speichern,
- Profil laden,
- Konto anlegen.

Diese Funktionen bilden den aktuellen fachlichen Kern des Prototyps und müssen beim Wechsel auf ein neues Frontend erhalten bleiben.

### Funktionen oder UI-Elemente, die nicht heilig sind

Der aktuelle Entdecken-Hub mit Kachelstruktur ist keine fachliche Pflichtfunktion. Er ist eine Navigations- oder Zwischenschicht im Streamlit-Prototyp. Die darunterliegenden Ziele müssen erreichbar bleiben, aber die Kachelstruktur selbst kann im neuen Frontend ersetzt, reduziert oder anders gelöst werden.

Nicht zwingend v1-pflichtig oder später ausbaubar:

- bestehende Hub-Kachelstruktur,
- Playlist-Automatisierung,
- umfangreiche Konto-Verwaltung jenseits von Speichern und Laden,
- Pagination als exakt gleiche Interaktion wie im Prototyp.

Weiterhin wichtig:

- Filterdetails sollen erhalten bleiben.
- Konto bedeutet für v1 vor allem: Musikgeschmack speichern und wieder laden.

### Neues Frontend und Zukunftsfunktionen

Das neue Frontend soll zuerst die vorhandene Funktionalität schöner, klarer und professioneller abbilden. Gleichzeitig sollen Account-, E-Mail- und Playlist-Zukunft architektonisch mitgedacht werden.

Produktentscheidung:

> Nicht alle Zukunftsfeatures müssen sofort sichtbar fertig sein, aber das Datenmodell und die API sollten sie nicht verbauen.

### Streamlit während der Migration

Architektonisch besteht freie Hand. Der alte Streamlit-Prototyp darf schrittweise ersetzt werden, sollte aber während der Übergangsphase möglichst weiter funktionieren, solange das keinen unverhältnismäßigen Aufwand erzeugt.

Pragmatische Migrationshaltung:

- Fachlogik aus Streamlit-Seiten in wiederverwendbare Python-Services ziehen.
- Neue API gegen diese Services bauen.
- Streamlit kann währenddessen dieselbe Logik weiter nutzen oder als Prototyp nebenher bestehen bleiben.
- Das neue Frontend ersetzt nach und nach die eigentliche Nutzeroberfläche.

### Nächster Meilenstein

Die Produkt-/UX-Richtung ist jetzt ausreichend klar, um nicht weiter rein abstrakt zu planen. Der nächste richtige Schritt ist aus aktueller Sicht:

> API- und Datenmodell-Schnitt aus der bestehenden Streamlit-Funktionalität ableiten.

Begründung:

- Der Produktkern ist geklärt.
- Die unverzichtbaren Funktionen sind benannt.
- Die größte technische Gefahr ist nun, dass das neue Frontend direkt wieder an UI-Zustände statt an klare Produktressourcen gekoppelt wird.
- Ein API-Schnitt zwingt dazu, User, Geschmacksprofil, Empfehlungen, neue Rezensionen und Playlist-Export sauber zu modellieren.

## Abgeleitete Anforderungen aus Runde 5

- Der neue Frontend-Schnitt muss alle v1-Pflichtfunktionen abdecken.
- Der bestehende Hub ist optional; seine Ziele bleiben erforderlich.
- Filterdetails bleiben fachlich erhalten.
- Konto-v1 bedeutet primär Speichern und Laden des Geschmacksprofils.
- Playlist-Automatisierung ist Zukunft, Playlist-Erzeugung und Export sind v1.
- Die Migration soll fachliche Logik aus Streamlit herauslösen, ohne unnötig alles auf einmal abzureißen.
- Der nächste Meilenstein ist eine API-/Datenmodell-Spezifikation.

## API-/Datenmodell-Spezifikation v0

Diese Spezifikation beschreibt den gewünschten Produkt- und API-Schnitt für ein neues Frontend. Sie ist noch kein Implementierungsplan bis auf Methodenebene, aber konkret genug, um daraus FastAPI-Routen, Pydantic-Modelle und Services abzuleiten.

### Grundprinzipien

- Das neue Frontend spricht nicht direkt mit Streamlit-Session-State.
- Fachlogik wird in wiederverwendbare Python-Services verschoben.
- Streamlit darf während der Migration weiter existieren, soll aber nicht mehr die fachliche Quelle der Wahrheit sein.
- Gäste können ein temporäres Geschmacksprofil erzeugen und Empfehlungen sehen.
- Angemeldete Nutzer können ihr Geschmacksprofil speichern, laden und später Automatisierungen aktivieren.
- Archivempfehlungen und neue Rezensionen sind getrennte Produktbereiche, teilen sich aber Bewertungs-, Karten- und Erklärlogik.

### Zentrale Zustände

#### Kein Geschmacksprofil

Der Nutzer hat noch keine musikalischen Präferenzen angegeben.

Erlaubt:

- Startseite sehen,
- öffentliche Informationen sehen,
- Geschmacksprofil starten,
- anmelden oder Konto anlegen.

Nicht erlaubt:

- personalisierte Empfehlungen,
- personalisierte Playlist-Erzeugung,
- automatische Zustellung.

#### Temporäres Geschmacksprofil

Der Nutzer hat Schritt 1 bis 3 abgeschlossen, ist aber nicht angemeldet oder hat das Profil nicht gespeichert.

Erlaubt:

- Archivempfehlungen sehen,
- neueste Rezensionen personalisiert sortieren,
- Playlist-Export manuell erzeugen,
- Profil speichern als nächsten Schritt angeboten bekommen,
- Geschmack und Filter ändern.

Nicht erlaubt oder nur eingeschränkt:

- Profil dauerhaft wiederverwenden,
- E-Mail-Zustellung,
- automatische Playlist-Abos.

#### Gespeichertes Profil

Der Nutzer hat ein Konto und ein gespeichertes Geschmacksprofil.

Erlaubt:

- Profil laden,
- Profil ändern und erneut speichern,
- Empfehlungen reproduzierbar berechnen,
- Playlist-Export erzeugen,
- später E-Mail- und Automatisierungsfunktionen aktivieren.

### Ressourcen

#### User

Repräsentiert eine Person oder ein Konto.

Vorläufige Felder:

```json
{
  "id": "user_123",
  "email": "name@example.com",
  "display_name": null,
  "created_at": "2026-06-21T12:00:00Z",
  "updated_at": "2026-06-21T12:00:00Z"
}
```

Hinweise:

- `email` ist wahrscheinlich der natürliche Login-Identifier.
- Ein separater Benutzername ist für v1 nicht erforderlich.
- Die aktuelle Implementierung nutzt noch `slug`; dieser sollte in einer neuen API nicht zwingend als Produktbegriff sichtbar sein.

Offen:

- Auth-Methode: Magic Link, Passwort, OAuth oder einfache frühe Lösung.

#### TasteProfile

Repräsentiert die fachliche Beschreibung des Musikgeschmacks.

Aus der bestehenden Implementierung bekannte Felder:

```json
{
  "id": "profile_123",
  "user_id": "user_123",
  "schema_version": 1,
  "name": "Standardprofil",
  "flow_mode": null,
  "selected_communities": ["C001", "C042"],
  "artist_flow_selected_communities": ["C001"],
  "genre_flow_selected_communities": ["C042"],
  "community_weights_raw": {
    "C001": 1.0,
    "C042": 0.6
  },
  "filter_settings": {
    "year_min": 1999,
    "year_max": 2026,
    "rating_min": 6.0,
    "rating_max": 10.0,
    "score_min": 0.0,
    "score_max": 1.0,
    "sort_mode": "fixed",
    "serendipity": 0.0,
    "community_spectrum_crossover": 0.5,
    "overall_weight_alpha": 1.0,
    "overall_weight_beta": 1.0,
    "overall_weight_gamma": 1.0,
    "plattenlabel_selection": []
  },
  "created_at": "2026-06-21T12:00:00Z",
  "updated_at": "2026-06-21T12:00:00Z"
}
```

Hinweise:

- V1 unterstützt genau ein aktives gespeichertes Profil pro Nutzer.
- Das API-Modell sollte trotzdem eine eigene Ressource `TasteProfile` haben, damit mehrere Profile später möglich bleiben.
- Für Gäste kann dasselbe Objekt ohne `id` und `user_id` als temporäres Profil verwendet werden.
- `filter_settings` sollte im Code später in ein stärker typisiertes Modell überführt werden, auch wenn es aktuell als Dict gespeichert wird.

#### Review

Repräsentiert eine plattentests.de-Rezension.

Bekannte Felder aus dem Domain-Modell:

```json
{
  "id": 123,
  "url": "https://www.plattentests.de/rezi.php?show=...",
  "artist": "Artist",
  "album": "Album",
  "title": null,
  "author": null,
  "labels": ["Label"],
  "release_date": "2024-01-19",
  "release_year": 2024,
  "rating": 8.0,
  "user_rating": null,
  "text_excerpt": "Kurzer Auszug ...",
  "references": ["Referenzartist"]
}
```

Hinweise:

- Die API sollte nicht zwingend den kompletten Rezensionstext im Listen-Endpunkt liefern.
- Für Karten reicht zunächst ein kurzer Auszug.
- Detail-Endpunkte können später vollständige Reviewdaten liefern.

#### Recommendation

Repräsentiert ein bewertetes Album für ein bestimmtes Geschmacksprofil.

Felder aus bestehender Empfehlungslogik:

```json
{
  "rank": 1,
  "review_id": 123,
  "artist": "Artist",
  "album": "Album",
  "url": "https://www.plattentests.de/rezi.php?show=...",
  "release_date": "2024-01-19",
  "year": 2024,
  "rating": 8.0,
  "rating_effective": 8.0,
  "score": 0.72,
  "overall_score": 0.84,
  "k_hits": 2,
  "purity_raw": 0.65,
  "breadth_raw": 0.48,
  "hits_pct": 48.0,
  "labels": "Label A, Label B",
  "text_excerpt": "Kurzer Auszug ...",
  "top_communities": [
    {
      "id": "C001",
      "label": "Indie Rock",
      "affinity": 0.81,
      "matched_user_preference": true
    }
  ],
  "explanation": {
    "summary": "Passt vor allem wegen Indie Rock und hoher Affinität zu deinem Profil.",
    "matched_labels": ["Indie Rock"],
    "score_parts": [
      {
        "label": "Stilnähe",
        "value": 0.72
      }
    ]
  }
}
```

Hinweise:

- `matched_user_preference` ist im Streamlit-Prototyp aktuell implizit über Hervorhebung gelöst. In der API sollte es explizit werden.
- `explanation` kann in v0 noch einfach sein, sollte aber als eigenes Feld vorbereitet werden.
- `overall_score`, `score`, `purity_raw`, `breadth_raw` und `hits_pct` sind erklärungsrelevant, müssen aber in der UI verständlich übersetzt werden.

#### RecommendationSet

Repräsentiert das Ergebnis einer Empfehlungsberechnung.

```json
{
  "id": null,
  "source": "archive",
  "profile_snapshot": {},
  "generated_at": "2026-06-21T12:00:00Z",
  "total": 240,
  "items": []
}
```

Mögliche Werte für `source`:

- `archive`,
- `new_reviews`.

Hinweise:

- Für Gäste kann `id` leer bleiben.
- `profile_snapshot` ist wichtig, damit später nachvollziehbar ist, mit welchen Einstellungen ein Ergebnis erzeugt wurde.
- Persistenz von RecommendationSets ist für v1 nicht zwingend Pflicht.

#### WeeklyBatchFit

Repräsentiert die Einschätzung, wie gut die neuesten Rezensionen einer Woche zu einem Profil passen.

```json
{
  "period_start": "2026-06-15",
  "period_end": "2026-06-21",
  "review_count": 20,
  "matching_count": 8,
  "fit_label": "mau",
  "fit_score": 0.42,
  "message": "Diese Woche passt nur mittelgut zu deinem Profil; hier sind trotzdem die besten Empfehlungen."
}
```

Hinweise:

- Dieses Modell ist für E-Mail und Wochenansicht wichtig.
- Die genaue Berechnung kann später aus Verteilung und Scores abgeleitet werden.

#### PlaylistExport

Repräsentiert eine manuell erzeugte Playlist-Vorschlagsliste.

Bekannte Felder aus `PlaylistSuggestion` und Exportlogik:

```json
{
  "id": "playlist_export_123",
  "name": "Plattenradar 2026-06-21",
  "source": "archive",
  "format": "txt",
  "created_at": "2026-06-21T12:00:00Z",
  "items": [
    {
      "review_id": 123,
      "artist": "Artist",
      "album": "Album",
      "track_title": "Song",
      "source_kind": "highlight",
      "score_weight": 0.08,
      "raw_score": 0.72
    }
  ],
  "download": {
    "filename": "plattenradar-2026-06-21.txt",
    "content_type": "text/plain"
  }
}
```

Unterstützte v1-Exportformate:

- `txt`: freie TuneMyMusic-kompatible Zeilen im Format `Artist - Title`,
- `csv`: TuneMyMusic-kompatible Spalten `Track name`, `Artist name`, `Playlist name`.

### API-Endpunkte v0

Die Endpunkte sind als fachlicher Schnitt formuliert. Pfade, Namen und Auth-Details können bei der FastAPI-Implementierung noch angepasst werden.

#### Health

`GET /api/health`

Zweck:

- Prüfen, ob API und Datenbasis erreichbar sind.

Antwort:

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

#### Aktueller Nutzer

`GET /api/me`

Zweck:

- Aktuellen angemeldeten Nutzer laden.

Antwort für angemeldete Nutzer:

```json
{
  "user": {
    "id": "user_123",
    "email": "name@example.com"
  }
}
```

Antwort für Gäste:

```json
{
  "user": null
}
```

#### Geschmacksprofil validieren oder normalisieren

`POST /api/taste-profiles/preview`

Zweck:

- Temporäres Profil aus Wizard-Daten erzeugen, validieren und normalisieren.
- Kein Login erforderlich.

Request:

```json
{
  "flow_mode": null,
  "selected_communities": ["C001", "C042"],
  "artist_flow_selected_communities": ["C001"],
  "genre_flow_selected_communities": ["C042"],
  "community_weights_raw": {
    "C001": 1.0,
    "C042": 0.6
  },
  "filter_settings": {}
}
```

Antwort:

```json
{
  "profile": {},
  "is_complete": true,
  "warnings": []
}
```

#### Gespeichertes Profil laden

`GET /api/taste-profile`

Zweck:

- Das aktive gespeicherte Profil des angemeldeten Nutzers laden.

Auth:

- erforderlich.

Antwort:

```json
{
  "profile": {}
}
```

#### Geschmacksprofil speichern

`PUT /api/taste-profile`

Zweck:

- Temporäres oder bestehendes Geschmacksprofil für den angemeldeten Nutzer speichern.
- V1 überschreibt das eine aktive Profil.

Auth:

- erforderlich.

Request:

```json
{
  "profile": {}
}
```

Antwort:

```json
{
  "profile": {},
  "saved_at": "2026-06-21T12:00:00Z"
}
```

#### Archivempfehlungen berechnen

`POST /api/recommendations/archive`

Zweck:

- Empfehlungen aus dem gesamten lokalen Review-Archiv berechnen.
- Funktioniert mit temporärem Profil oder gespeicherter Nutzerkennung.

Request für temporäres Profil:

```json
{
  "profile": {},
  "limit": 50,
  "offset": 0
}
```

Request für angemeldeten Nutzer mit gespeichertem Profil:

```json
{
  "profile": null,
  "limit": 50,
  "offset": 0
}
```

Antwort:

```json
{
  "source": "archive",
  "generated_at": "2026-06-21T12:00:00Z",
  "total": 240,
  "items": []
}
```

#### Neueste Rezensionen personalisiert berechnen

`POST /api/recommendations/new-reviews`

Zweck:

- Neueste Rezensionen laden und anhand des Profils sortieren/bewerten.

Request:

```json
{
  "profile": {},
  "limit": 30,
  "days": null
}
```

Antwort:

```json
{
  "source": "new_reviews",
  "generated_at": "2026-06-21T12:00:00Z",
  "batch_fit": {},
  "total": 30,
  "items": []
}
```

#### Playlist-Export erzeugen

`POST /api/playlists/exports`

Zweck:

- Aus Archivempfehlungen oder neuesten Rezensionen eine Trackliste erzeugen.

Request:

```json
{
  "profile": {},
  "source": "archive",
  "name": "Plattenradar 2026-06-21",
  "format": "txt",
  "selection_strategy": "stratified",
  "max_tracks": 30
}
```

Antwort:

```json
{
  "playlist_export": {},
  "content": "Artist - Track\nOther Artist - Track",
  "filename": "plattenradar-2026-06-21.txt",
  "content_type": "text/plain"
}
```

Hinweise:

- In v1 kann der Export synchron erzeugt werden.
- Spätere Automatisierung kann dieselbe Ressource verwenden, aber asynchron per Job laufen.

#### Reviews suchen oder laden

`GET /api/reviews/{review_id}`

Zweck:

- Einzelne Reviewdetails für Detailansichten laden.

Antwort:

```json
{
  "review": {}
}
```

Optional später:

`GET /api/reviews?query=&artist=&year_min=&year_max=`

### Service-Schicht v0

Damit Streamlit und neues Frontend nicht zwei getrennte fachliche Welten werden, sollte die Logik mittelfristig in Services liegen.

Vorgeschlagene Services:

- `TasteProfileService`
  - Profil validieren,
  - Profil normalisieren,
  - Profil speichern/laden,
  - Vollständigkeit prüfen.

- `RecommendationService`
  - Archivempfehlungen berechnen,
  - neue Rezensionen bewerten,
  - gemeinsame Recommendation-DTOs bauen,
  - Erklärungssignale berechnen.

- `ReviewService`
  - Reviews laden,
  - neueste Reviews ermitteln,
  - Reviewdetails liefern.

- `PlaylistExportService`
  - Playlist-Suggestions bauen,
  - TXT/CSV formatieren,
  - Dateinamen und Content-Type liefern.

- `AccountService`
  - Nutzer anlegen,
  - Login/Auth kapseln,
  - aktuelles Profil dem Nutzer zuordnen.

### Migrationsschnitt aus Streamlit

Aktuelle Streamlit-nahe Quellen:

- Profilpersistenz: `src/music_review/dashboard/user_profile_store.py`
- User-DB: `src/music_review/dashboard/user_db.py`
- Empfehlungspool: `pages/recommendations_pool.py`
- Neueste Reviews: `pages/neueste_reviews_pool.py`
- Playlist-Erzeugung: `src/music_review/dashboard/playlist_builder.py`
- Playlist-Export: `src/music_review/dashboard/playlist_export.py`
- Empfehlungskarten-Formatierung: `pages/page_formatting.py`

Migrationsziel:

- Berechnungen aus `pages/` herauslösen, sofern sie nicht reine UI sind.
- DTO-/Schema-Aufbereitung von HTML-Rendering trennen.
- Karteninhalte als JSON liefern, nicht als HTML-Strings.
- Streamlit kann währenddessen dieselben Services konsumieren.

### Offene Entscheidungen vor Code

1. Auth-Variante für v1 festlegen oder bewusst vertagen. Entscheidung v0: einfache E-Mail-und-Passwort-Lösung ist ausreichend.
2. Entscheiden, ob `POST /api/recommendations/archive` immer ein Profil im Body bekommt oder für eingeloggte Nutzer automatisch das gespeicherte Profil nutzt. Empfehlung v0: Endpunkte akzeptieren ein optionales Profil im Body; wenn keines mitgegeben wird, nutzt die API das aktive gespeicherte Profil des eingeloggten Nutzers.
3. Filtermodell stärker typisieren: Welche `filter_settings`-Keys sind offiziell? Entscheidung v0: alle bestehenden Filter sind offiziell, werden gespeichert und als `TasteFilterSettings` typisiert.
4. Recommendation-Erklärung v0 definieren: Welche Scorebestandteile werden sichtbar? Entscheidung v0: subtile visuelle Erklärbarkeit über passende Genre-/Community-Labels, keine prominente Score-Aufschlüsselung.
5. Playlist-Export synchron oder bereits als Job modellieren? Entscheidung v0: synchroner Export, keine Persistenzpflicht.
6. Umgang mit Pagination: `limit`/`offset`, Cursor oder zunächst simpler Slice? Entscheidung v0: API unterstützt `limit`/`offset`; Berechnung darf intern vollständig erfolgen, aber die Antwort liefert nur einen Ausschnitt.
7. Wird `RecommendationSet` persistiert oder nur live berechnet? Entscheidung v0: live berechnen, keine Persistenz von RecommendationSets in v1.

## Entscheidungsrunde 1: Auth und Profilverhalten

### Auth-Variante

Für v1 ist eine einfache E-Mail-und-Passwort-Lösung ausreichend. Der erste Teilnehmerkreis besteht aus Freunden und Bekannten, und es werden keine hochkritischen Daten gespeichert. Das zentrale gespeicherte Datum ist der Musikgeschmack.

Entscheidung v0:

> Plattenradar v1 verwendet E-Mail und Passwort, ohne separaten Benutzernamen.

Hinweise:

- E-Mail passt später zur Playlist-Zustellung.
- Höhere Sicherheits- oder OAuth-Varianten sind aktuell nicht notwendig.
- Die Umsetzung sollte trotzdem sauber sein: Passwörter nie im Klartext speichern, Passwort-Hashing nutzen, Sessions ordentlich behandeln.

### Registrierung im Nutzerfluss

Ein neuer Nutzer soll nicht am Anfang zur Registrierung gedrängt werden. Vor dem ersten Aha-Moment weiß er noch nicht, ob Plattenradar für ihn nützlich ist.

Entscheidung v0:

> Kontoerstellung wird nach dem ersten Aha-Moment angeboten, nicht als Einstiegshürde.

Gleichzeitig muss Login jederzeit erreichbar sein, damit wiederkehrende Nutzer direkt ihr gespeichertes Profil laden können.

### Profil im Request vs. gespeichertes Profil

Der schwierige Punkt ist nicht technisch, sondern produktlogisch: Was passiert, wenn ein Nutzer ein temporäres Profil gebaut hat und sich dann einloggt? Welches Profil gewinnt?

Empfehlung v0:

> Die API sollte Empfehlungen immer für ein klar bestimmtes Profil berechnen. Das Frontend darf entweder ein temporäres Profil mitschicken oder das aktive gespeicherte Profil verwenden lassen.

Regelvorschlag:

- Wenn im Request ein Profil mitgegeben wird, wird genau dieses Profil verwendet.
- Wenn kein Profil mitgegeben wird und der Nutzer eingeloggt ist, verwendet die API das aktive gespeicherte Profil.
- Wenn kein Profil mitgegeben wird und der Nutzer nicht eingeloggt ist, gibt die API einen Fehler zurück: Geschmacksprofil erforderlich.
- Ein Login überschreibt niemals automatisch ein temporäres Profil.
- Nach Login mit vorhandenem temporärem Profil fragt die UI explizit:
  - aktuelles temporäres Profil speichern,
  - gespeichertes Profil laden,
  - temporäres Profil weiter unverändert verwenden.

Damit wird Überschreiben zu einer bewussten Nutzerentscheidung.

### Temporäres Profil speichern

Wenn ein Gast nach den ersten Empfehlungen "Profil speichern" klickt, ist die bevorzugte v1-Variante:

> Konto erstellen und aktuelles Profil direkt speichern.

Die UI sollte danach trotzdem eine kurze Bestätigung zeigen, etwa:

- "Dein Profil wurde gespeichert."
- "Du kannst es später im Profilbereich ändern."

Eine zusätzliche Profilbestätigung vor dem Speichern ist nur sinnvoll, wenn der Nutzer sonst schwer versteht, was gespeichert wird. Für v1 wirkt der direkte Weg besser.

### Account-Minimum für v1

Ein Konto muss in v1 nur wenig können:

- Konto erstellen,
- anmelden,
- abmelden,
- Geschmacksprofil speichern,
- Geschmacksprofil laden,
- Geschmacksprofil überschreiben oder aktualisieren.

Keine v1-Pflicht:

- umfangreiche Account-Verwaltung,
- Rollen/Rechte,
- öffentliche Profile,
- Social Features,
- komplexe E-Mail-Einstellungen.

### Ein Profil oder mehrere Profile

Bisher war für v1 ein Profil pro Nutzer vorgesehen. Die Diskussion zeigt aber, dass mehrere Profile ein mögliches Mittel gegen das Überschreib-Dilemma sind: Statt "altes Profil überschreiben oder neues verlieren" könnte ein Nutzer Profile benennen und später für Playlists auswählen.

Empfehlung v0:

> Das Datenmodell sollte mehrere Profile pro Nutzer erlauben, die UI kann in v1 aber mit einem aktiven Standardprofil starten.

Pragmatischer Schnitt:

- Backend/API modelliert `TasteProfile` als eigene Ressource mit `id`, `name`, `user_id` und `is_default`.
- V1-UI zeigt zunächst vor allem das Standardprofil.
- Wenn ein temporäres Profil gespeichert wird und bereits ein gespeichertes Profil existiert, kann die UI anbieten:
  - Standardprofil überschreiben,
  - als neues Profil speichern.
- Playlist-Erzeugung kann später an ein bestimmtes Profil gebunden werden.

Diese Lösung hält v1 einfach, verbaut aber die spätere Erweiterung nicht.

### Aktualisierte API-Empfehlung

Statt nur `GET /api/taste-profile` und `PUT /api/taste-profile` sollte die Spezifikation perspektivisch mehrere Profile unterstützen:

- `GET /api/taste-profiles`
- `POST /api/taste-profiles`
- `GET /api/taste-profiles/{profile_id}`
- `PUT /api/taste-profiles/{profile_id}`
- `POST /api/taste-profiles/{profile_id}/make-default`

Für v1 kann zusätzlich ein Convenience-Endpunkt existieren:

- `GET /api/taste-profile/default`

Empfehlungs-Endpunkte:

- Akzeptieren optional `profile` oder `profile_id`.
- Ohne beides nutzen sie bei eingeloggten Nutzern das Default-Profil.
- Bei Gästen ist `profile` im Request erforderlich.

## Entscheidungsrunde 2: Offizielles Filtermodell

### Grundsatzentscheidung

Alle aktuell implementierten Filter sind für v1 Pflicht. Sie wurden jeweils aus einem konkreten fachlichen Grund gebaut und sollen beim Wechsel auf das neue Frontend nicht zurückgebaut werden.

Entscheidung v0:

> Alle bestehenden Filter gehören zum gespeicherten Geschmacksprofil und müssen im neuen Frontend abbildbar sein.

### UI-Prinzip

Die Filter sollen nicht als Data-Science-Parameter wirken. Nutzer sollen verstehen, was sie mit einem Filter bewirken, ohne interne Scores, Normalisierungen oder Gewichtungsformeln kennen zu müssen.

Ziel:

> Semantische Bedienung statt nackter Zahlen.

Das bedeutet:

- Filter bleiben sichtbar.
- Die UI erklärt jeden Filter in Alltagssprache.
- Numerische Werte dürfen intern existieren, sollen aber nicht die primäre Nutzererfahrung sein.
- Wo möglich, sollten Presets oder beschriftete Stufen die Bedienung vereinfachen.
- Die vorhandene Kontrolle bleibt erhalten; sie wird nur verständlicher gestaltet.

### Sichtbarkeit und Expertenmodus

Normale Nutzer sollen grundsätzlich alle wichtigen Filter sehen können. Ein kompletter Versteckmodus wäre fachlich falsch, weil die Filter echte Auswirkungen auf die Empfehlungsqualität haben.

Ein Sonderfall ist der Plattenlabel-Filter:

- Er ist fachlich vorhanden und für manche plattentests.de-Nutzer interessant.
- Er ist weniger allgemein verständlich als Jahr, Wertung oder Stilpassung.
- Er kann als Expertenfilter geführt werden.
- Er wäre der erste Kandidat, der weniger prominent platziert wird, falls die UI zu voll wird.

Entscheidung v0:

> Alle Filter bleiben verfügbar; Plattenlabel darf als Expertenfilter weniger prominent erscheinen.

### Offizielle Filterfelder

Die bestehenden `filter_settings` sollten in ein typisiertes API-Modell überführt werden. Offizielle Felder für v1:

```json
{
  "year_min": 1999,
  "year_max": 2026,
  "rating_min": 7,
  "rating_max": 10,
  "score_min": 0.0,
  "score_max": 1.0,
  "community_spectrum_crossover": 0.5,
  "overall_weight_alpha": 1.0,
  "overall_weight_beta": 1.0,
  "overall_weight_gamma": 1.0,
  "plattenlabel_selection": [],
  "sort_mode": "fixed",
  "serendipity": 0.0
}
```

Zusätzlich außerhalb von `filter_settings`, aber Teil des Geschmacksprofils:

```json
{
  "community_weights_raw": {
    "C001": 1.0,
    "C042": 0.6
  }
}
```

### Filtergruppen für die UI

Die neue UI sollte die Filter nicht als lose Liste zeigen, sondern in verständliche Gruppen gliedern:

1. **Was soll überhaupt in die Auswahl?**
   - Veröffentlichungsjahr,
   - plattentests.de-Wertung,
   - Mindest-/Maximalpassung zum Stilprofil,
   - Plattenlabel als Expertenfilter.

2. **Wie soll sortiert und priorisiert werden?**
   - Nähe zu gewählten Stilrichtungen,
   - Gewicht der plattentests.de-Wertung,
   - klare Stilpräferenz vs. breite Stilabdeckung,
   - Gewicht des Stilpräferenz-Terms,
   - Gewichte pro Stil-Schwerpunkt.

3. **Wie viel Entdeckung darf rein?**
   - Sortiermodus,
   - Serendipity bzw. Durchmischung.

### Presets

Presets sind ausdrücklich erwünscht, solange sie die Kontrolle nicht entfernen.

Denkbare Presets:

- **Treffsicher:** strenge Stilpassung, nah am gewählten Profil.
- **Ausgewogen:** Standardwerte.
- **Entdeckerisch:** lockerere Stilpassung und mehr stilistische Randbereiche, aber keine Zufallsmischung.
- **Kritikerlieblinge:** höhere Gewichtung der plattentests.de-Wertung.
- **Vielschichtig:** stärkere Betonung von Alben, die mehrere gewählte Stilrichtungen zugleich berühren.

Presets sollten die zugrunde liegenden Filter sichtbar verändern, damit Nutzer lernen, was passiert.

Nicht Teil der Geschmacks-Presets:

- Zufallsmischung der Rangliste.
- "Liste variieren" bleibt ein eigener Sortier-/Listenmechanismus.

### Speicherung

Alle Filter sind Teil des Geschmacksprofils und müssen gespeichert werden.

Entscheidung v0:

> Es gibt keine Trennung zwischen dauerhaftem Geschmacksprofil und temporären Filter-Ansichtseinstellungen. Alle aktuellen Filterwerte werden mit dem Profil gespeichert.

Ausnahme oder spätere Präzisierung:

- Rein technische UI-Zustände wie aufgeklappte Panels, aktuelle Seitennummer oder lokale Widget-Keys werden nicht gespeichert.

### API-Folge

Das bisher freie `filter_settings`-Dict sollte in der API als `TasteFilterSettings` typisiert werden.

Validierungsregeln:

- `year_min <= year_max`,
- `rating_min <= rating_max`,
- Rating zwischen 0 und 10,
- Score-/Gewichtswerte im Bereich 0 bis 1,
- unbekannte Plattenlabels ignorieren oder als Warnung zurückgeben,
- `serendipity` nur wirksam, wenn passender Sortiermodus aktiv ist.

### Aktualisierte offene Punkte

- Welche deutschen UI-Bezeichnungen bekommen die Presets?
- Wie wird der Expertenfilter "Plattenlabel" visuell eingeordnet?
- Soll es zusätzlich einen echten "Expertenmodus" geben oder nur weniger prominente Expertenabschnitte?

## Entscheidungsrunde 3: Empfehlungserklärungen

### Grundsatzentscheidung

Erklärbarkeit ist wichtig, aber nicht die Kernfunktionalität. Die Empfehlung selbst und die Musik stehen im Vordergrund. Data Science dient dem Produktnutzen und soll nicht als Selbstzweck inszeniert werden.

Entscheidung v0:

> Plattenradar erklärt Empfehlungen subtil, visuell und geschmacklich, nicht als technische Score-Lektion.

### Was erklärt werden soll

Die wichtigste Erklärung ist die Passung zwischen Album und Nutzerprofil, besonders über Musikrichtungen, Genre-/Community-Labels und die vom Nutzer gewählten Stil-Schwerpunkte.

Wichtiger als:

- mathematische Scorebestandteile,
- vollständige Formeltransparenz,
- technische Rankingparameter.

Im Vordergrund:

- Welche Stil- oder Genre-Labels passen zu meinem Profil?
- Warum fühlt sich dieses Album geschmacklich relevant an?
- Welche gewählten Präferenzen werden hier getroffen?

### Sichtbarkeit auf Empfehlungskarten

Die Erklärung soll direkt auf der Karte wahrnehmbar sein, aber subtil. Sie soll nicht erst in einem versteckten Detailbereich liegen, aber die Karte auch nicht mit Text überfrachten.

Geeignete Mittel:

- dezente Umrandung passender Tags,
- unterschiedliche Tag-Farben oder Intensitäten,
- kleine Symbole oder Marker für "passt zu deinem Profil",
- klare, aber leichte Legende,
- optionaler Tooltip oder Info-Hinweis für interessierte Nutzer.

Nicht gewünscht:

- lange Erklärungstexte auf jeder Karte,
- sichtbare Formeln,
- technische Scoretabellen als Standardansicht,
- vollgepackte Karten.

### Legende

Die aktuelle Hervorhebung passender Genres ist fachlich richtig, aber zu subtil, weil sie nicht erklärt wird. Das neue Frontend braucht eine elegante Legende.

Anforderungen an die Legende:

- kurz,
- ästhetisch,
- nicht dominant,
- in der Nähe der Karten oder Filter,
- verständlich ohne Data-Science-Vokabular.

Beispielrichtung:

> Markierte Stil-Tags passen zu deinem Profil.

Oder visueller:

- normaler Tag: Stil des Albums,
- markierter Tag: trifft deine Auswahl.

### Data-Science-Sichtbarkeit

Das Projekt darf im Portfolio zeigen, dass eine ernsthafte Data-Science-Logik dahintersteht. Für normale Nutzer soll diese Logik aber nicht im Vordergrund stehen.

Entscheidung v0:

> Data Science bleibt im Produkt spürbar, aber nicht laut sichtbar.

Portfolio-Wert entsteht durch gute Empfehlungen, saubere Erklärsignale und professionelles UX-Design, nicht durch sichtbare Rohparameter.

### Begriffe

Technische Begriffe bleiben intern:

- `purity_raw`,
- `breadth_raw`,
- `overall_weight_alpha`,
- `overall_weight_beta`,
- `overall_weight_gamma`,
- `community_spectrum_norm`,
- `community_spectrum_effective`.

Mögliche Nutzerbegriffe:

- Stilpassung,
- Stiltreffer,
- passt zu deinem Profil,
- trifft deine Auswahl,
- Nähe zu deinem Geschmack,
- geschmackliche Nähe.

Noch offen:

- Der Begriff "Stilnähe" ist möglich, aber noch nicht überzeugend.
- Die Formeln sollten später gemeinsam durchgegangen und in präzisere Nutzersprache übersetzt werden.

### API-Folge

Die API sollte Erklärungssignale liefern, aber nicht erzwingen, dass die UI daraus lange Texte macht.

Empfohlenes `Recommendation`-Feld:

```json
{
  "top_communities": [
    {
      "id": "C001",
      "label": "Indie Rock",
      "affinity": 0.81,
      "matched_user_preference": true,
      "display_strength": "strong"
    }
  ],
  "explanation_signals": {
    "matched_community_count": 2,
    "primary_matched_labels": ["Indie Rock", "Post-Punk"],
    "fit_level": "high"
  }
}
```

Hinweise:

- `matched_user_preference` steuert Tag-Hervorhebung.
- `display_strength` kann die visuelle Intensität steuern.
- `fit_level` kann für kleine Symbole, Legenden oder Sortierhinweise genutzt werden.
- Eine ausführliche `explanation.summary` ist optional und nicht Hauptbestandteil der v1-UI.

### Spätere Arbeitsrunde

Eigene spätere Mini-Session:

> Formeln in Nutzersprache übersetzen.

Ziel dieser Session:

- technische Scorebestandteile verstehen,
- passende deutsche Begriffe finden,
- UI-Texte und Tooltips präzise, aber nicht nerdig formulieren.

## Entscheidungsrunde 4: Playlist-Export und Automatisierung

### Synchronität

Playlist-Erzeugung soll in v1 synchron passieren, wie im aktuellen Prototyp:

1. Nutzer klickt "Playlist erzeugen".
2. Plattenradar berechnet Vorschläge.
3. Nutzer erhält direkt TXT- oder CSV-Download.

Entscheidung v0:

> Playlist-Export ist in v1 ein synchroner Request, kein Background-Job.

### Quellen

Playlist-Erzeugung muss in v1 beide bestehenden Quellen unterstützen:

- Archivempfehlungen aus dem gesamten lokalen Bestand,
- neueste Rezensionen.

Entscheidung v0:

> `PlaylistExport.source` unterstützt mindestens `archive` und `new_reviews`.

### Persistenz

Playlist-Exports müssen in v1 nicht dauerhaft in Plattenradar gespeichert werden. Nach dem Export lädt der Nutzer die Datei in seine Musik-App oder in einen Dienst wie TuneMyMusic hoch; dort lebt die Playlist weiter.

Entscheidung v0:

> Plattenradar muss keine Playlist-Historie speichern.

Konsequenzen:

- Kein v1-Bereich "alte Playlist-Exports".
- Kein dauerhaftes `PlaylistExport`-Archiv nötig.
- `PlaylistExport` kann ein transienter Response-Typ sein.
- Dateiname, Format und Inhalt reichen für v1.

### Bindung an Profile

Wenn Playlist-Exports nicht dauerhaft gespeichert werden, braucht v1 keine sichtbare dauerhafte Bindung zwischen Playlist und Profil.

Trotzdem sollte der Export intern aus einem klaren Profil berechnet werden:

- temporäres Profil im Request,
- gespeichertes Profil per `profile_id`,
- Default-Profil des eingeloggten Nutzers.

API-Folge:

> Playlist-Erzeugung folgt denselben Profilregeln wie Empfehlungen, speichert aber keine eigene dauerhafte Profilbindung.

### Automatisierung

Automatische Playlist-Zustellung ist ein späterer Feature Request. Die v1-Architektur soll sie nicht verbauen, aber sie muss noch nicht implementiert werden.

Entscheidung v0:

> Automatisierung wird im Datenmodell mitgedacht, aber nicht als v1-Funktion gebaut.

Spätere Ressourcen können sein:

- `PlaylistSubscription`,
- `EmailDelivery`,
- `ScheduledPlaylistRun`.

Diese Ressourcen gehören nicht zur v1-Pflicht-API, können aber als spätere Erweiterung im Dokument erwähnt bleiben.

### Aktualisierte API-Empfehlung

`POST /api/playlists/exports`

Charakter:

- synchron,
- nicht persistent,
- gibt Dateiinhalt direkt zurück.

Request:

```json
{
  "profile": {},
  "profile_id": null,
  "source": "archive",
  "name": "Plattenradar 2026-06-22",
  "format": "txt",
  "selection_strategy": "stratified",
  "max_tracks": 30
}
```

Antwort:

```json
{
  "source": "archive",
  "name": "Plattenradar 2026-06-22",
  "format": "txt",
  "filename": "plattenradar-2026-06-22.txt",
  "content_type": "text/plain",
  "content": "Artist - Track\nOther Artist - Track",
  "items": []
}
```

Validierung:

- `source` muss `archive` oder `new_reviews` sein.
- `format` muss `txt` oder `csv` sein.
- Gastnutzer müssen ein `profile` mitsenden.
- Eingeloggte Nutzer können `profile_id` oder das Default-Profil nutzen.
- `max_tracks` wird begrenzt, damit der synchrone Request schnell bleibt.

## Entscheidungsrunde 5: Ergebnislisten, Pagination und RecommendationSets

### Berechnung vs. Darstellung

Die vollständige Berechnung der Archivempfehlungen ist aktuell akzeptabel, weil sie nur wenige Sekunden dauert. Problematisch ist nicht primär die Berechnung, sondern die Darstellung sehr großer Listen mit potenziell vielen tausend Alben.

Entscheidung v0:

> Empfehlungen dürfen intern vollständig berechnet werden, aber die API liefert paginierte Ergebnis-Ausschnitte.

API-Folge:

- Empfehlungs-Endpunkte unterstützen `limit` und `offset`.
- Die Response enthält `total`, `limit`, `offset` und `items`.
- Das Frontend rendert nur den aktuellen Ausschnitt.

Beispiel:

```json
{
  "source": "archive",
  "generated_at": "2026-06-22T12:00:00Z",
  "total": 2400,
  "limit": 50,
  "offset": 0,
  "items": []
}
```

Hinweise:

- Intern kann der Service zunächst die komplette Liste berechnen und danach slicen.
- Spätere Performance-Optimierung kann die Berechnung verbessern, ohne den API-Schnitt zu ändern.
- Cursor-Pagination ist für v1 nicht nötig.

### Reproduzierbarkeit und Entdeckungsmodus

Der Standardfall soll deterministisch sein. Wenn Profil, Filter und Daten gleich bleiben, soll die Liste gleich bleiben.

Gleichzeitig ist ein Entdeckungsmodus sinnvoll, damit Nutzer nicht immer dieselben Alben oben sehen, wenn sie bewusst mehr Variation wollen.

Aktuelle Logik:

- Default: kein Zufallseinfluss.
- Optional: Serendipity/Zufallsmischung.
- Höherer Serendipity-Wert bringt andere Alben weiter nach oben.

Produktproblem:

- "Zufall" oder "Willkür" ist für Nutzer schwer intuitiv.
- Die Funktion erfüllt aber einen echten Zweck: mehr Entdeckung ohne Profiländerung.

Empfehlung v0:

> Das Feature sollte als Entdeckungsmodus formuliert werden, nicht als Zufall.

Mögliche UI-Begriffe:

- Mehr Entdeckung,
- Liste auffrischen,
- Überraschungen einstreuen,
- Bekannte Pfade verlassen,
- Variation.

API-Folge:

```json
{
  "sort_mode": "deterministic",
  "discovery_mix": 0.0,
  "random_seed": null
}
```

Oder bei aktiviertem Entdeckungsmodus:

```json
{
  "sort_mode": "discovery",
  "discovery_mix": 0.35,
  "random_seed": 123456
}
```

Hinweise:

- Intern kann das weiterhin auf `sort_mode` und `serendipity` abgebildet werden.
- Ein optionaler `random_seed` ermöglicht reproduzierbare Zufallslisten, falls später gewünscht.
- Ohne Seed darf eine neue Liste anders aussehen, wenn der Nutzer bewusst "neu mischen" auslöst.

### RecommendationSet-Persistenz

Für v1 müssen generierte Empfehlungsergebnisse nicht gespeichert werden. Es reicht, Empfehlungen aus Profil und Daten neu zu berechnen.

Entscheidung v0:

> `RecommendationSet` ist in v1 ein Response-Modell, keine dauerhaft gespeicherte Ressource.

Konsequenzen:

- Keine Empfehlungshistorie in v1.
- Kein "alte Empfehlungslisten anzeigen".
- Keine Datenbanktabelle für RecommendationSets nötig.
- Performance kann später über Caching optimiert werden.

Mögliche spätere Optimierung:

- Cache pro Profil-Snapshot und Datenstand,
- Cache pro neuem Review-Batch,
- gespeicherter Seed für reproduzierbare Entdeckungslisten.

### Merken, Ausblenden, Schon gehört

Funktionen wie "merken", "ausblenden" oder "schon gehört" sind für v1 nicht wichtig.

Entscheidung v0:

> Keine Persistenz einzelner Empfehlungseinträge in v1.

Später denkbar:

- gespeicherte Alben,
- ausgeblendete Alben,
- Feedback "passt" / "passt nicht",
- gehört-Markierung,
- personalisierte Nachjustierung durch Nutzerfeedback.

Diese Funktionen würden neue Ressourcen erfordern, etwa `UserAlbumState` oder `RecommendationFeedback`, gehören aber nicht zum v1-Schnitt.

### Neueste Rezensionen: letzte X vs. Wochenbatch

Produktseitig ist ein Wochenbatch intuitiver als "die letzten X Rezensionen". Fachlich wäre es sinnvoll, die Rezensionen nach dem Zeitpunkt zu gruppieren, an dem Plattenradar sie entdeckt oder abgerufen hat.

Aktuelles Problem:

- Vorhanden ist das Veröffentlichungsdatum des Albums.
- Dieses Datum ist nicht dasselbe wie das Rezensionsdatum.
- Für Wochenbatches fehlt aktuell ein zuverlässiges Datum, wann eine Rezension neu auf plattentests.de erschienen bzw. von Plattenradar entdeckt wurde.

Entscheidung v0:

> Kurzfristig nutzt v1 weiterhin "letzte X Rezensionen"; perspektivisch soll ein `discovered_at`- oder `scraped_at`-Datum für echte Wochenbatches gespeichert werden.

Pipeline-Anforderung:

- Wenn der Cron-Job neue Rezensionen erkennt, soll der Zeitpunkt gespeichert werden, an dem Plattenradar die Rezension erstmals gesehen hat.

Mögliche Felder:

```json
{
  "review_id": 123,
  "scraped_at": "2026-06-22T10:15:00Z",
  "first_seen_at": "2026-06-22T10:15:00Z"
}
```

Produktziel später:

- "Neue Empfehlungen der Woche",
- "letzte 5 bis 6 Wochen",
- Batch-Fit pro Woche,
- automatische Playlist-Zustellung auf Basis neuer Wochenbatches.

### Aktualisierte API-Empfehlung

Archiv:

`POST /api/recommendations/archive`

Request:

```json
{
  "profile": {},
  "profile_id": null,
  "limit": 50,
  "offset": 0,
  "sort_mode": "deterministic",
  "discovery_mix": 0.0,
  "random_seed": null
}
```

Neueste Rezensionen kurzfristig:

`POST /api/recommendations/new-reviews`

Request:

```json
{
  "profile": {},
  "profile_id": null,
  "limit": 30,
  "offset": 0,
  "recent_count": 50
}
```

Neueste Rezensionen später:

```json
{
  "profile": {},
  "profile_id": null,
  "limit": 30,
  "offset": 0,
  "period_start": "2026-06-01",
  "period_end": "2026-06-22"
}
```

## Aktualisierte Restentscheidungen

- Preset-Namen und semantische Filtertexte finalisieren.
- Plattenlabel-Expertenfilter visuell einordnen.
- Formeln gemeinsam in Nutzersprache übersetzen.
- Auth technisch konkretisieren: Passwort-Hashing, Session/Cookie, Reset-Fluss.
- Festlegen, wann `first_seen_at` / `scraped_at` in der Pipeline eingeführt wird.

## Entscheidungsrunde 6: Presets und Filtertexte

### Grundmodi zuerst, Expertenfilter darunter

Die Filter bleiben fachlich vollständig erhalten, sollen aber nicht alle mit gleicher Prominenz auf Nutzer einwirken. Die neue Oberfläche soll zuerst einfache Grundmodi anbieten. Die detaillierten Regler bleiben verfügbar, werden aber als Expertenfilter oder erweiterte Einstellungen eingeordnet.

Entscheidung v0:

> Grundmodi sind die primäre Bedienebene; alle bestehenden Filter bleiben als Expertenfilter verfügbar und gespeichert.

Das löst zwei Probleme:

- Neue Nutzer müssen keine technischen Regler verstehen, um gute Ergebnisse zu bekommen.
- Power-User behalten die volle Kontrolle.

### Konfigurierbare Presets

Die Grundmodi sollen nicht hart im Code versteckt sein. Sinnvoll ist eine Konfiguration, in der Schwellenwerte und Gewichtungen für die Modi gepflegt werden können.

Denkbare Modi:

- Treffsicher,
- Ausgewogen,
- Entdeckerisch,
- Kritikerlieblinge,
- vielschichtige Alben (Arbeitsname; ersetzt "Breiter Geschmack"),
- Fokussiert.

Offen:

- Welche Modi bleiben final?
- Welche konkreten Werte setzen sie?
- Sollen Presets nur Startwerte setzen oder dauerhaft als eigener Modus gespeichert werden? Entscheidung v0: Presets setzen einmal die Regler; danach ist das Profil benutzerdefiniert, sobald Werte manuell geändert werden.

Empfehlung v0:

> Presets setzen konkrete Filterwerte, die danach sichtbar und manuell veränderbar sind.

Dadurch bleiben sie transparent und verhindern keinen Expertenzugriff.

Default:

> Ausgewogen ist der Standardmodus.

Speicherlogik:

- Gespeichert werden die durch das Preset gesetzten Filter- und Gewichtungswerte.
- Das Preset selbst muss nicht dauerhaft als aktiver Modus gespeichert werden.
- Wenn Nutzer nach der Preset-Auswahl einzelne Werte ändern, gilt das Profil als benutzerdefiniert.
- Die UI kann trotzdem optional anzeigen: "Ausgehend von: Ausgewogen".

### Stil-Match / Score-Filter

Der Filter beschreibt, wie stark ein Album den gewählten Fein-Genres entsprechen muss. Die bisher vorgeschlagenen Begriffe sind noch nicht perfekt.

Vorläufig beste Bezeichnung:

> Stilpassung

Alternativen, noch nicht final:

- Geschmacksnähe,
- Profiltreffer,
- Nähe zu deinem Geschmack,
- Passung zu deinen Stilen.

Aktuelle Einschätzung:

- "Stilpassung" ist verständlich, aber noch etwas technisch.
- Der Begriff sollte später mit der Formel abgeglichen werden.
- Wichtig ist eine kurze Erklärung unter dem Regler.

Möglicher Kurztext:

> Bestimmt, wie stark ein Album deinen gewählten Stilrichtungen entsprechen muss.

### Serendipity / Variation

Die aktuelle Serendipity-Funktion ist kein einfacher Ein-/Aus-Schalter, sondern ein Kontinuum. Sie sorgt bei aktivem Zufallseinfluss dafür, dass die Liste variiert und auch andere Alben nach oben kommen können.

Problem:

- "Zufall" klingt beliebig.
- "Willkür" klingt negativ.
- "Entdeckungsmodus" klingt eher nach Schalter als nach Regler.
- Die tatsächliche Funktion muss erklärt werden: Die Liste wird stärker variiert, je höher der Wert ist.

Arbeitsname:

> Liste variieren

Weitere mögliche Bezeichnungen:

- Mehr Variation,
- Überraschungen einstreuen,
- Reihenfolge auffrischen,
- Entdeckungsspielraum,
- Mehr Abwechslung.

Möglicher Kurztext:

> Mischt passende Alben stärker durch, damit nicht immer dieselben Treffer oben stehen.

UI-Idee:

- Im Expertenbereich wird der Regler als "Liste variieren" gezeigt.
- Ein Button "neu mischen" könnte später mit einem neuen Seed arbeiten.

Wichtige Trennung:

> "Entdeckerisch" im Preset-Sinn bedeutet stilistische Öffnung, nicht zufällige Ranglistenvariation.

Das heißt:

- Das Preset "Entdeckerisch" setzt Filter und Gewichtungen so, dass mehr stilistische Randbereiche zugelassen werden.
- Die Zufallskomponente bleibt ein eigener Sortier-/Listenmechanismus.
- Zufall wirkt später auf die Rangliste, nicht auf die grundlegende Geschmacks- und Filterdefinition.

### Fokus vs. Breite

Dieser Regler adressiert ein echtes Rankingproblem: Stilreine Alben können sonst überproportional stark bevorzugt werden. Wenn ein Album vollständig einem einzigen gewählten Stil entspricht, kann es sehr weit oben landen, obwohl andere Alben mehrere gewählte Stilrichtungen verbinden und für den Nutzer womöglich interessanter sind.

Beispiel:

- Ein reines Deutsch-Punk-Album trifft einen gewählten Stil vollständig.
- Dadurch kann es in der Rangliste sehr stark profitieren.
- Das kann andere, breiter passende Alben verdrängen.

Arbeitsbegriff:

> Fokus vs. Breite

Bedeutung:

- **Fokus:** Alben steigen, wenn sie einen deiner gewählten Stile besonders klar treffen.
- **Breite:** Alben steigen, wenn sie mehrere deiner gewählten Stilrichtungen zugleich berühren.

Möglicher Kurztext:

> Entscheidet, ob klare Treffer in einem Stil oder Alben mit mehreren passenden Stilanteilen stärker bevorzugt werden.

Dieser Regler braucht zwingend eine Erklärung, weil die Begriffe allein nicht ausreichen.

### Erklärtext auf der Filterseite

Erklärtexte sollen kurz sein und unter den jeweiligen Reglern stehen. Wenn Grundmodi im Vordergrund stehen und Details als Expertenfilter darunter liegen, ist etwas erklärender Text akzeptabel.

Entscheidung v0:

> Kurze Erklärung direkt unter jedem Regler; keine langen Hilfetexte als Standardansicht.

UI-Richtung:

- Grundmodi oben, visuell ruhig.
- Expertenfilter darunter, ggf. aufklappbar.
- Pro Regler ein kurzer Satz.
- Tooltips optional für Details.

### Aktualisierte UI-Struktur für Filter

Vorschlag:

1. **Grundmodus wählen**
   - Treffsicher,
   - Ausgewogen,
   - Entdeckerisch,
   - Kritikerlieblinge,
   - Vielschichtig.

2. **Zusammenfassung der gesetzten Werte**
   - kurzer Satz, was der Modus bewirkt.

3. **Expertenfilter**
   - Zeitraum,
   - plattentests.de-Wertung,
   - Stilpassung,
   - Plattenlabel,
   - Fokus vs. Breite,
   - Gewichtung von Stilpassung/Wertung/Fokus-Breite,
   - Gewichte pro Stil-Schwerpunkt,
   - Liste variieren.

4. **Speichern / Empfehlungen anzeigen**

Diese Struktur ist inzwischen als API-Konfiguration über `GET /v1/taste-filter-ui` modelliert. Das Frontend kann damit die Filterseite aufbauen, ohne technische Feldnamen als sichtbare Sprache verwenden zu müssen.

### Darstellung der Grundmodi

Die Grundmodi sollen nicht nur als technische Dropdown-Auswahl erscheinen. Besser ist eine kleine Auswahlfläche mit mittelgroßen Modus-Boxen.

Empfehlung v0:

> Presets werden als mittelgroße Auswahlkarten mit Icon, Titel und kurzem Erklärungssatz dargestellt.

Designrichtung:

- keine riesigen Marketing-Karten,
- keine winzigen Tabs ohne Erklärung,
- eher kompakte Karten oder Kacheln in einer ruhigen Grid-/Segment-Anordnung,
- ein Icon pro Modus,
- ein kurzer Satz unter dem Titel,
- der aktive Modus ist klar markiert,
- nach manueller Änderung erscheint der Zustand "Benutzerdefiniert".

Beispielstruktur:

- **Ausgewogen**
  Gute Mischung aus Passung, Wertung und stilistischer Breite.
- **Treffsicher**
  Bleibt nah an deinen gewählten Stilrichtungen.
- **Entdeckerisch**
  Öffnet die Auswahl für angrenzende Stilrichtungen.
- **Kritikerlieblinge**
  Gewichtet starke plattentests.de-Wertungen höher.
- **Vielschichtig**
  Bevorzugt Alben, die mehrere deiner gewählten Stilrichtungen berühren.

### API- und Konfigurationsfolge

Presets sollten als Konfiguration modelliert werden, nicht nur als UI-Texte.

Beispiel:

```json
{
  "id": "balanced",
  "label": "Ausgewogen",
  "description": "Gute Mischung aus Stilpassung, Wertung und Vielschichtigkeit.",
  "filter_settings": {
    "score_min": 0.4,
    "score_max": 1.0,
    "rating_min": 6,
    "rating_max": 10,
    "overall_weight_alpha": 0.5,
    "overall_weight_beta": 0.25,
    "overall_weight_gamma": 0.25,
    "community_spectrum_crossover": 0.5,
    "sort_mode": "deterministic",
    "serendipity": 0.0
  }
}
```

Offen:

- konkrete Werte pro Preset,
- finaler Begriff für Stilpassung,
- finaler Begriff für Serendipity/Variation,
- finale Beschreibung für Fokus vs. Breite,
- finaler Name für den Preset, der Alben bevorzugt, die mehrere gewählte Stilrichtungen zugleich berühren.

### Namenskorrektur: "Breiter Geschmack"

"Breiter Geschmack" ist als Preset-Name nicht passend, weil es nicht um eine Eigenschaft des Nutzers geht. Gemeint ist eine Eigenschaft der Albumempfehlung: Alben, die mehrere der gewählten Stilrichtungen zugleich berühren oder stilistisch vielschichtiger sind.

Verworfener Arbeitsname:

- Breiter Geschmack.

Bessere Richtung:

- Name beschreibt das Album oder die Empfehlungsliste, nicht den Nutzer.
- Name klingt nicht technisch.
- Name macht klar, dass mehrere passende Stilrichtungen zusammenkommen.

## Entscheidungsrunde 7: Preset-Charaktere

### Grundlogik

Die Presets sind keine komplett unterschiedlichen Produktmodi, sondern verständliche Varianten um einen soliden Standard herum. Sie setzen Filter- und Gewichtungswerte, die anschließend manuell verändert und gespeichert werden können.

Default:

> Ausgewogen.

### Treffsicher

Charakter:

- sehr strenge Stilpassung,
- nah an den gewählten Stilrichtungen,
- plattentests.de-Wertung mindestens 6,
- keine ungewollte Bevorzugung stilreiner Alben.

Wichtiger fachlicher Hinweis:

> Treffsicher darf nicht bedeuten, dass Alben, die nur einen einzigen gewählten Stil stark treffen, automatisch alles dominieren.

Daher sollte der Fokus-vs.-Breite-Regler auch in diesem Preset so gesetzt werden, dass stilreine Alben nicht unfair bevorzugt werden.

Untertitel:

> Nah an deinem Profil.

### Ausgewogen

Charakter:

- ähnlich wie Treffsicher,
- aber Stilpassung einen Tick weniger streng,
- solider Standardmodus,
- plattentests.de-Wertung mindestens 6,
- Stilpassung, Wertung und Vielschichtigkeit in guter Balance.

Untertitel:

> Der beste Startpunkt.

### Entdeckerisch

Charakter:

- basiert auf Ausgewogen,
- aber Stilpassung noch einmal lockerer,
- öffnet die Auswahl für angrenzende Stilbereiche,
- bedeutet nicht automatische Zufallsmischung der Rangliste.

Wichtige Trennung:

> Entdeckerisch verändert die Geschmacks- und Filterlogik; "Liste variieren" bleibt ein separater Mechanismus für die Ranglistenvariation.

Untertitel:

> Mehr angrenzende Stile.

### Kritikerlieblinge

Charakter:

- basiert auf Ausgewogen,
- plattentests.de-Wertung mindestens 8,
- Wertung bekommt stärkere Bedeutung,
- Stilpassung bleibt weiterhin relevant.

Untertitel:

> Höher bewertete Alben zuerst.

### Vielschichtig

Charakter:

- basiert auf Ausgewogen,
- stärkere Betonung von Alben, die mehrere gewählte Stilrichtungen zugleich berühren,
- Vielschichtigkeit wird im Ranking wichtiger,
- soll nicht einfach "breiter Nutzergeschmack" ausdrücken, sondern eine Eigenschaft der Alben.

Untertitel:

> Mehrere deiner Stile zugleich.

### Preset-Konfigurationsskizze ohne finale Zahlen

Die konkreten Zahlen werden später festgelegt. Die Tendenzen sind:

| Preset | Stilpassung | Rating-Minimum | Wertungsgewicht | Vielschichtigkeitsgewicht | Listenvariation |
| --- | --- | --- | --- | --- | --- |
| Treffsicher | sehr streng | 6 | normal | ausgewogen gegen stilreine Dominanz | aus |
| Ausgewogen | streng, aber etwas offener | 6 | normal | ausgewogen | aus |
| Entdeckerisch | lockerer als Ausgewogen | 6 | normal | ausgewogen | aus |
| Kritikerlieblinge | wie Ausgewogen | 8 | höher | ausgewogen | aus |
| Vielschichtig | wie Ausgewogen | 6 | normal | höher | aus |

Hinweis:

- "Listenvariation" bleibt in allen Presets standardmäßig aus.
- Variation kann später separat über "Liste variieren" aktiviert werden.

### Konkreter Preset-Wertevorschlag v0

Diese Werte sind ein erster fachlicher Startpunkt und müssen später mit echten Ergebnislisten geprüft werden. Sie sollen unterscheidbare Modi erzeugen, ohne das Ranking sofort extrem zu verzerren.

Interne Bedeutung:

- `score_min` / `score_max`: harte Stilpassungs-Filtergrenze.
- `rating_min` / `rating_max`: harte plattentests.de-Wertungsgrenze.
- `overall_weight_alpha`: Gewicht der Stilpassung im Gesamtranking.
- `overall_weight_beta`: Gewicht der plattentests.de-Wertung im Gesamtranking.
- `overall_weight_gamma`: Gewicht des Fokus-vs.-Breite-Terms.
- `community_spectrum_crossover`: 0 = klarer Stilfokus, 0.5 = ausgewogen, 1 = breite Abdeckung.
- `sort_mode` / `serendipity`: Ranglistenvariation; in Presets standardmäßig aus.

| Preset | `score_min` | `score_max` | `rating_min` | `rating_max` | `alpha` | `beta` | `gamma` | `crossover` | `sort_mode` | `serendipity` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| Treffsicher | 0.50 | 1.00 | 6 | 10 | 0.60 | 0.20 | 0.20 | 0.50 | deterministic | 0.00 |
| Ausgewogen | 0.40 | 1.00 | 6 | 10 | 0.50 | 0.25 | 0.25 | 0.50 | deterministic | 0.00 |
| Entdeckerisch | 0.25 | 1.00 | 6 | 10 | 0.50 | 0.25 | 0.25 | 0.50 | deterministic | 0.00 |
| Kritikerlieblinge | 0.40 | 1.00 | 8 | 10 | 0.35 | 0.45 | 0.20 | 0.50 | deterministic | 0.00 |
| Vielschichtig | 0.40 | 1.00 | 6 | 10 | 0.45 | 0.20 | 0.35 | 0.75 | deterministic | 0.00 |

Begründung:

- **Treffsicher** setzt die höchste Stilpassungs-Untergrenze und gewichtet Stilpassung am stärksten. `crossover` bleibt neutral, damit stilreine Alben nicht automatisch bevorzugt werden.
- **Ausgewogen** entspricht am ehesten der fachlichen Default-Idee, aber mit Rating-Minimum 6 statt dem bisherigen UI-Default 7.
- **Entdeckerisch** senkt vor allem die Stilpassungs-Untergrenze deutlich; es aktiviert keine Zufallsmischung.
- **Kritikerlieblinge** setzt Rating-Minimum 8 und gibt der Wertung das höchste Gewicht, ohne Stilpassung unwichtig zu machen.
- **Vielschichtig** setzt `crossover` auf "Eher Breite" und erhöht `gamma`, damit Alben profitieren, die mehrere gewählte Stilrichtungen zugleich berühren.

Kalibrierungsfragen:

- Liefert `score_min = 0.50` bei Treffsicher genug Treffer und bleibt trotzdem streng?
- Ist `score_min = 0.25` für Entdeckerisch offen genug, ohne beliebig zu wirken?
- Ist Rating-Minimum 6 als allgemeine Untergrenze passend, obwohl der bisherige UI-Default 7 war?
- Soll Vielschichtig `crossover = 0.75` oder direkt `1.0` verwenden?
- Soll Kritikerlieblinge `beta = 0.45` oder noch stärker Richtung Wertung gehen?

### Preset-Konfiguration als JSON-Skizze

```json
[
  {
    "id": "precise",
    "label": "Treffsicher",
    "subtitle": "Nah an deinem Profil",
    "description": "Strenge Stilpassung, ohne stilreine Alben unfair zu bevorzugen.",
    "filter_settings": {
      "score_min": 0.5,
      "score_max": 1.0,
      "rating_min": 6,
      "rating_max": 10,
      "overall_weight_alpha": 0.6,
      "overall_weight_beta": 0.2,
      "overall_weight_gamma": 0.2,
      "community_spectrum_crossover": 0.5,
      "sort_mode": "deterministic",
      "serendipity": 0.0
    }
  },
  {
    "id": "balanced",
    "label": "Ausgewogen",
    "subtitle": "Der beste Startpunkt",
    "description": "Gute Mischung aus Stilpassung, Wertung und Vielschichtigkeit.",
    "filter_settings": {
      "score_min": 0.4,
      "score_max": 1.0,
      "rating_min": 6,
      "rating_max": 10,
      "overall_weight_alpha": 0.5,
      "overall_weight_beta": 0.25,
      "overall_weight_gamma": 0.25,
      "community_spectrum_crossover": 0.5,
      "sort_mode": "deterministic",
      "serendipity": 0.0
    }
  },
  {
    "id": "exploratory",
    "label": "Entdeckerisch",
    "subtitle": "Mehr angrenzende Stile",
    "description": "Öffnet die Auswahl für Alben, die etwas weiter von deinem Profil entfernt liegen.",
    "filter_settings": {
      "score_min": 0.25,
      "score_max": 1.0,
      "rating_min": 6,
      "rating_max": 10,
      "overall_weight_alpha": 0.5,
      "overall_weight_beta": 0.25,
      "overall_weight_gamma": 0.25,
      "community_spectrum_crossover": 0.5,
      "sort_mode": "deterministic",
      "serendipity": 0.0
    }
  },
  {
    "id": "critics",
    "label": "Kritikerlieblinge",
    "subtitle": "Höher bewertete Alben zuerst",
    "description": "Bevorzugt Alben mit starken plattentests.de-Wertungen.",
    "filter_settings": {
      "score_min": 0.4,
      "score_max": 1.0,
      "rating_min": 8,
      "rating_max": 10,
      "overall_weight_alpha": 0.35,
      "overall_weight_beta": 0.45,
      "overall_weight_gamma": 0.2,
      "community_spectrum_crossover": 0.5,
      "sort_mode": "deterministic",
      "serendipity": 0.0
    }
  },
  {
    "id": "multifaceted",
    "label": "Vielschichtig",
    "subtitle": "Mehrere deiner Stile zugleich",
    "description": "Bevorzugt Alben, die mehrere deiner gewählten Stilrichtungen berühren.",
    "filter_settings": {
      "score_min": 0.4,
      "score_max": 1.0,
      "rating_min": 6,
      "rating_max": 10,
      "overall_weight_alpha": 0.45,
      "overall_weight_beta": 0.2,
      "overall_weight_gamma": 0.35,
      "community_spectrum_crossover": 0.75,
      "sort_mode": "deterministic",
      "serendipity": 0.0
    }
  }
]
```
