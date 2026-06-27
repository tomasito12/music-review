# Implementierungsplan: Künstlerbilder für Top-Fundstücke

Stand: 2026-06-27  
Status: Plan (noch nicht implementiert)  
Bezug: [Plattenradar Designrunde](plattenradar-designrunde-layout-befunde.md) (Runde 8 – „leere“ Karten ohne Bild)

## 1. Ziel

Die **Aktuell**-Seite wirkt ohne Bildmaterial etwas leer. Dieser Plan beschreibt, wie wir für die **Top-Fundstücke** (max. 3 Highlight-Karten) optional ein **lizenziertes Künstlerfoto** von Wikimedia Commons einbinden – aufgelöst über MusicBrainz und Wikidata, mit **persistenter Speicherung unter `data/`** und korrekter **Attribution**.

### Produktziel (Spike / v1 des Features)

- Ein Highlight mit Bild fühlt sich **editorialer** an, ohne die Scanbarkeit der Liste zu verschlechtern.
- Fehlende Bilder sind **normal** – die Karte sieht dann wie heute aus.
- Keine direkten Commons/Wikidata-Aufrufe aus dem Browser.

### Nicht-Ziele (für die erste Ausbaustufe)

- Bilder für die **gesamte Empfehlungsliste** oder Entdecken.
- Album-Cover statt Künstlerfotos.
- Automatischer Batch für alle Künstler im Korpus.
- Bildbearbeitung, Cropping-Pipeline über Standard-Thumbnails hinaus.
- Hosting als CDN – zunächst FastAPI + lokale Dateien / Commons-Thumb-URLs.

---

## 2. Architektur (Zielbild)

```
React (Highlight-Karte)
  ↓  GET /v1/artists/{mbid}/image  oder  Feld in Recommendation-Response
FastAPI
  ↓  ArtistImageService
Cache (data/artist_images.jsonl + optional data/artist_images/*.jpg)
  ↓  bei Cache-Miss
MusicBrainz (artist MBID → url-rels → Wikidata)
  ↓
Wikidata (P18 image / P154 logo – nur P18 für Fotos)
  ↓
Wikimedia Commons API (Datei-Metadaten, Lizenz, Autor, Thumb-URL)
  ↓
optional: Thumbnail lokal speichern
```

**Prinzipien**

| Prinzip | Umsetzung |
|--------|-----------|
| Backend als Grenze | React spricht nur Plattenradar-API an |
| MBID first | `artist_mbid` aus `metadata.jsonl`, Fallback Namenssuche |
| Persistenz | Metadaten immer in JSONL; Bilddatei optional |
| Fail open | Kein Bild → `null`, UI unverändert |
| Rechtssicherheit | Nur Bilder mit klarer, speicherbarer Lizenz + Attribution |

---

## 3. Datenquellen im bestehenden Projekt

Bereits vorhanden und zu nutzen:

| Artefakt | Relevanz |
|----------|----------|
| `data/metadata.jsonl` | `artist_mbid` pro Review (`fetch_metadata.py`) |
| `src/music_review/pipeline/enrichment/musicbrainz_client.py` | Artist-Lookup, Rate-Limit ~1 req/s |
| `src/music_review/api/app.py` | Empfehlungs-Endpunkte `/v1/recommendations/*` |
| `frontend/.../RecommendationHighlights.tsx` | Ziel-UI für Bildintegration |

**Review → Künstler-Bild:** Für jede Highlight-Empfehlung `review_id` → Metadaten-Zeile → `artist_mbid`. Ohne MBID: einmalig MusicBrainz-Suche nach `artist` (mit Disambiguation-Logik wie im bestehenden Client).

---

## 4. Auflösungskette (Detail)

### Schritt A – MusicBrainz Artist

- Input: `artist_mbid` (bevorzugt) oder `artist_name`
- Request: `GET /artist/{mbid}?inc=url-rels`
- Output: Wikidata-URL in `relations` (`type == wikidata`)

Bestehenden `_lookup_artist_with_tags` erweitern oder schlanken Wrapper `fetch_artist_wikidata_id(mbid) -> str | None`.

### Schritt B – Wikidata

- Input: Q-ID (z. B. `Q123`)
- Request: Wikidata Entity API (`wbgetentities`)
- Feld: **P18** (image) – Commons-Dateiname als Wert
- Optional später: P154 (logo) nur wenn P18 fehlt und es sich um ein Foto handelt (v1: nur P18)

### Schritt C – Wikimedia Commons

- Input: Dateiname (z. B. `Artist_name.jpg`)
- Request: Commons API `action=query&prop=imageinfo&iiprop=url|extmetadata`
- Output:
  - `url` / `thumburl` (Thumbnail ~300px für Karten)
  - `LicenseShortName`, `LicenseUrl`, `Artist`, `Credit`, `UsageTerms`

### Schritt D – Lizenzfilter (v1)

Nur cachen und ausliefern, wenn:

- Lizenz erkennbar ist (z. B. CC-BY, CC-BY-SA, CC0, Public domain)
- `attribution_text` gebaut werden kann

**Ausschließen (v1):** NC-only, unklare „All rights reserved“, fehlende Autorenangabe bei CC-BY.

Konkrete Allowlist in Code als Konstante, nicht als Ad-hoc-String-Vergleich.

### Schritt E – Attribution-Text

Vorlage (an Commons-Vorgaben angelehnt):

```
„{title}“ von {author}, {license} via Wikimedia Commons
```

Zusätzlich speichern: `source_url` (Commons-Dateiseite), `license_url`.

---

## 5. Datenmodell & Speicherorte

### Neue Pfade (`src/music_review/data_access/paths.py`)

```text
data/artist_images.jsonl          # ein Eintrag pro artist_mbid (Index + Metadaten)
data/artist_images/{mbid}.jpg   # optional: gecachtes Thumbnail (binär)
```

### JSONL-Schema (ein Objekt pro Zeile, Key: `artist_mbid`)

```json
{
  "artist_mbid": "a1b2c3d4-...",
  "artist_name": "The Notwist",
  "wikidata_id": "Q774353",
  "commons_file": "The_Notwist.jpg",
  "image_url": "https://upload.wikimedia.org/...",
  "thumbnail_url": "https://upload.wikimedia.org/.../thumb/...",
  "local_path": "artist_images/a1b2c3d4-....jpg",
  "license": "CC BY-SA 2.0",
  "license_url": "https://creativecommons.org/licenses/by-sa/2.0/",
  "author": "User:Example",
  "source_url": "https://commons.wikimedia.org/wiki/File:The_Notwist.jpg",
  "attribution_text": "„The Notwist“ von User:Example, CC BY-SA 2.0 via Wikimedia Commons",
  "status": "ok",
  "fetched_at": "2026-06-27T12:00:00Z"
}
```

**Negative Cache** (wichtig für Rate-Limits):

```json
{
  "artist_mbid": "...",
  "artist_name": "...",
  "status": "not_found",
  "reason": "no_wikidata_id | no_commons_image | license_rejected",
  "fetched_at": "..."
}
```

Negative Einträge TTL: z. B. **30 Tage** nicht erneut extern abfragen.

### Modul-Vorschlag

| Modul | Verantwortung |
|-------|----------------|
| `src/music_review/application/artist_image_models.py` | `ArtistImageRecord`, Status-Enum |
| `src/music_review/application/artist_image_store.py` | JSONL lesen/schreiben, lokale JPG |
| `src/music_review/application/artist_image_resolver.py` | MB → Wikidata → Commons |
| `src/music_review/application/artist_image_service.py` | Cache-Logik, TTL, Orchestrierung |
| `src/music_review/pipeline/enrichment/wikidata_client.py` | Wikidata HTTP (User-Agent) |
| `src/music_review/pipeline/enrichment/commons_client.py` | Commons API + Lizenz-Parsing |

Tests spiegeln unter `tests/music_review/application/test_artist_image_*.py` und `tests/music_review/pipeline/enrichment/test_commons_client.py`.

---

## 6. API-Design

### Option A (empfohlen für Spike): Dedizierter Endpunkt

```
GET /v1/artists/{artist_mbid}/image
```

**Response 200**

```json
{
  "artist_mbid": "...",
  "artist_name": "...",
  "thumbnail_url": "/v1/artists/{mbid}/image/file",
  "attribution_text": "...",
  "license": "CC BY 2.0",
  "source_url": "https://commons.wikimedia.org/wiki/File:..."
}
```

**Response 404** – kein Bild (Frontend: kein `<img>`)

Optional:

```
GET /v1/artists/{artist_mbid}/image/file
```

Liefert gecachte JPG mit `Cache-Control: public, max-age=86400`.

### Option B (später): Feld in `Recommendation`

```json
{
  "artist_image": { "thumbnail_url": "...", "attribution_text": "..." }
}
```

Nur für Highlights befüllen, um Payload der Liste klein zu halten.

**Empfehlung:** Spike mit **Option A**; Frontend lädt Bilder parallel für 3 MBIDs. Option B erst, wenn Latenz stört.

### Batch (optional, Phase 2)

```
POST /v1/artists/images
Body: { "artist_mbids": ["...", "...", "..."] }
```

Ein Roundtrip für Top-Fundstücke.

---

## 7. CorpusProvider / Metadaten-Anbindung

`CorpusProvider` um Lookup erweitern:

```python
def artist_mbid_for_review(self, review_id: int) -> str | None: ...
```

Implementierung: Map aus `metadata.jsonl` / `metadata_imputed.jsonl` (bereits im Provider-Kontext oder neu aus `data_access`).

Bei Empfehlungs-Response optional `artist_mbid` mitliefern (neues Feld an `Recommendation`), damit das Frontend nicht review_id → mbid mappen muss.

---

## 8. Frontend (nur Top-Fundstücke)

### Datenfluss

1. `buildAktuellHighlights` liefert wie bisher 3 `Recommendation`s.
2. Pro Highlight: `artist_mbid` aus API (neues Feld) oder Lookup.
3. `useArtistImage(mbid)` → `GET /v1/artists/{mbid}/image`.
4. `RecommendationCard` / neues `HighlightCardMedia`:
   - Mit Bild: links oder oben, festes Seitenverhältnis (z. B. 4:3), `object-fit: cover`
   - Darunter: **eine Zeile** `attribution_text` (0.68rem, muted)
   - Ohne Bild: Layout wie heute

### UI-Regeln (Design)

- Bild **nur** bei `variant="feature"` / Highlights
- Max. Höhe begrenzen (~120–140px), damit Karten nicht höher als Nachbarn werden
- Attribution immer sichtbar wenn Bild sichtbar (Lizenzpflicht)
- `loading="lazy"`, `alt="{artist}"`

### Neue Frontend-Dateien (geplant)

- `frontend/src/lib/artistImageApi.ts`
- `frontend/src/hooks/useArtistImage.ts`
- `frontend/src/components/ArtistImage.tsx`
- CSS in `global.css`: `.highlight-card-media`, `.artist-attribution`

---

## 9. Phasen & Meilensteine

### Phase 0 – Spike (1–2 Tage)

**Ziel:** 5 feste MBIDs manuell durch die Kette jagen, JSONL-Eintrag + HTML-Mock.

- [x] `commons_client.py` + `wikidata_client.py` mit Unit-Tests (gemockt)
- [x] CLI: `hatch run artist-image-cli --mbid ... -v`
- [x] Wikidata-Fallback per SPARQL (P434/P435) wenn MusicBrainz url-rels leer
- [ ] Manuell prüfen: Lizenz, Attribution, Thumbnail-Qualität (lokal mit Live-API)

**Akzeptanz:** 3 von 5 Testkünstlern liefern ein nutzbares Bild mit korrekter Attribution.

### Phase 1 – Backend-Service + API (2–3 Tage)

- [ ] `artist_image_store.py` + `artist_image_service.py`
- [ ] `GET /v1/artists/{mbid}/image` + Tests in `tests/music_review/api/test_app.py`
- [ ] Negative Cache + TTL
- [ ] `artist_mbid` auf `Recommendation` (optional review-basiert befüllt)

**Akzeptanz:** Zweiter Request für gleichen MBID ohne externe API-Calls.

### Phase 2 – Frontend Highlight (1–2 Tage)

- [ ] `useArtistImage` + `ArtistImage` in `RecommendationHighlights`
- [ ] Visual-Test `aktuell-redesign.png` mit gemocktem Image-Endpunkt
- [ ] Fallback-Layout ohne Bild getestet

**Akzeptanz:** Aktuell-Referenzscreen zeigt 1–3 Bilder; keine Layout-Sprünge ohne Bild.

### Phase 3 – Härtung (optional)

- [ ] Batch-Endpunkt für 3 MBIDs
- [ ] Lokaler Datei-Cache + `/image/file`
- [ ] CLI `--review-id` / `--artist-name` für manuelle Nachpflege
- [ ] Eintrag in `update-db` **nicht** standardmäßig; optional `--fetch-artist-images` Flag

---

## 10. Tests

| Ebene | Was |
|-------|-----|
| Unit | Lizenz-Allowlist, Attribution-Builder, JSONL roundtrip |
| Unit | Wikidata/Commons-Parser an Fixture-JSON |
| API | 200 mit Bild, 404 ohne, Cache-Hit |
| Frontend | `artistImageApi.test.ts`, Hook mit mock fetch |
| Visual | Playwright mock für `/v1/artists/*/image` |

Keine Netzwerk-Tests in CI – alles über Fixtures.

---

## 11. Betrieb & Konfiguration

### Umgebungsvariablen

| Variable | Zweck |
|----------|--------|
| `USER_AGENT_APP` / `USER_AGENT_CONTACT` | Bereits für MusicBrainz; auch Wikidata/Commons |
| `ARTIST_IMAGE_CACHE_TTL_DAYS` | Default 30 für negative Einträge |
| `ARTIST_IMAGE_DOWNLOAD` | `true` = JPG unter `data/artist_images/` speichern |

### Rate Limits

- MusicBrainz: bestehendes 1 req/s einhalten
- Wikidata/Commons: sequentiell, max. 1–2 req/s, Backoff bei 429
- Pro Seitenaufruf max. **3** externe Ketten (nur Highlights)

### Codex Cloud

- `data/artist_images.jsonl` nicht in Git; Fixtures in `tests/fixtures/artist_images/`
- API-Tests mit Mock-Store

---

## 12. Risiken & Mitigationen

| Risiko | Mitigation |
|--------|------------|
| Falscher Künstler (MBID) | MBID aus Metadaten; bei Namenssuche Disambiguation aus MB |
| Kein Bild | Negative Cache; UI-Fallback |
| Lizenzfehler | Allowlist; lieber kein Bild als falsche Nutzung |
| Langsame Seite | Parallel fetch, nur 3 Bilder; Cache |
| Uneinheitliche Kartenhöhe | Feste Bildhöhe + `object-fit: cover` |
| Commons-URL bricht | Optional lokale Kopie in Phase 3 |

---

## 13. Offene Entscheidungen (vor Phase 1 klären)

1. **Bildposition:** links neben Text vs. oben über Titel? (Empfehlung: **oben**, volle Kartenbreite – einfacher für 3-Spalten-Grid)
2. **Nur `artist_mbid` aus Metadaten** oder auch On-the-fly-Suche wenn MBID fehlt? (Empfehlung: **beides**, Suche nur bei Highlights)
3. **Lokale JPG** in v1 oder erst Commons-Thumb-URL? (Empfehlung: **URL in Spike**, lokale Datei Phase 3)
4. **`artist_mbid` in Recommendation-Response** – ja/nein? (Empfehlung: **ja**)

---

## 14. Akzeptanzkriterien (Gesamtfeature)

- [ ] Top-Fundstücke können ein Künstlerthumbnail anzeigen.
- [ ] Attribution ist unter jedem Bild sichtbar und in `data/artist_images.jsonl` nachvollziehbar.
- [ ] Kein Bild → identisches Erlebnis wie vor dem Feature.
- [ ] Kein direkter Commons/Wikidata-Zugriff aus dem Browser.
- [ ] Zweiter Aufruf für denselben Künstler nutzt Cache (kein erneuter Commons-Call in Tests nachgeführt).
- [ ] `hatch run lint:all` und `hatch run test:run` / `hatch run frontend-test` grün.

---

## 15. Nächster Schritt

**Phase 0 starten:** CLI-Spike mit 5 Künstlern aus dem lokalen Korpus (MBIDs aus `metadata.jsonl`), Ergebnisse in `data/artist_images.jsonl` schreiben und manuell an der Highlight-Karten-HTML-Mock bewerten.

Wenn du die offenen Entscheidungen aus Abschnitt 13 bestätigst (oder abweichst), kann die Implementierung direkt an Phase 0 anschließen.
