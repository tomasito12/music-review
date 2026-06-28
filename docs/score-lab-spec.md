# Score Lab — Spezifikation v1

Stand: 2026-06-28  
Bezug: `docs/scoring-analyse-und-roadmap.md` (Priorität 1)  
Zielgruppe: Produktentwicklung / Kalibrierung (nicht Endnutzer-Produkt v1)

---

## 1. Ziel

Eine **interne Experimentier-Oberfläche**, um zu verstehen und zu tunen:

- wie `S_a`, Spectrum, Rating und `overall_score` zusammenwirken
- wie Presets und Schieberegler die Rangliste verändern
- ob Schwellen (`score_min`, `fit_level`) für ein Profil sinnvoll sind

**Nicht-Ziel v1:** Neue Scoring-Formeln in Produktion bringen (Kosinus, Perzentile) — nur
sichtbar machen und vergleichen.

---

## 2. Plattform-Entscheidung

| Option | Pro | Contra |
|--------|-----|--------|
| **Streamlit-Seite** (empfohlen) | Nutzt Session-Profil, `preference_ranking`, lokale `data/`; schnell | Nicht im React-Frontend |
| React Dev-Route | Näher an Plattenradar v1 | API-Erweiterung nötig, langsamer Start |

**Empfehlung:** Streamlit unter `pages/7_Score_Lab.py`, Eintrag in `st.navigation` /
optional Hub. React später optional über API-Breakdown (Roadmap Priorität 5).

---

## 3. Datenquelle und Logik

Wiederverwendung bestehender Pipeline — **keine zweite Score-Implementierung**.

| Baustein | Modul |
|----------|--------|
| Volle Score-Zeilen inkl. Breakdown | `preference_ranked_rows()` in `preference_ranking.py` |
| Archiv-Kandidaten (gefiltert) | `RecommendationService.compute_archive_recommendations()` |
| Aktives Profil | `st.session_state` wie `pages/6_Recommendations_Flow.py` |
| Affinitäten / Memberships | gleiche Loader wie `pages/recommendations_pool.py` |

### Felder pro Album (Tabelle + Detail)

Bereits von `preference_ranked_rows` geliefert bzw. ergänzen:

| Spalte | Bedeutung |
|--------|-----------|
| `rank` | Position nach `overall_score` |
| `review_id`, `artist`, `album` | Identifikation |
| `score` | `S_a` Stilpassung (roh) |
| `rating`, `rating_norm` | Wertung roh / [0,1] |
| `purity_norm`, `breadth_norm` | Spectrum-Komponenten (batch-normalisiert) |
| `community_spectrum_norm` | Gemischt vor Gate |
| `spectrum_matching_gate` | `g(S_a)` |
| `community_spectrum_effective` | Spectrum × Gate |
| `alpha`, `beta`, `gamma` | effektive Gewichte |
| `overall_score` | Gesamt |
| `k_hits` | Treffer in gewählten Communities (aus Service-Row) |

**Ergänzung v1:** `purity_raw`, `breadth_raw` in `preference_ranked_rows` exportieren
(statt nur intern `_purity_raw` zu löschen), damit das Lab Roh- und Norm-Werte zeigt.

---

## 4. UI-Abschnitte (Streamlit)

### 4.1 Kopf

- Titel: **Score Lab**
- Kurzhinweis: internes Werkzeug, deutsche UI
- Aktives Profil: Name, Anzahl Communities, Preset-ID (falls erkennbar)

### 4.2 Profil & Datenquelle (Sidebar)

- Profil aus Session (wie Empfehlungsflow) — Hinweis wenn kein Profil: zu Schritt 1–3
- **Datenquelle:**
  - `Archiv (gefiltert)` — wie `compute_recommendations` (Standard)
  - `Feste Review-IDs` — Textfeld / Suche für Einzelalbum-Debug
- **Limit:** Slider 50 / 200 / 500 / alle (Performance; Default 200)

### 4.3 Live-Gewichtung (Sidebar)

Schieberegler (session-lokal, überschreibt nicht gespeichertes Profil ohne expliziten Button):

- `overall_weight_alpha`, `beta`, `gamma` (wie Preset-Schwerpunkt)
- `community_spectrum_crossover`
- `score_min`, `score_max` (Hard-Filter auf `S_a`)
- Button **„Aus aktuellem Profil laden“** / **„Zurücksetzen“**

Bei Änderung: Neuberechnung (gecached per `st.cache_data` mit Profil-Hash + Parametern).

### 4.4 Ergebnis

- **Haupttabelle** (`st.dataframe`): sortierbar, alle Breakdown-Spalten
- **Album-Detail** (expander oder zweite Spalte): Top-Communities mit Affinität × Gewicht,
  Referenz-Künstler-Anzahl, Link plattentests.de
- **Mini-Chart** (optional v1.1): gestapelte Balken α·S_a | β·rating | γ·spectrum für
  gewähltes Album

### 4.5 Export

- Button **CSV exportieren** (UTF-8, Semikolon oder Komma)

### 4.6 Preset-Vergleich (v1.1)

- Zwei Presets aus `TASTE_PRESETS` nebeneinander: gleiche Kandidaten, unterschiedliche
  `overall_score`-Ränge, Delta-Spalte

---

## 5. Implementierung in Phasen

### Phase 0 — Vorbereitung (0.5 Tag)

- [ ] `docs/score-lab-spec.md` (dieses Dokument) — erledigt
- [ ] `preference_ranked_rows`: `purity_raw`, `breadth_raw` in Output behalten
- [ ] Hilfsfunktion `build_score_lab_rows(profile, *, limit, review_ids)` in neuem Modul
      `src/music_review/dashboard/score_lab.py` (dünner Wrapper)

### Phase 1 — Lesen & Verstehen (1 Tag)

- [ ] `pages/7_Score_Lab.py`: Profil aus Session, Tabelle Top-N, CSV-Export
- [ ] Navigation: Eintrag in `streamlit_app.py` (Sektion „Entwicklung“ oder ans Ende)
- [ ] Tests: `tests/music_review/dashboard/test_score_lab.py` (Wrapper + Spalten)
- [ ] `tests/pages/test_score_lab_page.py` (Smoke: Import, Hilfsfunktionen)

### Phase 2 — Experimentieren (0.5–1 Tag)

- [ ] Sidebar-Schieberegler mit Live-Recompute
- [ ] Album-Detail mit Community-Beiträgen
- [ ] Hinweisbox: welche Werte **nutzerabsolut** vs **batch-relativ** sind (aus Scoring-Doc)

### Phase 3 — Kalibrierung (später)

- [ ] Preset-Vergleich
- [ ] Toggle „Kosinus-Passung (Prototyp)“ — erst nach separater Implementierung in
      `recommendation_scoring.py`
- [ ] Perzentil-Schwellen visualisieren (Histogramm `S_a` für Profil)

---

## 6. Technische Randbedingungen

- **Performance:** Volles Archiv (~21k Reviews) kann mehrere Sekunden dauern; Default-Limit
  200, `st.spinner`, optional `@st.cache_data(ttl=300)` keyed by profile + settings.
- **Kein Schreiben ins Profil** aus dem Lab, außer expliziter „In Profil übernehmen“-Button
  (v2, optional).
- **Sprache:** Deutsch in UI; Code/Module Englisch.
- **Sichtbarkeit:** Siehe offene Entscheidung unten — nicht im öffentlichen React-Frontend v1.

---

## 7. Akzeptanzkriterien v1 (Phase 1+2)

1. Mit geladenem Taste-Profil zeigt das Lab mindestens 50 Alben mit allen Score-Spalten.
2. Änderung von α/β/γ oder crossover ändert `overall_score` und Rang sichtbar innerhalb von
   wenigen Sekunden.
3. Ein stilreines Album (hohes `purity_raw`) ist an den Spalten erkennbar.
4. CSV-Export enthält dieselben Spalten wie die Tabelle.
5. `hatch run lint:all` und `hatch run test:run` grün.

---

## 8. Entscheidungen (festgelegt 2026-06-28)

| # | Entscheidung | Ergebnis |
|---|--------------|----------|
| D1 | Sichtbarkeit | **Nur Streamlit-Navigation** — keine Hub-Karte |
| D2 | Default-Limit | **200** Alben (Sidebar wählbar) |
| D3 | v1-Umfang | **Tabelle + Live-Schieberegler + CSV** in der ersten Implementierung |

---

## 9. Verwandte Dateien (geplant)

| Datei | Zweck |
|-------|--------|
| `src/music_review/dashboard/score_lab.py` | Row-Builder, CSV-Helfer |
| `pages/7_Score_Lab.py` | Streamlit-UI |
| `tests/music_review/dashboard/test_score_lab.py` | Unit-Tests |
| `tests/pages/test_score_lab_page.py` | Page-Smoke |

---

## 10. Änderungshistorie

| Datum | Änderung |
|-------|----------|
| 2026-06-28 | Erstversion Spezifikation v1 |
