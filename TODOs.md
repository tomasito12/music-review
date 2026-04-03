# TODOs

Format:
- `- [ ] <id>: <short title> — <optional details>`

Status legend:
- `[ ]` open
- `[x]` done

- `- [x] dist-analysis: Analyse Vektor-Distanzen — verschiedene Inputs, Distanz-Verteilung visualisieren`

- `- [x] rag-relevance: Recherche/Überlegung zur Erhöhung der Passgenauigkeit zwischen Freitext-Eingabe und Review-Inhalt`

- `- [x] streamlit-latest-page: Streamlit-Page anlegen mit den neuesten Reviews und Community-Genres`

- `- [x] chroma-rebuild-smaller-tokens: Vektordatenbank neu anlegen mit kleinerer Anzahl an Tokens (und ggf. größerer Embedding-Size)`

- `- [x] ranking-improve: Bessere Sortierung finden (Score + Genre-Abdeckung + Rating + Freitext-Distanz)`

- `- [x] user-profile-auth: Nutzerprofil & Login — Musikvorlieben persistent speichern, Anmeldung ermöglichen (z. B. Session/Auth-Provider, Datenschutz klären)`

- `- [x] chroma-strip-metadata: Bandnamen/Metadaten aus dem Vektor rausnehmen`

- `- [ ] playlist-generation: Spotify/Deezer-Playlists aus den besten Hits erzeugen (im Recommendation Flow oder in Neueste Rezensionen)`

- `- [ ] rag-system-search: Semantische Suche zu einem echten RAG-System ausbauen (Chunks als Kontext an ein LLM geben)`

- `- [ ] react-frontend: Neues Frontend auf Basis von React erstellen (Architektur/Scope klären)`

- `- [ ] cloud-deployment: Deployment in der Cloud vorbereiten (Provider/Stack auswählen und umsetzen)`

Priorisierung:
- `Now`: kurzfristig, hoher Impact auf Qualität/Verlässlichkeit
- `Next`: mittelfristig, Produkt- und Betriebsreife
- `Later`: größere Initiativen mit höherem Aufwand

Now (high impact):

- `- [x] dq-monitoring: Data-Quality-Checks + Pipeline-Health-Report nach jedem Update (Pflichtfelder, Duplikate, Ausreißer, Nullraten)`

- `- [ ] retrieval-eval-goldset: Goldset für Retrieval aufbauen (30-100 Queries) + Metriken (Recall@k/nDCG) als Regressionstest`

- `- [ ] incremental-indexing: Inkrementelles Embedding/Indexing einführen (nur neue/geänderte Reviews, idempotent mit Checksums)`

- `- [ ] api-resilience: Einheitliche Retry/Backoff/Timeout-Policy für OpenAI/MusicBrainz/Scraper + Fehlerklassifikation`

- `- [ ] spotify-search-cache-trim: Spotify-Suche entlasten — weniger Query-Varianten, aggressiveres Caching von Suchergebnissen (429 / App-Rate-Limits bei vielen Nutzern)`

- `- [ ] spotify-playlist-regenerate-hint: Streamlit-Hinweis bei Plattenradar — Nutzer auf mäßiges „Nochmal erzeugen“ hinweisen (viele API-Calls pro Playlist; gemeinsame App-Quota)`

- `- [ ] typed-settings-validation: Zentrales typisiertes Settings-Modell mit Startup-Validierung (fail fast bei Fehlkonfiguration)`

Next (productization):

- `- [ ] structured-logging-observability: Strukturierte Logs mit run_id/stage/review_id + Laufzeit-/Fehler-Metriken`

- `- [ ] integration-tests-pipeline: End-to-end-nahe Integrationstests über Stage-Grenzen (Scrape -> Enrich -> Index -> Search)`

- `- [ ] recommendation-explainability: Erklärbarkeit im UI ergänzen ("Warum empfohlen?" inkl. Top-Signale)`

- `- [ ] ranking-diversity-control: Diversitätssteuerung im Ranking ergänzen (Qualität + stilistische Breite balancieren)`

- `- [ ] secrets-hygiene: Secret-Handling härten (Leak-Prüfung, Logging-Schutz, pre-commit secret scan)`

Later (larger initiatives):

- `- [ ] artifact-versioning-reproducibility: Versionierung für Daten-/Modell-Artefakte + reproduzierbare One-Command-Pipeline`

- `- [ ] frontend-architecture-decision: Zielarchitektur UI klären (Streamlit-only vs. Streamlit+React) inkl. Migrationspfad`

