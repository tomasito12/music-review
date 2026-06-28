# Scoring-Analyse und Roadmap (Plattenradar)

Stand: 2026-06-28  
Zweck: Dauerhafte Referenz für Score-Berechnung, bekannte Probleme und priorisierte
Verbesserungsvorschläge. Ergänzt die API-Spezifikation in
`docs/plattenradar-v1-product-api.md` (Preset-Werte) mit der fachlichen Tiefe.

---

## 1. Ausgangslage und Kernproblem

Das Empfehlungs-Ranking kombiniert mehrere Größen mit **unterschiedlichen Skalen**:

1. **Stilpassung** (`S_a`, im Code oft `score`) — rohe, nutzerabhängige Summe
2. **plattentests.de-Wertung** — feste Skala 0–10
3. **Fokus vs. Vielschichtigkeit** — relativ zur **aktuellen Kandidatenliste** normalisiert

Zusätzlich werden **absolute Schwellen** verwendet:

- `score_min` / `score_max` (z. B. Preset-Baseline `score_min = 0.40`)
- `fit_level` in der API (`high` ab `overall_score >= 0.75`, `low` unter `0.35`)

Wenn die Score-Ranges **pro Nutzer** unterschiedlich sind, sind solche absoluten Schwellen
für Geschmacksprofile und UI-Hinweise **schwer vergleichbar**.

### Zweites Problem: Stilreine Alben dominieren

Ursprünglich sollte vor allem der **Passungsscore** (`S_a`) ranken. Das scheitert an
Alben, deren Referenzliste faktisch **einer einzigen Community** entspricht (z. B.
deutscher Punkrock). Hat der Nutzer diese Community gewählt, liegt das Album fast immer
oben — **100 % Übereinstimmung**.

Alben mit **mehreren Stilrichtungen** in den Referenzen werden benachteiligt: eine
nicht-gewünschte Neben-Community reicht, um die Passung zu drücken — obwohl viele Nutzer
(und das Produkt) **Vielschichtigkeit** eher schätzen.

### Workaround heute: Crossover-Slider

Der Regler **„Fokus oder Vielschichtigkeit“** (`community_spectrum_crossover`) mischt
stilreine vs. vielschichtige Alben innerhalb der Ergebnisliste. Er liefert für manche
Profile sinnvolle Rankings, ist aber:

- für Endnutzer schwer erklärbar
- **batch-relativ** (hängt von der aktuellen Kandidatenmenge ab)
- zusammen mit rohem `S_a` schwer global zu kalibrieren

**Langfristig** gehört die Korrektur in die **Passungsdefinition**, nicht in einen
zusätzlichen UI-Regler.

---

## 2. Wie der Score berechnet wird

### 2.1 Pipeline (Überblick)

```
Referenzliste (plattentests.de)
    → Community-Massen pro Album
    → Album-Affinitäten je Community (0–1, Summe = 1)
    → S_a (gewichtete Summe über Nutzer-Communities)
    → Hard-Filter: score_min/max, Rating, Jahr, Labels
    → purity_raw, breadth_raw
    → Batch-Normalisierung innerhalb der Kandidatenliste
    → spectrum_effektiv = spectrum_norm × gate(S_a)
    → overall_score = α·S_a + β·rating_norm + γ·spectrum_effektiv
    → optional Serendipity-Shuffle
```

Relevante Module:

| Modul | Rolle |
|-------|--------|
| `src/music_review/pipeline/retrieval/album_affinities.py` | Album → Community-Affinitäten |
| `src/music_review/application/recommendation_service.py` | Kandidaten, Filter, overall_score |
| `src/music_review/dashboard/recommendation_scoring.py` | Reine Score-Funktionen |
| `src/music_review/dashboard/preference_ranking.py` | Gleiche Logik für Neueste / Playlists |
| `src/music_review/application/presets.py` | Presets und Filter-UI-Metadaten |
| `src/music_review/config.py` | Default-Gewichte α, β, γ, Gate-Konstante |

### 2.2 Stilpassung `S_a` (Feld `score`)

Für jedes Album und jede **vom Nutzer gewählte** Community:

```
Beitrag(c) = Nutzer-Gewicht(c) × Album-Affinität(c)
S_a        = Σ Beitrag(c)   über alle gewählten Communities mit Treffer
```

- Album-Affinitäten entstehen aus den **Referenz-Künstlern** des Reviews
  (positionsgewichtet, pro Auflösung auf Summe 1 normalisiert).
- Default-Nutzer-Gewicht pro Community: `0.5` (`RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW`).
- **Stilreines Album:** Affinität ≈ 1.0 auf einer Community → hohes `S_a`, wenn diese
  Community gewählt ist.

`S_a` ist **nicht** auf [0, 1] normiert und hängt von Anzahl und Höhe der
Nutzer-Gewichte ab.

### 2.3 Fokus vs. Vielschichtigkeit

| Rohwert | Funktion | Bedeutung |
|---------|----------|-----------|
| `purity_raw` | `purity_max_weighted_share` | Anteil der stärksten Community an `S_a`; hoch = stilrein |
| `breadth_raw` | `breadth_raw_from_selected_community_masses` | 1 − Gini über Referenz-Massen; hoch = viele Stile |

Normalisierung **innerhalb der aktuellen Kandidatenliste**:

- `purity` → Min-Max
- `breadth` → Perzentil-Rang
- Mischung: `(1 − λ) · purity_norm + λ · breadth_norm` mit `λ = community_spectrum_crossover`

**Gate** (Kopplung an Stilpassung):

```
g(S_a) = S_a / (S_a + k)     mit k = 0.2 (Half-Saturation)
spectrum_effektiv = community_spectrum_norm × g(S_a)
```

Bei schwacher Stilpassung zählt der Spectrum-Term weniger.

### 2.4 Gesamtscore `overall_score`

```
rating_norm   = clamp(Rating, 0, 10) / 10   (fehlend → Default 7.0)
overall_score = α · S_a + β · rating_norm + γ · spectrum_effektiv
```

`α`, `β`, `γ` werden aus den Nutzer-/Preset-Werten normalisiert (Summe = 1).
Defaults in `config.py`: α=0.5, β=0.25, γ=0.25.

### 2.5 Presets (Gewichtung, nicht Filtergrenzen)

Alle Presets teilen dieselben **harten Filter** (`score_min = 0.40`, `rating_min = 6`, …).
Unterschieden sind vor allem **α, β, γ** und teils **λ** (crossover).

| Preset | α | β | γ | λ (crossover) |
|--------|---|---|---|---------------|
| Treffsicher | 0.70 | 0.20 | 0.10 | 0.50 |
| Ausgewogen | 0.50 | 0.25 | 0.25 | 0.50 |
| Entdeckerisch | 0.30 | 0.30 | 0.40 | 0.50 |
| Kritikerlieblinge | 0.30 | 0.50 | 0.20 | 0.50 |
| Vielschichtig | 0.35 | 0.15 | 0.50 | 0.75 |

Details: `src/music_review/application/presets.py`, Tabelle in
`docs/plattenradar-v1-product-api.md` (Abschnitt Preset-Wertevorschlag).

### 2.6 Was die API anzeigt

- `overall_score` → `score_display` als „**XX % Fit**“ (`overall_score × 100`)
- `ExplanationSignals.fit_level`: `high` ≥ 0.75, `low` < 0.35 auf `overall_score`
- Score-Komponenten (`S_a`, purity, breadth, …) sind in der **öffentlichen API nicht**
  exponiert (nur intern in Recommendation-Rows)

---

## 3. Warum absolute Schwellen problematisch sind

`S_a` variiert mit:

- Anzahl gewählter Communities
- individuellen Community-Gewichten
- Album-Verteilung (stilrein vs. gemischt)

→ `score_min = 0.4` bedeutet für einen Nutzer mit 3 Communities etwas anderes als für
einen mit 12.

`overall_score` mischt:

- **rohes** `S_a` (nutzerspezifische Skala)
- **batch-normalisierten** Spectrum-Term (listenspezifisch)
- **absolute** `rating_norm`

→ Prozent-Fit und feste `fit_level`-Grenzen sind **über Nutzer hinweg nicht kalibriert**.

**Folge:** Geschmacksprofile und Presets sollten Schwellen eher als **relative**
Größen (Perzentil, „oberste X %“) oder reines **Ranking** interpretieren — nicht als
universelle absoluten Werte.

---

## 4. Priorisierte Verbesserungsvorschläge

Bewertung: Nutzen vs. Aufwand. Reihenfolge = empfohlene Umsetzungssequenz.

### Priorität 1 — Score Lab (Experimentier-Oberfläche)

**Ziel:** Punkte A und B aus der Analyse — mit Scores experimentieren und Formeln
wieder verstehen.

**Inhalt (v1):**

- Taste-Profil laden (Communities, Gewichte, Filter, Preset)
- Tabelle: Top-N Alben mit **allen Zwischenwerten**:
  `S_a`, `purity_raw/norm`, `breadth_raw/norm`, `gate`, `rating_norm`,
  `spectrum_effektiv`, `overall_score`, Rang
- Live-Schieberegler für α, β, γ, λ; sofortige Neu-Sortierung
- Optional: zwei Profile / Presets nebeneinander vergleichen
- Export CSV für Offline-Analyse

**Technik:** Streamlit-Seite unter `pages/` (schnellster Weg, Daten lokal) oder
interner Dev-Modus im React-Frontend.

**Aufwand:** mittel (ca. 1–2 Tage für brauchbare v1)  
**Nutzen:** sehr hoch — Voraussetzung für alle weiteren Kalibrierungsentscheidungen

---

### Priorität 2 — Nutzer-relative Schwellen

**Ziel:** Punkt C pragmatisch lösen, ohne die ganze Passungsformel zu ersetzen.

**Vorschläge:**

- `score_min` als **Perzentil** innerhalb der Nutzer-Kandidaten
  (z. B. „nur oberste 60 % Stilpassung“ statt „mindestens 0.4“)
- `fit_level` aus **Rang/Perzentil** von `overall_score`, nicht aus 0.75 / 0.35 global
- Presets ändern **Gewichtung**; Filter steuern **wie viel der Liste** sichtbar bleibt

**Aufwand:** mittel  
**Nutzen:** hoch — macht Profile und Presets über Nutzer vergleichbar in der **Bedeutung**

---

### Priorität 3 — Passungsformel: Kosinus / Ähnlichkeit statt Crossover-Slider

**Ziel:** Stilreine Dominanz in der **Definition** von Stilpassung entschärfen; Crossover
aus der Nutzeroberfläche entfernen.

| Ansatz | Idee | Erklärbarkeit |
|--------|------|----------------|
| **Kosinus-Ähnlichkeit** | Nutzer-Gewichtsvektor vs. Album-Affinitätsvektor (L2-normiert) | Ein Passungsmaß |
| **Entropie-Bonus** | Leichter Bonus, wenn Album mehrere *gewählte* Communities trifft | „Mehrere deiner Stile“ |
| **Sublinearität** | z. B. `sqrt(Affinität)` pro Community | Dämpft 100 %-Treffer |

**Empfehlung:** Kosinus- oder JSD-Ähnlichkeit als Ersatz für `S_a` prototypen; γ im
`overall_score` reduzieren oder streichen, wenn die neue Passung Vielschichtigkeit schon
abbildet.

**Aufwand:** hoch (neue Metrik, Tests, Kalibrierung, Migration)  
**Nutzen:** sehr hoch langfristig — entfernt den erklärungsfeindlichen Slider

---

### Priorität 4 — Dokumentation `docs/scoring.md` (technische Referenz)

**Ziel:** Kurzreferenz für Entwickler (englische Identifiers, klare Formeln).

Kann aus diesem Dokument abgeleitet werden; Fokus auf:

- Glossar
- Code-Verweise
- „Was ist absolut vs. batch-relativ“
- Testfälle / Randfälle (stilreines Album, viele Communities, fehlende Referenzen)

**Aufwand:** gering  
**Nutzen:** mittel (Wartung, Onboarding, Agenten)

---

### Priorität 5 — API Score-Breakdown (optional)

**Ziel:** `score_components` in der Recommendation-API (Dev-Flag oder Expertenmodus).

**Aufwand:** niedrig–mittel  
**Nutzen:** mittel — Score Lab kann zunächst ohne API auskommen (Streamlit direkt auf
Python-Layer)

---

### Priorität 6 — Zwei-Ebenen-Modell (Produktstrategie)

**Ebene 1 — Harte Filter:** Rating, Jahr, Labels (absolute Skalen, unproblematisch)

**Ebene 2 — Weiches Ranking:** nur relative Ordnung nach innen

**Nach außen:** qualitative Stufen („Sehr passend / Passend / Entdeckung“) aus
**Rangquintilen**, nicht aus `0.82` als Prozent.

**Aufwand:** mittel (UX + API + Copy)  
**Nutzen:** hoch für Verständlichkeit; beendet die Illusion einer universellen %-Skala

---

## 5. Was bewusst nicht priorisiert wird

- Weitere Presets/Schieberegler **ohne** Score Lab (Kalibrierung im Blindflug)
- Absolute Schwellen beibehalten und nur UI-Texte verschönern
- Crossover nur umbenennen — das Ranking-Problem bei stilreinen Alben bleibt bei niedrigem λ

---

## 6. Empfohlene Umsetzungsreihenfolge

1. **Score Lab** — Transparenz und Experimente
2. **`score_min` / `fit_level` auf Perzentile** — nutzbare Profile über Nutzer hinweg
3. **Kosinus-Passung** prototypen; Crossover aus Nutzer-UI zurückziehen
4. **`docs/scoring.md`** (technische Kurzreferenz) parallel zu Schritt 1 pflegen

---

## 7. Offene Kalibrierungsfragen

Aus `docs/plattenradar-v1-product-api.md`, weiterhin gültig bis Score Lab beantwortet:

- Ist `α = 0.70` (Treffsicher) spürbar strenger als Ausgewogen, ohne die Liste zu leeren?
- Ist `α = 0.30` (Entdeckerisch) offen genug, ohne beliebig zu wirken?
- Ist `rating_min = 6` als gemeinsame Untergrenze passend?
- Soll „Vielschichtig“ `λ = 0.75` oder `1.0` nutzen — oder entfällt λ nach neuer Passung?
- Soll Kritikerlieblinge noch stärker auf β gehen?

---

## 8. Verwandte Dokumente

| Dokument | Inhalt |
|----------|--------|
| `docs/plattenradar-v1-product-api.md` | API, Preset-Werte, Filterfelder |
| `docs/plattenradar-design-evaluierung-2026-06-28.md` | UX zu Passung, Tags, Erklärungen |
| `src/music_review/dashboard/recommendation_scoring.py` | Implementierung der Formeln |
| `tests/music_review/dashboard/test_recommendation_scoring.py` | Unit-Tests für Scoring |

---

## 9. Änderungshistorie

| Datum | Änderung |
|-------|----------|
| 2026-06-28 | Erstanlage aus Scoring-Diskussion (Analyse, Crossover-Problem, Roadmap) |
