# Playlist Feature v2 — Redesign Plan

Status: Active  
Basis: [`playlist-pr-review-feedback.md`](playlist-pr-review-feedback.md) (PR1–PR5 + Integration v2 PO review)  
Branch: `cursor/improve-playlist-v2`

This document is the implementation plan for the next playlist iteration. It consolidates agent and product-owner feedback into phased, testable work.

---

## North Star

**Current state:** Functionally complete (form → generate → export), but still feels like a configuration tool with a table attached — not the emotional payoff of Aktuell/Entdecken.

**v2 goal:** A **two-phase journey**:

1. **Configure** — calm, symmetric, understandable controls
2. **Celebrate & export** — clear success moment, guided TuneMyMusic path, rich track rows

**Principle:** *Nicht neu bauen, sondern polieren* — polish the existing pipeline, do not rewrite it.

---

## Information Architecture

```
Phase A: CONFIGURE (default)
  - Mode cards (Neuheiten / Archiv)
  - Mode-specific fields only
  - Primary CTA: „Playlist vorbereiten“

        │ success
        ▼

Phase B: RESULT
  - Success header (name, count, source)
  - Export block (primary path + secondary options)
  - TuneMyMusic guide (open, above track list)
  - Track list
  - Collapsed „Einstellungen ändern“ → expands Phase A
```

---

## Workstreams

### A — Form stability & clarity

| ID | Issue | Solution | Priority |
|----|-------|----------|----------|
| A1 | Context line jumps layout on mode switch | Remove `playlist-entry-context` (redundant with mode cards) | P1 |
| A2 | Neuheiten vs Archiv visual imbalance | Short mode intro; group Archiv-only sections | P1 |
| A3 | Native `<select>` for Zeitraum | Segment chips (like track count) | P2 |
| A4 | Long mobile scroll before CTA | Trim intro; inline profile line | P2 |
| A5 | Archiv pool double control (chips + slider) | Single leading control or synced chips | P2 |
| A6 | Pool summary / 1000 cap unclear | Emphasize key number; „Bis 1000“ chip label | P3 |

### B — Neuheiten: Fokus control

Replace opaque „Entdecken ↔ Fokus“ slider with **3 presets** (Vielfalt / Ausgewogen / Stark fokussiert) + helper text. Rename field label away from „Fokus“.

| Priority | P0 |
| Files | `PlaylistGenerator.tsx`, `playlistExport.ts`, `PlaylistDualSlider.tsx` → chips |

### C — Archiv: Titel pro Album (backend required)

Replace slider with presets (Vielfalt / Ausgewogen / Album vertiefen) and enforce **max tracks per album** in `playlist_builder.py`.

| Priority | P0 |
| Files | `playlist_builder.py`, `playlist_service.py`, API schema, frontend payload |

### D — Zeitraum / Update-Runden

Expand options (1 / 2 / 4 / 8 / 12 / 20), show estimated pool size, explain fallback when no batch history.

| Priority | P1 |
| Files | `aktuellPage.ts`, `playlistForm.ts`, optional API |

### E — Export flow

- Two groups: **Export** (CSV primary) vs **Neue Ziehung** (Remix)
- TuneMyMusic guide open and above track list
- Combined action: CSV download + open TuneMyMusic
- Recommended path copy; freetext as alternative

| Priority | P0 |
| Files | `PlaylistGenerator.tsx`, `TuneMyMusicGuide.tsx`, `global.css` |

### F — Result presentation

| ID | Change | Priority |
|----|--------|----------|
| F1 | Remove 6-tile mosaic → compact success header | P1 |
| F2 | Release year + label in track rows | P1 |
| F3 | Larger thumbnails; initials fallback | P2 |
| F4 | Default archive name: `Plattenarchiv` (one word) | P2 |

---

## Phased Delivery

### Phase 1 — Quick wins (frontend-only) ✅ done

1. Remove context line layout jump (A1)
2. Export button grouping + mobile layout (E)
3. TuneMyMusic prominent + open by default (E)
4. Success header after generation
5. Form collapse after generation (two-phase model)
6. `Plattenarchiv` default name (F4)
7. Chip label „Bis 1000“ instead of „Max.“ (A6)

**Exit criteria:** PO re-test mobile + desktop; Playwright screenshots updated.

### Phase 2 — Control redesign ✅ done

1. Neuheiten mood presets (B) — Vielfalt / Ausgewogen / Stark fokussiert
2. Zeitraum expansion + fallback copy (D) — chips 1/2/4/8/12/20
3. Archiv pool control simplification (A5) — chips only, slider removed
4. Remove mosaic, compact success header (F1)
5. Thumbnail size + initials fallback (F3)

### Phase 3 — Backend album-spread logic ✅ done

1. Per-album track caps in `playlist_builder.py` (C)
2. API schema + service wiring
3. Archiv preset chips → new API field
4. Year + label in export items (F2)
5. Builder regression tests

### Phase 4 — Polish & parity ✅

1. Zeitraum segment chips (A3) — done in Phase 2
2. Optional „Erweitert“ accordion — playlist name + fine sliders
3. Playwright references (form + result, both modes, mobile)
4. Update feedback doc with v2 review section

**Exit criteria:** CI visual regression green; PO re-test optional.

---

## Component Map (target)

```
PlaylistGenerator.tsx          # orchestrator, phase state
├── PlaylistConfigureForm.tsx  # extracted form (phase 2+)
├── PlaylistResultPanel.tsx    # success, export, track list (phase 2+)
│   ├── PlaylistExportActions.tsx
│   ├── TuneMyMusicGuide.tsx
│   └── PlaylistTrackList.tsx
playlistForm.ts                # presets, pool logic, copy helpers
playlistExport.ts              # API payload, TuneMyMusic URLs
playlist_builder.py            # album spread enforcement (phase 3)
```

---

## Out of Scope (v2)

- API limit increase beyond 1000
- Lightbox on artist thumbnails
- Rating / match score in result rows
- Preview before generation
- Deezer/Spotify direct integration

---

## Success Criteria (qualitative)

After v2, a tester should answer **yes** to:

1. Can I configure without understanding weighting math?
2. After generating, do I immediately know what to do next (TuneMyMusic)?
3. Does Archiv „Vielfalt“ give at most one track per album? (phase 3)
4. Is the layout stable when switching Neuheiten ↔ Archiv?
5. Does the result phase feel like a payoff, not an appendix?

---

## Changelog

| Datum | Phase | Änderung |
|-------|-------|----------|
| 2026-07-03 | Plan | Initial v2 redesign plan from PR feedback doc |
| 2026-07-03 | Phase 1 | Quick wins: export flow, form collapse, copy fixes |
| 2026-07-03 | Phase 2 | Control presets, mosaic removal, initials fallback |
| 2026-07-03 | Phase 3 | Album-spread backend rules, year/label in rows |
| 2026-07-03 | Phase 4 | Erweitert accordion, Playwright refs, feedback doc v2 |
| 2026-07-03 | Phase 2 | Mood presets, update-round chips, pool chips only, mosaic removed, initials |
| 2026-07-03 | Phase 3 | Album-spread backend rules, API field, year/label in export rows |
