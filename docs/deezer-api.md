# Deezer API (Music Review)

Maintainer-facing reference for how this project integrates with the
[Deezer Developer API](https://developers.deezer.com/api). It documents the
OAuth flow, the per-environment configuration, the rate-limit budget, and the
deliberate design choices that differ from the Spotify integration.

Official documentation evolves; verify any behaviour against the live
[Deezer API reference](https://developers.deezer.com/api).

## How this project uses Deezer

- **OAuth** (Authorization Code, no PKCE): users connect their Deezer account
  from the Streamlit app via `pages/deezer_connection_ui.py` and the kickoff
  in `pages/deezer_oauth_kickoff.py`.
- **Token storage**: tokens are stored both in the user's encrypted profile
  database row (`oauth_token_json`) and mirrored to Streamlit session state
  via `pages/deezer_token_persist.py`.
- **Search**: track resolution for playlist generation. Each playlist build
  triggers many `search/track` calls; see
  `src/music_review/dashboard/newest_deezer_playlist.py`.
- **Playlists**: create-or-replace by name and set visibility through
  `src/music_review/dashboard/neueste_deezer_publish.py`, all backed by
  `DeezerClient.playlist_*` methods in `src/music_review/integrations/deezer_client.py`.
- **OAuth callback**: `pages/10_Deezer_Callback.py` exchanges the authorization
  code, restores the originating session, and redirects back to the unified
  playlist hub (`pages/9_Playlist_Erzeugen.py`).

## Configuration: environment variables

Deezer credentials live in `.env` (gitignored). The shared **project app**
mode is the default: a single Deezer Developer App that all users connect
through. The same variables are used by the lightweight `.env` loader in
`DeezerAuthConfig.from_env()`.

| Variable | Required | Description |
| --- | --- | --- |
| `DEEZER_APP_ID` | yes | Application ID from the Deezer Developer dashboard. |
| `DEEZER_APP_SECRET` | yes | Application secret from the same dashboard. |
| `DEEZER_REDIRECT_URI` | yes | Must point to `pages/10_Deezer_Callback.py` (default Streamlit URL slug: `deezer_callback`). The path's last segment is normalized to the canonical Streamlit page path. |
| `DEEZER_PERMS` | no | Comma-separated permission list. Defaults to `manage_library,offline_access`. **Always include `offline_access`** because Deezer does not issue refresh tokens; without it the user would have to reconnect after expiry. |

Example `.env` snippet:

```dotenv
DEEZER_APP_ID=1234567
DEEZER_APP_SECRET=ab12cd34ef56gh78
DEEZER_REDIRECT_URI=http://127.0.0.1:8501/deezer_callback
DEEZER_PERMS=manage_library,offline_access
```

When developing locally, register the same redirect URI under your Deezer
Developer App's *Application domain* / *Redirect URL* settings. The host
(`localhost` vs `127.0.0.1`) must match exactly because Streamlit cookies
are scoped per host.

### Per-user app credentials (optional)

Users who hit the shared app's quota can register their own Deezer Developer
App and store their personal `app_id` / `app_secret` via the Streaming-
Verbindungen page. These are persisted in the user database
(`deezer_app_id`, `deezer_app_secret`) and loaded by
`DeezerAuthConfig.from_user_credentials()`. The redirect URI still falls
back to the shared `.env` value unless overridden explicitly.

## OAuth flow specifics

Deezer's OAuth2 implementation has three notable deviations from Spotify:

1. **No PKCE**: the authorize endpoint does not accept `code_challenge`/
   `code_verifier`. CSRF protection is provided by the `state` query parameter
   only (see `pages/deezer_oauth_kickoff.py`).
2. **Form-encoded token response**: `oauth/access_token.php` returns
   `access_token=...&expires=...` as `text/plain`, not JSON. The client parses
   both shapes (`_parse_access_token_response` in `deezer_client.py`).
3. **No refresh tokens**: the only way to obtain a non-expiring token is to
   request the `offline_access` permission. The client always includes it by
   default; if you customize `DEEZER_PERMS`, keep `offline_access` in the list.

Authenticated API calls pass the bearer token as `?access_token=...` in the
query string instead of an `Authorization` header.

Application-level errors are returned inside HTTP 200 responses with an
`error` envelope; the client converts those to `RuntimeError` so callers can
react uniformly.

## Rate limits and throttling

Deezer enforces an **IP-based rate limit of approximately 50 requests per
5 seconds** per app (and per IP). Exceeding it triggers application-level
"Quota limit exceeded" errors rather than HTTP 429. Because the limit is
per-IP rather than per-user, a shared project app is viable as long as
client-side throttling is in place.

The `DeezerClient` caps bulk request rate via
`DEEZER_BULK_REQUEST_INTERVAL_SECONDS` (currently ~0.1 s between calls,
i.e. ~10 req/s headroom under the 10 req/s average ceiling). Playlist
generation runs in a background thread (`neueste_deezer_generate_job.py`)
to keep Streamlit responsive while the throttled search calls complete.

Practical implications for Music Review:

- One generated playlist still triggers many search calls.
- Multiple users on the same IP (typical for the shared deployment) compete
  for the same per-IP budget.
- Use the shared `StreamingCatalogCache` (Spotify URIs and Deezer URIs share
  the same cache namespace via the `(provider, key)` tuple) to avoid
  re-resolving tracks the deployment already knows.

## Operational checklist

1. Register the app at the [Deezer Developer dashboard](https://developers.deezer.com/myapps);
   set the redirect URL to the same value as `DEEZER_REDIRECT_URI`.
2. Store `DEEZER_APP_ID`, `DEEZER_APP_SECRET`, and `DEEZER_REDIRECT_URI` in
   `.env`. Restart Streamlit after changes (the loader reads `.env` once
   per process).
3. Keep `offline_access` in `DEEZER_PERMS`; otherwise tokens expire silently
   and users have to reconnect.
4. When debugging: tail the Streamlit logs for `DeezerClient` warnings
   (rate-limit messages and parse fallbacks both log via the standard
   `music_review` logger).
5. For users who hit the shared quota, point them at the Streaming-
   Verbindungen page to register their own Deezer app.

## Related project files

- `src/music_review/integrations/deezer_client.py` -- HTTP client, OAuth helpers,
  rate-limit throttling.
- `src/music_review/dashboard/newest_deezer_playlist.py` -- search-based track
  resolution for playlist generation.
- `src/music_review/dashboard/neueste_deezer_publish.py` -- create-or-replace
  playlists by name and set visibility.
- `src/music_review/dashboard/neueste_deezer_generate_job.py` -- background-
  safe pipeline used by the Streamlit UI.
- `pages/9_Playlist_Erzeugen.py` -- unified playlist hub (Spotify + Deezer).
- `pages/10_Deezer_Callback.py` -- OAuth callback; redirects back to the hub.
- `pages/deezer_connection_ui.py`, `pages/deezer_oauth_kickoff.py`,
  `pages/deezer_token_persist.py` -- connection UI, kickoff, token persistence.
- `pages/neueste_deezer_playlist_section.py` -- Streamlit section reused by
  the unified hub for both newest reviews and the album archive.

## Related project rules and resources

- [Deezer API reference](https://developers.deezer.com/api)
- [OAuth flow documentation](https://developers.deezer.com/api/oauth)
- This project's Spotify counterpart: [`docs/spotify-web-api.md`](spotify-web-api.md)
