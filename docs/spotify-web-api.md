# Spotify Web API (Music Review)

This document summarizes how this project uses the Spotify Web API and what we know about **quota modes**, **rate limits**, and **practical constraints**. It is maintainer-facing reference material, not end-user copy.

Official documentation changes over time; always verify against [Spotify for Developers](https://developer.spotify.com/documentation/web-api).

## How this project uses Spotify

- **OAuth** (Authorization Code flow with PKCE): users connect their Spotify account from the Streamlit app. Tokens live in Streamlit session state only.
- **Search**: track resolution for playlist generation (many `search` calls per playlist build; see `src/music_review/dashboard/newest_spotify_playlist.py`).
- **Playlists**: create playlists and add tracks (`SpotifyClient` in `src/music_review/integrations/spotify_client.py`).
- **Configuration**: environment variables documented in `SpotifyAuthConfig.from_env` (e.g. `SPOTIFY_CLIENT_ID`, `SPOTIFY_REDIRECT_URI`, `SPOTIFY_SCOPES`, optional `SPOTIFY_CLIENT_SECRET`).

All requests from every user share the **same Spotify app** (same Client ID) unless you register separate apps.

## Quota modes

Spotify distinguishes at least:

### Development mode (default for new apps)

- Intended for building the integration and **limited end-user access**.
- **User allowlist**: up to **5 authenticated Spotify users** may use the app for API-backed features. You add them in the [Developer Dashboard](https://developer.spotify.com/dashboard) under the app’s **Settings → Users Management** (name + Spotify email). Users not on the list may still complete login in some cases, but API calls with their token can fail (e.g. **403**).
- The **app owner** must have **Spotify Premium** for development-mode apps to function (per Spotify’s quota-mode documentation).
- **Lower** Web API rate limit than extended quota mode.

See: [Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

### Extended quota mode

- For apps meant for a **wider audience**: **unlimited** users (no development allowlist in the same way) and a **higher** Web API rate limit than development mode.
- **Not a self-service “paid tier”** in the public docs: access is via **application / review**, not a documented retail price list.
- **Eligibility (policy changes over time)**: Spotify has stated that **extended access / partner applications** are aimed at **organizations** (not individuals) and listed requirements such as an established business entity, a launched service, minimum active-user thresholds, and commercial viability. As of **May 15, 2025**, Spotify indicated applications are accepted **only from organizations**, via a company email and a specific form—see Spotify’s blog post [Updating the Criteria for Web API Extended Access](https://developer.spotify.com/blog/2025-04-15-updating-the-criteria-for-web-api-extended-access) and the linked [Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) page.

**Implication for solo / non-company developers:** extended quota mode is **not** realistically available under current public criteria if you are not an eligible organization. Plan for **development mode** limits (5 users, lower rate limit) unless your situation changes or Spotify publishes new paths.

## Rate limits

### What Spotify documents

- Limits are based on the **number of calls your app makes in a rolling 30-second window** (not a single fixed “requests per second” number in the main rate-limit doc).
- The effective cap **depends on quota mode** (development vs extended). Spotify does **not** publish a single universal numeric cap (e.g. “N requests per 30 seconds”) on the primary [Rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits) page for all apps.
- When exceeded, the API returns **HTTP 429 Too Many Requests**. Responses often include a **`Retry-After`** header (value in **seconds**) indicating how long to wait before retrying.
- **Per-endpoint** limits may apply (Spotify cites **playlist image upload** as an example). Details may appear in the API response body for that endpoint.

See: [Rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits).

### Implications for Music Review

- **One generated playlist** triggers **many** search (and related) calls—not one API call per playlist.
- **Multiple users** using the same Client ID **add up** against the same app quota; concurrent or repeated “regenerate preview” usage increases **429** risk.
- Prefer **backoff** honoring `Retry-After`, **fewer redundant queries**, and **caching** where safe (see project `TODOs.md`: `spotify-search-cache-trim`, `spotify-playlist-regenerate-hint`).

## Operational checklist

1. Register the app in the [Developer Dashboard](https://developer.spotify.com/dashboard); set redirect URI to match `.env`.
2. In development mode, **allowlist** every beta tester (max 5).
3. Request OAuth scopes actually needed (defaults include `playlist-read-private` for `GET /me/playlists` name matching plus playlist modify scopes); reconnect after scope changes.
4. Monitor dashboard **API traffic** graphs when debugging 429s.
5. For large production audiences, extended quota requires **Spotify approval** under current **organization-focused** criteria—not something individuals can assume.

## Policy and product updates

Spotify occasionally updates developer access rules (e.g. blog posts in **2025** and **2026**). Before relying on this file for compliance or product decisions, re-read:

- [Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)
- [Rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits)
- Recent posts under [Spotify for Developers — Blog](https://developer.spotify.com/blog)

## Related project files

- `src/music_review/integrations/spotify_client.py` — HTTP client and OAuth helpers
- `pages/9_Spotify_Playlists.py` — connection UI and manual playlists
- `pages/neueste_spotify_playlist_section.py` — “newest reviews” playlist builder
- `TODOs.md` — open improvements (caching, UI hints for rate limits)
