# Plattenradar v1 Frontend Concept

Status: Working draft  
Branch: `develop`

This document captures the UX and frontend shell decisions for Plattenradar v1.
It complements `docs/plattenradar-v1-product-api.md` and should be updated after
each interview round.

## Product Feeling

Plattenradar should feel like a music discovery product, not like a business
dashboard or data-science tool.

Working motto:

> Der schnellste Weg zu Alben, die zu dir passen.

This is a guiding sentence, not necessarily final visible copy.

## Visual Direction

The frontend should lean closer to a music magazine than to an analytical
dashboard. It should be enjoyable to browse, but still structured enough to make
recommendations, filters, and playlists easy to use.

Implications:

- Music and albums are the hero, not charts or formulas.
- The UI should avoid a business-tool feel.
- Data-science logic should stay in the background and serve discovery.
- Rankings are useful, but should not dominate the visual identity.
- The app needs warmth and editorial rhythm despite limited visual media.

## Relationship To Plattentests.de

Plattenradar is not a competitor to plattentests.de. It is an appreciative layer
on top of the plattentests.de review archive.

Product stance:

- plattentests.de remains the source and should be visibly credited.
- Recommendation cards should link back to the original plattentests.de reviews.
- Plattenradar adds targeted discovery and playlist workflows that
  plattentests.de itself does not try to provide.
- The tone should communicate respect for the original archive and its
  long-running editorial work.

## Audience

The UI is for music fans first, not data scientists. It may contain enough depth
for music enthusiasts, but it should not assume that users enjoy technical
ranking mechanics.

Nerdiness level:

- Visible music enthusiasm is welcome.
- Visible data-science machinery should be subtle.
- Technical terms such as raw scores, alpha, beta, gamma, or model internals
  should not be part of the normal UI.

## Desired First Result Emotion

The first strong result screen should create this reaction:

> Krass, das kenne ich alles noch nicht. Ich will sofort reinhören.

Secondary reaction:

> Das klingt, als könnte es wirklich zu mir passen.

This means the result screen should make listening feel like the natural next
step. Playlist generation and export should therefore be close to the
recommendation experience, not hidden as a distant utility.

## Visual Asset Constraint

Album covers and artist photos would make the product more magazine-like, but
copyright and data-source limitations mean v1 must not depend on them.

Design implication:

- The first frontend shell must work beautifully without covers.
- Recommendation cards need strong typography, spacing, tags, ratings, and
  subtle fit signals.
- Later image support can be explored only if copyright-safe sources or explicit
  permissions are available.

## Open Design Questions

- How can the app create a music-magazine feeling without album covers?
- Should Plattenradar use editorial-style sections, typographic hierarchy, and
  review excerpts as the main visual material?
- How prominent should the plattentests.de attribution be on cards and pages?
- Where should playlist generation sit in the first result experience?

## Information Architecture

For a returning user with a saved profile, the app should open on the newest
reviews experience. This is the part of Plattenradar that changes most often and
therefore gives returning users a reason to come back.

Default return state:

> Aktuell: personal recommendations from the newest plattentests.de reviews.

The archive recommendations remain important, but they are more static. They
belong in a separate discovery area rather than being the default return screen.

## Main Navigation

Preferred direction:

- `Aktuell`
- `Entdecken`
- `Playlists`
- `Musikprofil` or another still-to-be-finalized profile label
- `Konto` or account access as a smaller secondary entry

Working labels:

- `Aktuell` means newest reviews, personalized for the saved or temporary
  profile.
- `Entdecken` means archive discovery across the historical review corpus.
- `Playlists` means generated listening lists and export workflows.
- `Musikprofil` means the user's style selections, weights, and filters.

The label for the profile area is still open. `Mein Geschmack` feels too plain,
`Meine Musikpräferenzen` is too long, and `Musikprofil` is currently the most
practical working label.

## Start Page Decision

Plattenradar v1 should not use an extra home page after a profile exists. A
generic tile hub would likely become an unnecessary intermediate layer.

Rules:

- Returning user with saved profile: open `Aktuell`.
- Guest without profile: open the taste setup flow.
- Guest with temporary profile: continue to the last recommendation context when
  possible, otherwise default to `Entdecken`.

The old Streamlit-style tile hub should not be the primary model for the new
frontend shell.

## Aktuell vs Entdecken

`Aktuell` and `Entdecken` should be two clearly separated areas because their
user intent and tone are different.

`Aktuell`:

- time-based and returning-user oriented,
- focuses on newest reviews since the last updates,
- should include a short personalized batch message,
- should answer: "Was ist neu und passt zu mir?"

`Entdecken`:

- archive-based and exploratory,
- helps when users feel they have nothing good to listen to,
- should answer: "Was habe ich im riesigen Archiv noch verpasst?"

Both areas can share card components, filters, pagination, and playlist actions,
but they should not feel like one generic table with a source filter.

## Aktuell Batch Message

The `Aktuell` screen should include a short personal message above the result
list. It should summarize how promising the current batch is for the user's
profile.

Examples of intended tone:

- "Diese Woche sind ein paar Alben dazugekommen, die gut zu deinem Musikprofil
  passen."
- "Diese Woche war es etwas mauer, aber hier sind die besten Treffer aus dem
  neuen Schwung."

The exact text can be generated from the score distribution later. For the first
frontend shell, it can be static or mocked as long as the layout leaves room for
it.

## Playlist Placement

Playlist generation should be both:

- a direct action from recommendation contexts,
- and a dedicated main area for managing/exporting playlists.

Design rule:

> Users should be able to go from "this looks interesting" to "I can listen to
> this now" without hunting through the navigation.

Implications:

- Recommendation pages should have an obvious playlist action near the list.
- The dedicated `Playlists` area can collect source choices, export format, and
  generation settings.
- The transition from recommendations to playlist generation must feel seamless,
  not like switching to an unrelated tool.

## First-Time User Flow

Users without a saved or temporary profile should not land on an empty dashboard
or a generic navigation hub. They need a short welcome moment that makes the
value proposition clear and then moves them directly into taste setup.

Recommended v1 flow:

1. Welcome screen.
2. Taste setup.
3. `Entdecken` result screen as the first aha moment.
4. Subtle save prompt after recommendations are visible.

### Welcome Screen

The welcome screen should be brief. It should not become a marketing landing
page.

Purpose:

- explain what Plattenradar does in one or two short sentences,
- set expectation that recommendations need a music profile,
- offer a clear primary action to start taste setup,
- offer a secondary login action for returning users.

Suggested structure:

- Product name and short value sentence.
- One concise explanation:
  - Plattenradar helps you find albums from the plattentests.de archive and new
    reviews that fit your music profile.
- Primary action:
  - `Musikprofil erstellen`
- Secondary action:
  - `Einloggen`

The taste setup should start after the primary button click. It should not be
embedded below a long welcome page, because the first visit needs momentum.

### Login Detection

If the browser/session already has a valid login, the welcome screen should be
skipped and the user should land on `Aktuell`.

If there is no valid login and no temporary profile, the user sees the welcome
screen.

### Explanation Before Taste Setup

The user needs only a short explanation before step 1. The UI should avoid
lengthy onboarding text.

Principle:

> Explain just enough so users understand why they are choosing styles before
> they see recommendations.

### First Aha Destination

After completing taste setup for the first time, the user should go to
`Entdecken`, not `Aktuell`.

Reasoning:

- The archive is the strongest first impression because it can surface unknown
  albums from many years of reviews.
- `Aktuell` is more valuable for returning users because it changes over time.
- The first visit should demonstrate the unique archive-discovery value of
  Plattenradar.

### Save Prompt Strategy

Saving should be offered after the user has seen value, not before. Asking for
an account too early creates friction before trust exists.

Recommended v1 behavior:

- Do not require registration before taste setup.
- Do not interrupt immediately after taste setup.
- Show recommendations first.
- Then show a subtle but visible save prompt near the recommendation results.

Suggested prompt tone:

> Dieses Musikprofil speichern, damit du beim nächsten Besuch direkt neue
> Empfehlungen bekommst.

Additional save prompts may appear in context:

- when generating a playlist,
- when changing filters after a useful result,
- when leaving the page with an unsaved temporary profile.

These prompts should be lightweight, not modal by default.

### After Saving

When a guest saves a profile, the current recommendation context should remain
stable. The app should not suddenly move them away from the result list.

Recommended v1 behavior:

- Save profile.
- Confirm inline.
- Keep the user on the current `Entdecken` result screen.
- Offer a secondary action:
  - `Zu Aktuell wechseln`

On the next visit, the saved-profile user starts on `Aktuell`.

## Recommendation Results

Recommendation result screens should feel like browsing a curated music archive,
not like operating a ranking dashboard. The primary user behavior is browsing
albums and opening interesting reviews.

Primary result action:

> Open individual reviews on plattentests.de.

Secondary actions:

- adjust filters,
- generate a playlist from the current recommendation context,
- load more results.

Playlist generation is important, but it should not dominate individual
recommendation cards.

## Recommendation Cards

Recommendation cards should prioritize album and review context over immediate
playlist mechanics.

Required visible card information:

- artist,
- album,
- year or release date,
- plattentests.de rating,
- fit signal,
- genre/community tags,
- short review excerpt,
- link to the original plattentests.de review.

Not required on every card:

- playlist availability,
- streaming-service status,
- technical score details.

### Card Link Behavior

The artist/album heading should link to the original plattentests.de review.
This keeps the source relationship clear and makes reading the review feel like
the natural primary action.

A separate `Rezension lesen` button can be considered later if link
discoverability is not strong enough, but the heading link is the preferred v1
behavior.

### Fit Display

The fit signal should avoid feeling like a data-science score, but users still
need some sense of ranking distance.

Design tension:

- A precise number helps users understand how close ranks are.
- A visible number can make the UI feel too analytical.
- A purely symbolic signal may be too vague.

Recommended v1 direction:

- Use a subtle fit label rather than a large score badge.
- Keep the exact score visually secondary.
- Combine the score with matched style tags so the number never stands alone.

Possible display:

- small text: `Sehr passend`, `Passend`, `Interessanter Randbereich`,
- optional secondary text or tooltip: `87% Fit`,
- highlighted matching tags as the main explanation.

The exact visual treatment should be tested in the frontend shell. The goal is
to preserve ranking transparency without turning each card into a metrics card.

### Filters On Result Screens

Filters should be adjustable from the result screen, not only from a separate
profile/settings page. This helps users understand how their choices affect the
recommendations.

Design rule:

> Filter adjustment should be close to the results, but not visually louder than
> the albums.

Possible v1 structure:

- compact filter summary above the list,
- expandable filter panel or side panel,
- immediate re-run action after filter changes,
- clear indication when the current list reflects unsaved temporary changes.

## Visual System Without Covers

The result UI must work without album covers or artist photos. This is a core v1
constraint, not a temporary bug.

Preferred result density:

- overview first,
- compact enough to scan many recommendations,
- richer than a plain table,
- not dependent on large magazine-style image cards.

The recommended direction is a refined editorial list: each item is a structured
text card with strong hierarchy, tags, rating, and excerpt. It should be more
beautiful than a database row, but more scannable than large image-led cards.

### Review Excerpts

Cards should show a teaser, not the full review.

Recommended v1 behavior:

- one or two lines, or one short sentence group,
- visibly truncated with an ellipsis,
- enough text to create editorial flavor,
- clear path to continue reading on plattentests.de.

This also supports the source relationship: Plattenradar should surface and
route users to plattentests.de, not reproduce the full review experience.

### Card Density Modes

Multiple display modes can be considered later, but v1 should start with one
excellent default view. The default should prioritize overview and browsing.

Possible future modes:

- compact list,
- richer editorial cards.

For the first frontend shell, avoid building mode switching unless it becomes
necessary during visual prototyping.

### Visual Building Blocks

Useful substitutes for missing covers:

- precise typography,
- genre/community tags,
- subtle fit markers,
- plattentests.de rating as a small graphic or strong metadata element,
- short review excerpt,
- generous but controlled whitespace,
- thin dividers or calm card borders.

Avoid:

- overly decorative cards,
- fake cover placeholders,
- loud score badges,
- dense dashboard tables,
- visual elements that distract from album discovery.

### Top Recommendations

Archive results should use a consistent card structure. Highlighting the top
three archive recommendations would imply a precision that the ranking may not
really have, especially when many high-ranking albums are very close together.

`Aktuell` may support one stronger highlight if the current batch contains a
clearly excellent match. This should be threshold-based, not position-based.

Open design decision:

- define later what score distribution justifies a highlighted top item on
  `Aktuell`.

### Color Direction

Preferred mood:

> hell, editorial, ruhig, professionell.

The UI should feel pleasant and polished, not cheap or overly playful.

The current assets are usable but should not dominate the new frontend system:

- `assets/plattenradar_logo.png` is clear and memorable enough for navigation
  branding, but should be used smaller and calmer in the new shell.
- `assets/plattenradar_background.png` is light and pleasant, but soft and
  somewhat generic. It can inspire the bright tone, but should not become a
  full-page background pattern for the main app.

Recommendation:

- keep the existing logo as provisional brand asset,
- use the existing background only sparingly, if at all,
- design the shell primarily through typography, spacing, tags, and editorial
  layout,
- consider a later dedicated visual-identity round before final polish.

## Music Profile And Filter Setup

The music profile setup should not become one flat settings page. The existing
logic is genuinely progressive: broad styles constrain or guide detailed style
clusters, and detailed style choices then feed filter and weighting decisions.

Recommended v1 direction:

> Use a guided setup workspace, not a dense settings form.

This should feel calmer and more modern than the current Streamlit wizard, but
it should preserve the staged dependency of the current flow.

### Setup Structure

The three existing conceptual steps remain valid:

1. Broad style areas.
2. Detailed style clusters.
3. Filters, presets, and weights.

They do not have to look like three separate old-school wizard pages, but the UI
should make the progression visible.

Recommended shell:

- stepper or progress rail,
- main panel for the current decision,
- compact side summary showing what has already been selected,
- clear back/continue controls,
- no forced account creation during setup.

This gives users orientation without dumping all controls onto one page.

### Backtracking And Dependency Changes

Users should be able to go back at any time. However, changing earlier choices
can invalidate or alter later choices, so the UI needs explicit cascade handling.

Rules:

- Going back is always possible.
- Changing broad style areas can remove detailed style clusters that no longer
  belong to the active broad areas.
- Changing detailed style clusters can remove or reshape per-style weights.
- The UI should show a gentle note when later choices were adjusted because of
  earlier changes.

Suggested wording:

> Einige Detailauswahlen wurden angepasst, weil sich deine groben
> Stilrichtungen geändert haben.

The goal is not to warn dramatically, but to keep the user from feeling that the
app silently lost work.

### Presets In Setup And Results

Presets such as `Treffsicher`, `Ausgewogen`, `Entdeckerisch`,
`Kritikerlieblinge`, and `Vielschichtig` are part of the music profile because
they set filter and ranking preferences. They should therefore appear in setup,
especially in the final filter/weighting stage.

At the same time, users will understand presets best when they can see result
changes. Presets should also be available from recommendation result screens as
temporary tuning controls.

Recommended behavior:

- In setup, presets set the initial profile values.
- In result screens, presets can be applied temporarily to the current result
  context.
- Applying a preset on a result screen should not automatically overwrite the
  saved profile.
- If the user is logged in and changes result filters, the UI should offer a
  lightweight `Änderungen speichern` action.
- If the user is a guest, the UI should offer `Musikprofil speichern`.

Design principle:

> Experimenting with results should feel safe. Saving should be explicit.

### Editing An Existing Music Profile

Editing an existing profile should use the same underlying components as first
setup, but the entry experience can be more compact.

Recommended model:

- First-time setup: guided step-by-step flow.
- Later editing: `Musikprofil` page with three editable sections.
- Opening a section enters the same focused editor used during setup.
- If the user edits an earlier section, downstream sections show that they may
  need review.

This avoids maintaining two different mental models while still making returning
profile edits faster.

Possible `Musikprofil` page structure:

- summary of selected broad style areas,
- summary of detailed style clusters,
- summary of current preset/filter choices,
- actions:
  - `Stilrichtungen bearbeiten`,
  - `Details bearbeiten`,
  - `Filter und Gewichtung bearbeiten`,
  - `Empfehlungen anzeigen`.

### Result-Screen Filter Changes

Recommendation result screens should support lightweight filter experimentation.
This is especially important because users understand many filters only when
they see the result list change.

However, result-screen controls should not expose the entire setup at full
weight.

Recommended v1 behavior:

- Show a compact filter/preset bar above results.
- Put detailed controls in an expandable panel or side drawer.
- Mark unsaved changes clearly but calmly.
- Allow users to apply changes to refresh the list.
- Offer explicit save only after changes produce a useful state.

Example states:

- `Gespeichertes Musikprofil`
- `Temporär angepasst`
- `Ungespeicherte Änderungen`

This solves the core tension: users can explore freely without accidentally
changing their long-term profile.

## Playlist Flow

Playlist generation is a core value of Plattenradar, but it should not dominate
recommendation cards. It should feel like the natural next step after browsing a
promising recommendation list.

### Playlist Entry Points

The strongest playlist action should sit above the result list, close to the
list title, batch message, and filter summary.

Reasoning:

- Users should see the playlist option before scrolling.
- The action belongs to the current recommendation context.
- It should be more prominent than a footer action.
- It should not be crammed into every recommendation card.

Recommended pattern:

- Result screen header:
  - title,
  - short explanatory/batch message,
  - primary or secondary action: `Playlist erzeugen`.

The dedicated `Playlists` navigation area remains useful, but v1 should treat it
mainly as a generator, not as a history or management system.

### Generator Step

When users start playlist generation from `Aktuell` or `Entdecken`, they should
see a short settings step before export. The playlist should not be generated
blindly from the list without showing relevant choices.

Required v1 settings:

- source context:
  - `Aktuell`,
  - `Entdecken`,
- number of tracks,
- focus strength:
  - balanced across the recommendation list,
  - more strongly focused on top recommendations,
- variation:
  - allow users to generate a different but still suitable playlist,
- playlist name:
  - default: `Plattenradar YYYY-MM-DD`,
  - editable but not visually dominant.

TXT and CSV should not be framed as a difficult pre-export choice. Both export
forms can be offered after generation:

- copyable text variant,
- downloadable TXT,
- downloadable CSV.

### Dedicated Playlists Area

For v1, `Playlists` should be a generator area:

> Neue Playlist erzeugen.

It does not need to store playlist history because generated playlists live
outside Plattenradar after users import them into their music service.

Future automation:

- recurring playlist emails,
- subscription settings,
- delivery preferences,
- automatic new-review playlists.

Those future settings may later live either in `Playlists` or account settings.
For v1, the frontend shell should leave room for this future but not implement
playlist management.

Future favorites:

- logged-in users can mark albums from recommendation cards as favorites,
- favorites are stored on the user account (not only in session storage),
- later, playlist generation may use favorites as a source pool in addition to
  `Aktuell` and `Entdecken`.

The recommendation card should eventually expose a calm favorite action. Until the
API exists, the shell may show the affordance only for authenticated users with
a save/login prompt for guests.

### After Generation

After generating a playlist, the most important next step is helping users move
it into their music service.

The generated playlist view should show:

- the playlist content in a readable, pleasant format,
- a copy action for the text version,
- download actions for TXT and CSV,
- concise instructions for TuneMyMusic or equivalent import flow,
- a link or hint back to the recommendation context.

The primary post-generation message should answer:

> Wie bekomme ich diese Playlist jetzt in meinen Musikdienst?

Generating another playlist variation is useful, but secondary.

## Account, Login, And Saving

The frontend must make login available without making registration an early
barrier. Users should be able to explore first, then save once they have seen
useful recommendations.

### Login Visibility

Login should always be reachable because returning users may arrive from a new
device without a valid cookie or session.

Recommended v1 behavior:

- Show a small `Einloggen` entry in the global header when logged out.
- Also show `Einloggen` as secondary action on the welcome screen.
- Do not force login before taste setup.
- After login, route users with a saved profile to `Aktuell`.

This supports both first-time users and returning users who are not recognized
by the current browser.

### Save Registration Flow

When a guest has seen recommendations and chooses to save the music profile, the
registration flow should not pull them away from the current result list.

Recommended pattern:

> Lightweight modal or inline dialog over the current context.

Purpose:

- keep the recommendation list visible or clearly preserved,
- make profile saving feel low-friction,
- avoid making users worry that their current settings will be lost.

Required fields:

- email,
- password.

The product can keep this simple because v1 stores only a music profile and does
not handle sensitive commercial data such as payment details.

### After Registration

After successful registration:

- the user is immediately logged in,
- the current temporary music profile is saved,
- the current recommendation list remains visible,
- an inline confirmation is shown,
- no hard redirect happens.

The user may then continue browsing, generate a playlist, or switch to `Aktuell`.

### Unsaved Changes For Logged-In Users

If a logged-in user changes filters or presets in a result context, those
changes should initially be temporary.

Recommended UI state:

- show a calm `Ungespeicherte Änderungen` indicator,
- show an explicit `Änderungen speichern` button,
- do not auto-overwrite the saved profile,
- avoid heavy warnings during normal experimentation.

If the user leaves with unsaved changes, a gentle confirmation can be considered
later. For the first shell, the visible unsaved state plus save button is enough.

### Visible Account Features

The user-facing account area should remain small but complete enough for trust.

V1 visible account features:

- show email address,
- logout,
- save/overwrite music profile,
- change password,
- delete account.

Implementation can phase these in, but the frontend concept should reserve
space for them. Profile saving and logout are required for the first useful
account flow; password change and account deletion can follow once basic auth is
stable.

## Frontend Shell MVP

The first frontend implementation should be a shell, not a complete product
rewrite. It should prove the new product structure, navigation, API contracts,
and visual direction without trying to replace every Streamlit detail at once.

Recommended stack:

- Vite,
- React,
- TypeScript.

Reasoning:

- The app is primarily an authenticated client against the local/FastAPI backend.
- Server-side rendering and SEO are not central v1 requirements.
- Vite keeps the first shell lightweight and easy to understand.

### MVP Goal

Build a usable frontend foundation that can:

- show the Plattenradar app frame,
- route between main areas,
- fetch API-driven preset/filter metadata,
- display mocked or real recommendation cards,
- demonstrate the first-time and returning-user structure,
- leave clear extension points for login, playlists, and full taste setup.

The shell should answer:

> Does the new Plattenradar already feel like the right product?

It does not need to answer:

> Has every Streamlit feature already been rebuilt?

### Routes

Initial route set:

- `/`
  - redirects based on known local state:
    - logged in with saved profile: `/aktuell`,
    - no profile: `/willkommen`,
    - temporary profile: last recommendation route or `/entdecken`.
- `/willkommen`
  - short welcome screen with `Musikprofil erstellen` and `Einloggen`.
- `/profil/setup`
  - guided music profile setup workspace.
- `/aktuell`
  - newest-review recommendations for the current profile.
- `/entdecken`
  - archive recommendations for the current profile.
- `/playlists`
  - playlist generator.
- `/musikprofil`
  - profile summary and edit entry points.
- `/konto`
  - small account area for email, logout, and later account actions.

If implementation needs an even smaller first pass, `/konto` can begin as an
account popover in the header while the route remains reserved.

### App Layout

Global shell:

- top navigation with `Aktuell`, `Entdecken`, `Playlists`, `Musikprofil`,
- right-side account entry:
  - `Einloggen` when logged out,
  - email/account menu when logged in,
- compact brand mark using the existing logo provisionally,
- responsive layout that keeps navigation usable on mobile.

The app should avoid a marketing-style homepage once a profile exists.

### First Components

Build these components first:

- `AppShell`
  - global layout, navigation, account area.
- `WelcomeScreen`
  - compact introduction and setup/login actions.
- `RecommendationList`
  - list wrapper, header message, playlist action, pagination/loading states.
- `RecommendationCard`
  - editorial text card with artist/album link, rating, tags, excerpt, and fit
    signal.
- `FilterSummaryBar`
  - compact current filter/preset state above results.
- `ProfileSetupShell`
  - guided setup frame with progress and summary, even if detailed selectors are
    initially mocked.
- `PlaylistGenerator`
  - settings step and generated output placeholder.
- `AuthDialog`
  - lightweight login/register shell.

### API Client

The frontend should have a small typed API client from the beginning.

Initial endpoints to wire:

- `GET /health`
- `GET /v1/presets`
- `GET /v1/taste-filter-ui`
- `POST /v1/recommendations/archive`
- `POST /v1/recommendations/new-reviews`
- `POST /v1/playlists/export`
- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `GET /v1/me`
- `GET /v1/me/taste-profile`
- `PUT /v1/me/taste-profile`

For the first visual shell, recommendation endpoints may be wrapped behind
fixtures or mocked responses if the local full corpus is not available. The API
client shape should still match the backend contracts.

### State Model

The frontend shell should explicitly model these user states:

- `anonymous_no_profile`,
- `anonymous_temporary_profile`,
- `authenticated_no_profile`,
- `authenticated_saved_profile`,
- `authenticated_unsaved_changes`.

This state model should drive routing, save prompts, and visible account actions.

Important rules:

- Temporary profile changes are safe and local until saved.
- Logged-in result filter changes do not overwrite the stored profile
  automatically.
- Registration after recommendations saves the current temporary profile and
  keeps the user in context.

### MVP Screens In Order

Implementation order:

1. App shell and routing.
2. Welcome screen.
3. Static/mocked `Aktuell` and `Entdecken` screens using the final card layout.
4. Typed API client for presets and filter UI metadata.
5. Recommendation cards connected to mocked or real API data.
6. Profile setup shell frame.
7. Playlist generator shell.
8. Auth dialog shell.

This order prioritizes product feel before deep interaction complexity.

### Explicit Non-Scope For First Shell

Do not build in the first shell:

- full parity with every Streamlit page,
- stored playlist history,
- recurring playlist email automation,
- account deletion implementation,
- password change implementation,
- full visual identity redesign,
- album-cover integration,
- production deployment changes.

These can follow once the shell proves the structure and feel.

### Acceptance Criteria

The first shell is good enough when:

- it starts locally with a documented command,
- navigation works across desktop and mobile widths,
- the visual direction feels light, editorial, and music-focused,
- recommendation cards are scannable without covers,
- the API client can fetch `/v1/presets` and `/v1/taste-filter-ui`,
- mocked or real recommendation data can render through the same card
  components,
- the distinction between no profile, temporary profile, and saved profile is
  visible in the UI model,
- linting and tests pass.

### Open Before Coding

Before starting implementation, decide:

- frontend folder name:
  - recommended: `frontend/`,
- package manager:
  - recommended: npm unless the project standardizes otherwise,
- UI library:
  - recommended: start with custom CSS and minimal dependencies,
- test setup:
  - recommended: Vitest + Testing Library once the first components exist.

## Feedbackrunde 1: Erste Frontend-Shell

Datum: 2026-06-25

Kontext:

- Die erste React/Vite-Shell wurde lokal mit Mock-Daten gebaut.
- Screenshots wurden mit Brave/Playwright geprüft.
- Feedback bezieht sich auf Startseite, Navigation, Musikprofil, `Aktuell`,
  `Entdecken`, Playlists und Login-Dialog.

### Gesamteindruck

User-Feedback:

- Der Entwurf sieht insgesamt gut und vielversprechend aus.
- Die Richtung ist grundsätzlich richtig, aber visuell teilweise etwas zu
  modern für die Zielgruppe.
- Die Zielgruppe ist eher musikaffin, links/alternativ und nicht
  Business- oder Tech-orientiert.
- Die Oberfläche soll professionell, angenehm und schön wirken, aber nicht zu
  glatt, steril oder zu sehr wie ein modernes SaaS-Produkt.

Codex-Einschätzung:

- Die Shell löst sich bereits deutlich vom Streamlit-Dashboard-Gefühl.
- Der Entwurf trifft die Richtung "Musikmagazin statt Data-Science-Tool".
- Die visuelle Sprache braucht noch mehr Wärme, Editorial-Charakter und etwas
  weniger moderne SaaS-Anmutung.
- Die erste Iteration ist eine gute Strukturprobe, aber noch kein fertiges
  visuelles System.

### Typografie Und Stil

User-Feedback:

- Die gewählte Schrift wirkt etwas zu modern für die Musikszene-Zielgruppe.
- Sehr große Überschriften wirken unruhig und teilweise unpassend.
- Der Kontrast zwischen kleinen Labels und sehr großen Headlines ist zu stark,
  besonders im Musikprofil-Setup.
- Die Überschriften auf `Aktuell`, `Entdecken` und `Playlists` sind zu groß.

Anforderung:

- Typografie soll editorial, musiknah und hochwertig wirken.
- Große Headlines sollen sparsamer eingesetzt werden.
- Inhaltsseiten brauchen kleinere, ruhigere Seitentitel.
- Labels und Headlines sollen harmonischer aufeinander abgestimmt werden.

### Startseite

User-Feedback:

- Die Startseite sieht gut aus.
- Der bestehende Text aus dem aktuellen Streamlit-Dashboard gefällt dem User
  sehr gut und sollte geprüft, übernommen oder mit dem neuen Einstieg
  kombiniert werden.
- Der aktuelle Startseitentext hat noch keine gute Überleitung zum
  Musikprofil.
- Es soll deutlicher werden, wie viel Plattenradar auf den Daten von
  plattentests.de aufbaut.
- Die Buttons `Musikprofil erstellen` und `Ich habe schon ein Profil` sind
  gut.
- Die rechte Box mit `Stile wählen`, `Profil schärfen`, `Alben entdecken`
  wirkt eher überflüssig.

Anforderung:

- Bestehenden Streamlit-Startseitentext analysieren.
- Startseite stärker auf Plattentests-Wertschätzung und Musikprofil-Einstieg
  zuschneiden.
- Rechte Prozessbox entfernen oder deutlich nützlicher machen.
- Startseite soll erklären, was Plattenradar macht, ohne wie eine
  Marketing-Landingpage zu wirken.

### Navigation

User-Feedback:

- Die Hauptnavigation `Aktuell`, `Entdecken`, `Playlists`, `Musikprofil`
  passt grundsätzlich.
- Die Leiste wirkt aktuell noch etwas klobig.
- Mobile Darstellung schneidet `Musikprofil` ab.

Codex-Einschätzung:

- Mobile Navigation braucht eine klare Lösung statt zufälligem Abschneiden.
- Die Navigation sollte leichter und weniger pillenartig wirken.
- Account/Login bleibt immer sichtbar oder schnell erreichbar.

Anforderung:

- Navigation visuell verschlanken.
- Mobile-Navigation gezielt gestalten.
- Labels beibehalten, aber Darstellung eleganter lösen.

### Musikprofil-Setup

User-Feedback:

- Beim Klick auf `Musikprofil erstellen` ist der kleine Labeltext
  `Musikprofil` neben der riesigen Headline nicht schön.
- `Welche groben Richtungen sollen ins Radar?` ist zu groß.
- `Beispielprofil verwenden` ist eine gute Idee, weil man schnell Ergebnisse
  sehen kann.
- Die rechte Infobox `Dein Profil noch nicht gespeichert ...` ist an dieser
  Stelle unklar und vermutlich nicht nötig.

User-Feedback (Wizard-Schritte 1–3, manueller Durchlauf):

- Schritt 1: Lange Richtungslabels (z. B. `Experimental & Avant-Garde`)
  umbrechen und machen Kacheln unterschiedlich hoch.
- Fortschrittsanzeige oben (`1 Richtungen`, `2 Details`, `3 Filter`) soll
  anklickbar sein und zu früheren Schritten zurückführen (nicht nur der
  `Zurück`-Button unten).
- `Beispielprofil verwenden` war unklar: Nutzer wusste nicht, dass der gesamte
  Wizard übersprungen wird und sofort Empfehlungen kommen.
- Schritt 2: Viele Detail-Kacheln sind anstrengend; Nutzer verliert nach
  einigen Minuten die Konzentration. Es braucht Entlastung (Hinweis, dass nicht
  alles ausgewählt werden muss) und sichtbaren Fortschritt (Anzahl gewählt).
- Schritt 2: Label und Beispiel-Künstler konkurrieren visuell; Künstlerzeile
  darf nicht umbrechen (sonst unterschiedliche Kachelhöhen). Wenn drei Namen
  zu lang sind, kürzere Kombination aus dem Künstler-Pool wählen statt nur die
  ersten zwei zu zeigen.
- Schritt 3 (`Treffsicher` etc.) und der Sprung zu den Empfehlungen wirken
  stimmig; Archivgröße (z. B. 3711 Alben) ist hilfreiche Rückmeldung.

Anforderung:

- Musikprofil-Setup ruhiger und weniger hero-artig gestalten.
- Kontextbox überarbeiten oder entfernen.
- Beispielprofil als schneller Demo-Pfad erhalten, aber klar als Schnelltest
  benennen und vor dem Sprung bestätigen.
- Fortschrittsleiste: Rücksprung zu abgeschlossenen Schritten per Klick.
- Schritt 1: Breitere Kacheln (z. B. zwei Spalten) und einheitliche
  Mindesthöhe.
- Schritt 2: Beruhigende Copy (`5–15 Stile reichen`), Zähler
  `X von Y ausgewählt`, einzeilige Künstlerbeispiele.
- Setup soll verständlich sein, aber nicht mit erklärenden Hinweisen
  überladen.

Offen / später prüfen:

- Detailauswahl weiter entlasten (Gruppierung nach Richtung, Suche, „Top
  Vorschläge“, Quick-Picks).
- Beispiel-Künstler ganz entfernen, wenn Label + Künstler weiterhin
  konkurrieren.
- Rechte Zusammenfassungsbox schlanker oder nur ab Schritt 2 sichtbar.

### Aktuell

User-Feedback:

- `Aktuell` soll nicht nur drei Empfehlungen zeigen.
- Es sollen grundsätzlich alle Rezensionen aus den letzten Updates angezeigt
  werden, sortiert nach Passung.
- Es braucht einen Filter, wie weit man in die Vergangenheit zurückgehen will,
  zum Beispiel die letzten X Update-Runden.
- Denkbar ist ein hervorgehobener Bereich mit besonderen Alben, etwa:
  - passendstes Album,
  - hoch bewertetes Album außerhalb des eigenen Musikprofils,
  - weiteres interessantes Album aus dem aktuellen Batch.
- Darunter soll die tatsächliche Rangliste folgen.
- Die aktuelle Intro-Copy wirkt noch nicht passend.

Anforderung:

- `Aktuell` als Update-orientierte Ergebnisliste konzipieren.
- Zeit-/Update-Filter vorsehen.
- Optionalen Highlight-Bereich über der Rangliste planen.
- Intro-Text dynamisch und batchbezogen denken.

### Entdecken / Archiv

User-Feedback:

- `Entdecken` bzw. Archiv soll anders funktionieren als `Aktuell`.
- Es gibt dort nicht zwingend drei hervorgehobene Alben.
- Man könnte aber auch im Archiv interessante Alben hervorheben, zum Beispiel:
  - besonders hohe Plattentests-Wertung,
  - besonders starke Genre-Passung,
  - besonders passendes Album.
- Die Richtung ist grundsätzlich gut, aber im Detail muss noch investiert
  werden.

Anforderung:

- Archiv-Erlebnis von `Aktuell` unterscheiden.
- Highlight-Logik im Archiv optional und anders begründen als bei neuen
  Rezensionen.
- Hauptfunktion bleibt die Rangliste aus dem Archiv.

### Empfehlungskarten

User-Feedback:

- Die Karten sehen grundsätzlich gut aus.
- Es fehlen noch Metadaten aus dem bestehenden Dashboard.
- Die Genre-Tags sind gut umgesetzt.
- Es fehlt noch die subtile Erklärung, warum ein Album passt.
- Der Scorewert fehlt noch und soll klein vertreten sein.
- Diese Seite ist eine der wichtigsten Seiten und braucht noch viel
  Detailarbeit.

Codex-Einschätzung:

- Karten sind bereits scannbar, aber noch zu generisch.
- Fit-Erklärung sollte visuell subtil bleiben, nicht textlastig.
- Score sollte vorhanden sein, aber sekundär.

Anforderung:

- Bestehende Streamlit-Empfehlungskarte analysieren.
- Fehlende Metadaten übernehmen, sofern fachlich relevant.
- Fit-Erklärung über Symbolik, Tag-Hervorhebung oder dezente Marker
  entwickeln.
- Score klein und nicht dominant anzeigen.

### Playlist-Bereich

User-Feedback:

- Die Playlist-Seite ist grundsätzlich nicht schlecht.
- Die Filter und Controls wirken aktuell zu klobig.
- Die Überschrift ist zu groß.
- Der Text nach der Generierung ist noch zu generisch.
- Es soll klarer erklärt werden, wie die Playlist in einen Streamingdienst
  importiert werden kann.
- Quelle `Entdecken` und `Aktuell` muss anders gelabelt werden:
  - eher `aus der Plattentests-Historie`,
  - oder `aus den letzten Update-Runden`.
- Für aktuelle Playlists muss einstellbar sein, wie weit man in die
  Vergangenheit zurückgehen will.
- `Anzahl Tracks` passt.
- `Fokus` soll abgestufter sein.
- `Variation` braucht eine bessere Erklärung und betrifft vermutlich vor allem
  Archiv-/Entdecken-Playlists.
- Playlist-Name mit `Plattenradar` und Datum passt grundsätzlich.
- Die finale Listenanzeige muss später separat geprüft werden.

Anforderung:

- Playlist-Controls eleganter und weniger formularhaft gestalten.
- Quellen semantisch umbenennen.
- Update-Zeitraum für aktuelle Playlists vorsehen.
- Fokus und Variation verständlicher machen.
- Nach Erzeugung klare Import-Hilfe für TuneMyMusic/Streamingdienst anzeigen.

### Login Und Account Dialog

User-Feedback:

- Klick auf `Ich habe schon ein Profil` öffnet einen Dialog mit falschem Text.
- Dort darf nicht `Profil speichern` stehen, sondern `Einloggen`.
- Schrift im Dialog ist zu groß.
- E-Mail- und Passwortfelder sehen schön aus.
- Nach Klick auf `Einloggen` erscheint ebenfalls fälschlich `Profil speichern`.

Anforderung:

- Auth-Dialog nach Kontext unterscheiden:
  - Login,
  - Profil speichern / registrieren.
- Dialog-Typografie verkleinern.
- Button- und Titeltexte korrigieren.
- Login-Pfad darf nicht wie Speichern wirken.

### Nächste Design-Aufgaben Aus Feedbackrunde 1

Priorität hoch:

1. Streamlit-Startseitentext und Empfehlungskarte analysieren.
2. Typografie insgesamt beruhigen.
3. Navigation verschlanken und Mobile-Darstellung lösen.
4. Login-Dialog-Kontext korrigieren.
5. Ergebnislisten-Konzept für `Aktuell` und `Entdecken` präzisieren.

Priorität mittel:

1. Playlist-Controls semantisch und visuell verbessern.
2. Fit-Erklärung und Score-Anzeige auf Karten entwerfen.
3. Startseiten-Prozessbox ersetzen oder entfernen.
4. Highlight-Logik für `Aktuell` und optional `Entdecken` spezifizieren.

Offene Fragen:

- Welche Schrift oder Schriftfamilie passt besser zur Zielgruppe?
- Soll `Aktuell` immer einen Highlight-Bereich haben oder nur bei klaren
  Treffern?
- Welche Metadaten aus der Streamlit-Karte sind wirklich Pflicht auf jeder
  Empfehlungskarte?
- Wie genau soll der Score benannt und skaliert werden?

## Feedbackrunde 2: Typografische Ruhe Und Funktionsschärfung

Datum: 2026-06-26

Kontext:

- Die überarbeitete Shell wurde erneut lokal geprüft.
- Dieses Feedback betrifft vor allem die typografische Hierarchie, die
  Konsistenz der UI-Texte und die noch zu konkretisierenden Ergebnis- und
  Playlist-Flows.

### Gesamteindruck

User-Feedback:

- Die Startseite mit ihrer Einstiegsfrage wirkt grundsätzlich gut und
  sympathisch.
- Die allgemeine Richtung der Shell stimmt; die Oberfläche soll jetzt ruhiger,
  eleganter und weniger aufdringlich werden.
- Das Feedback ist bewusst detailliert und ist für die weitere Gestaltung
  hilfreich, nicht zu kleinteilig.

### Typografische Leitentscheidung

Problem:

- Zu viele unterschiedliche Schriftgrößen, Schriften, Schriftschnitte und
  Farben lassen Startseite, Ergebnislisten, Musikprofil und Login unruhig
  wirken.
- Lange Überschriften werden aktuell zu groß dargestellt und brechen dadurch
  über zu viele Zeilen.
- Sehr fette Buttons wirken klobig.

Entscheidung:

- Eine ruhige UI-Schrift ist der Standard für Navigation, Texte, Formulare,
  Buttons und Metadaten.
- Eine editoriale Display-Schrift bleibt ausschließlich für ausgewählte
  Seitentitel und wird deutlich kleiner und zurückhaltender eingesetzt.
- Es gibt wenige, stabile Hierarchiestufen: Orientierungstext, Seitentitel,
  Fließtext, Metadaten. Zusätzliche Schriftwechsel und Farbakzente werden
  vermieden.
- Rot bleibt eine gezielte Akzentfarbe für Aktionen und aktive Zustände, nicht
  für jeden Orientierungstext.
- Buttons erhalten eine ruhigere Gewichtung und keine unnötig schwere
  Typografie.

### Startseite

User-Feedback:

- Die Einstiegsfrage funktioniert, ist in ihrer jetzigen Größe aber zu lang
  und zu dominant.
- `Willkommen bei Plattenradar`, die große Frage, Fließtext, hervorgehobener
  Brückensatz und Buttons wirken derzeit wie verschiedene visuelle Systeme.

Anforderung:

- Startseite als ruhige, redaktionelle Einleitung gestalten.
- Die Frage bleibt erhalten, wird aber als moderater Seitentitel statt als
  Hero-Headline behandelt.
- Der Brückensatz zum Musikprofil wird normaler Teil des Leseflusses; keine
  zusätzliche starke Farb- oder Font-Hierarchie.

### Aktuell Und Entdecken

User-Feedback:

- Die Vielfalt der Schriftstile stört auch auf Ergebnislisten.
- Die vorhandene Genre-Zuordnung ist ein guter Anfang, muss später aber noch
  verständlich erklärt werden.
- `Aktuell` braucht künftig einen kleinen, klar begründeten
  Hervorhebungsbereich vor der vollständigen Rangliste. Die Rangliste bleibt
  der Kern.

Anforderung:

- Ergebnisüberschriften und Metadaten typografisch beruhigen.
- Eine dezente Legende oder kontextnahe Erklärung für hervorgehobene
  Genre-Tags später als eigener Detail-Schritt konzipieren.
- Highlight-Bereich für neue Rezensionen vor der vollständigen API-Anbindung
  spezifizieren und erst dann mit echten Daten bauen.

### Playlist-Generator

User-Feedback:

- Die Grundstruktur passt, aber `Quelle`, `Aktuell` und `Entdecken` sind keine
  guten Nutzerbegriffe.
- Für neue Rezensionen soll ein Zeitraum wählbar sein.
- Variation gilt nur für Archiv-Playlists; bei aktuellen Rezensionen soll sie
  nicht erscheinen.

Anforderung:

- Quellen künftig als `Aus den letzten Updates` und `Aus dem
  Plattentests-Archiv` beschreiben.
- Zeitraum nur bei der Update-Quelle anbieten.
- Variation nur bei der Archiv-Quelle anbieten.

### Musikprofil Und Login

User-Feedback:

- `Welche groben Richtungen sollen ins Radar?` ist sprachlich und visuell noch
  nicht überzeugend.
- Musikprofil und Login profitieren ebenfalls von der ruhigeren Typografie.

Anforderung:

- Musikprofil-Setup als klare, persönliche Auswahl formulieren, ohne
  Radar-Metapher zu überdehnen.
- Login-Dialog beibehalten, aber typografisch an die restliche Oberfläche
  angleichen.

### Nächste Design-Aufgaben Aus Feedbackrunde 2

Priorität hoch:

1. Typografisches System in der Shell konsolidieren.
2. Startseite, Ergebnislisten, Playlist-Generator, Musikprofil und Login an
   dieses System anpassen.
3. Playlist-Quelle und kontextabhängige Controls verständlich machen.

Priorität danach:

1. Highlight-Konzept für `Aktuell` spezifizieren und mit echten Daten
   umsetzen.
2. Subtile, verständliche Erklärung für Genre-Hervorhebungen entwerfen.
3. Profil-Setup inhaltlich gegen die bestehende Schritt-1-bis-3-Logik prüfen.

### Prototyp: Highlight-Bereich Für Aktuell

Umgesetzt als bewusst vorläufiger UI-Vorschlag:

- Vor der vollständigen Rangliste stehen drei kleine, gleichwertige
  Redaktionsempfehlungen aus dem gewählten Update-Zeitraum.
- Die drei Blickwinkel sind `Beste Passung`, `Kritikerfavorit` und
  `Etwas außerhalb`.
- Jede Empfehlung enthält Albumlink, einen sehr kurzen Grund sowie
  Plattentests-Wertung und Score.
- Der Bereich ist keine alternative Rangliste und keine große
  Marketingbühne; darunter folgt klar abgegrenzt die vollständige Liste.
- Die Shell erhält Highlights als eigene Datenstruktur. Später soll der
  Backend-Endpunkt Auswahlgrund und Empfehlung gemeinsam liefern.

Offenes Feedback für die nächste Runde:

- Sind drei Highlights die richtige Anzahl oder reichen zwei?
- Fühlen sich die Auswahlgründe sinnvoll und musiknah an?
- Soll der Bereich stärker oder noch zurückhaltender gegenüber der Rangliste
  sein?
- Erst nach dieser inhaltlichen Entscheidung werden Farben, Abstände und
  eventuelle Icons final verfeinert.

### Feedback Zum Highlight-Bereich

User-Entscheidungen:

- Der Bereich erscheint bei jedem Update. Die beste Passung ist immer ein
  sinnvoller Anker.
- Es gibt zwei oder drei Highlights, aber keine leeren Kategorien: Nur
  Auswahlgründe mit einem tatsächlich interessanten Album erscheinen.
- `Beste Passung` und `Kritikerfavorit` sind verständlich.
- `Etwas außerhalb` ist inhaltlich sinnvoll, muss aber klarer machen, dass es
  sich etwa um ein hoch bewertetes Album außerhalb des aktuellen Musikprofils
  handeln kann. Der Begriff wird deshalb zu `Außerhalb deines Profils`
  präzisiert.
- Die beste Passung darf visuell etwas stärker erscheinen als ergänzende
  Fundstücke. Das Layout soll dadurch lebendiger werden, aber einer ruhigen,
  nachvollziehbaren Ordnung folgen.
- Zusätzlich erhält `Aktuell` eine dynamische Update-Zusammenfassung: Wie
  ergiebig war der gewählte Zeitraum für dieses Musikprofil und was ist daran
  bemerkenswert?

Technische Konsequenz:

- Der spätere API-Endpunkt für aktuelle Empfehlungen liefert neben der
  Rangliste eine optionale Liste von zwei bis drei Highlights sowie einen
  persönlichen Update-Überblick.

### Feedback Zur Zweiten Highlight-Variante

User-Feedback:

- Die große Karte für die beste Passung erzeugt zu viel leeren Raum und wirkt
  nicht überzeugend.
- Der individuelle Update-Überblick ist nicht klar genug als persönlicher
  Text erkennbar; er wirkt in die anderen Bedienelemente eingewurschtelt.
- Der Auftakt nimmt auf großen Bildschirmen so viel Höhe ein, dass die
  Rangliste im ersten sichtbaren Bereich nicht mehr erkennbar ist. Das darf
  nicht passieren, weil die Rangliste der Kern der Seite bleibt.

Codex-Einschätzung Nach Screenshot-Prüfung:

- Die Kritik trifft zu: Der aktuelle Ablauf hat zu viele vertikale Ebenen vor
  der Rangliste.
- Die Hauptkarte wächst durch das zweizeilige Grid stärker als durch ihren
  Inhalt; das ist keine sinnvolle Betonung.
- Nächster Entwurf: ein kompakter, deutlich abgegrenzter persönlicher
  Update-Hinweis und eine einzeilige Highlight-Reihe. Die beste Passung darf
  etwas breiter und farblich zurückhaltend akzentuiert sein, aber nicht höher
  als die anderen Highlights. Dadurch bleibt der Beginn der Rangliste im
  ersten Desktop-Ausschnitt sichtbar.

Umsetzung der verdichteten Variante:

- Der Update-Hinweis ist als kompakte, farblich zurückhaltende Zweispaltenbox
  aufgebaut: links die persönliche Einschätzung, rechts ihre kurze
  Begründung.
- Die Highlights stehen auf Desktop in einer einzelnen Reihe; die beste
  Passung ist etwas breiter statt höher.
- Die zusätzliche große Highlight-Überschrift wurde zu `Aus dem neuen
  Schwung` verdichtet.
- Der obere Seitenabstand und die Abstände zwischen Abschnitten wurden
  reduziert, damit Highlights und der Beginn der Rangliste gleichzeitig
  sichtbar sind.
- Nach der ersten Umsetzung wurde die Reihenfolge weiter verdichtet: Der
  Überblick ist strukturell eine echte Zeile statt versehentlich zweier Zeilen,
  und die sichtbare Highlight-Überschrift entfällt zugunsten der Karten selbst.
- Zeitraum und aktuelle Filter erscheinen in einer gemeinsamen,
  nutzerorientierten Ergebnisleiste. Ein technischer Shell-Hinweis über
  zukünftige Update-Daten wird nicht in der Oberfläche gezeigt.

Weiteres Feedback und Anpassung:

- Der persönliche Überblick und die Highlights sollen als zusammenhängender
  Empfehlungsbereich wahrnehmbar sein, nicht als mehrere gestapelte Boxen.
- Die neue Umsetzung verwendet deshalb eine äußere, zurückhaltende Fläche mit
  einer persönlichen Einordnung oben und drei durch feine Linien getrennten
  redaktionellen Empfehlungen darunter.
- Zwischen Steuerleiste, persönlicher Auswahl und Rangliste wird bewusst mehr
  Weißraum gelassen.

Letzte Verfeinerung:

- Der vertikale Abstand zwischen Ergebnissteuerung, persönlicher Auswahl und
  Rangliste wird deutlich erhöht. Die drei Ebenen sollen separat atmen können,
  ohne den zusammenhängenden Charakter der persönlichen Auswahl aufzulösen.

## Erster Echter Frontend-Durchstich

Datum: 2026-06-26

Umgesetzt:

- `GET /v1/taste-communities` liefert dem Frontend auswählbare Community-IDs
  mit lesbaren Genre-Labels.
- Das Musikprofil lädt diese Optionen aus der API und kann daraus ein
  temporäres, ausgewogenes Geschmacksprofil bauen.
- Nach Abschluss lädt `Entdecken` echte Archivempfehlungen über
  `POST /v1/recommendations/archive`; die Mock-Liste wird dort nicht mehr
  verwendet.
- Empfehlungskarten werden aus dem API-Vertrag gemappt und behalten Artist,
  Album, Plattentests-Wertung, Score, Label, Textauszug, Rezension-Link und
  passende Style-Tags.
- Lade-, Leer- und Fehlerzustände sind als echte Seitenzustände vorgesehen.

Bewusste Zwischenstufe:

- Der vollständige, bestehende Schritt-1-bis-3-Geschmackswizard ist noch nicht
  migriert. Die aktuelle Auswahl bindet nur Stil-Communities und die
  ausgewogenen Standardfilter an, damit der Kernflow bereits real funktioniert.
- Die nächste große fachliche Aufgabe ist die vollständige Übernahme dieser
  Schrittfolge einschließlich Feinwahl, Stilgewichtung und semantischer
  Filtermodi.

## Streamlit-Audit Nach Feedbackrunde 1

Datum: 2026-06-25

Geprüfte Dateien:

- `streamlit_app.py`
- `pages/6_Recommendations_Flow.py`
- `pages/8_Neueste_Rezensionen.py`
- `pages/9_Playlist_Erzeugen.py`
- `pages/playlist_section.py`
- `pages/page_formatting.py`
- `pages/page_css.py`

### Startseite Aus Dem Streamlit-Prototyp

Starker bestehender Textkern:

> plattentests.de rezensiert seit 1999 Alben aus allen Ecken der Musikwelt.
> Wie viele davon würden dir gefallen, wenn du sie nur kennen würdest?

Warum dieser Text wichtig ist:

- Er erklärt sofort die Datenbasis.
- Er macht die Archiv-Idee emotional verständlich.
- Er positioniert Plattenradar als Ergänzung zu plattentests.de.
- Er spricht Musikfans an, ohne technisch zu klingen.

Übernahme in die neue Shell:

- Der Startseitentext soll diesen Gedanken übernehmen.
- Der Claim `Der schnellste Weg zu Alben, die zu dir passen` bleibt als
  Produktgefühl hilfreich, soll aber nicht allein den Start tragen.
- Die neue Startseite braucht eine bessere Überleitung:
  - erst Datenkosmos und Nutzen,
  - dann Musikprofil als erster sinnvoller Schritt,
  - daneben Login für wiederkehrende Nutzer.

### Streamlit-Empfehlungskarte

Aktuelle Pflichtinformationen im Prototyp:

- Rang,
- Künstler und Album als Link zur plattentests.de-Rezension,
- Release-Jahr oder Release-Datum,
- plattentests.de-Rating,
- Score,
- Plattenlabel, wenn vorhanden,
- Stil-/Genre-Tags,
- stärkere Markierung bei Tags, die zum Nutzerprofil passen,
- Textauszug aus der Rezension.

Wichtige Design-Erkenntnis:

- Die neue Karte darf kompakter und schöner sein, soll aber diese
  Informationsdichte nicht verlieren.
- `Score` soll klein und sekundär sichtbar sein.
- Die Erklärung der Passung soll primär über die Stil-Tags erfolgen:
  - passende Tags leicht hervorgehoben,
  - Tag-Stärke über dezente Farbabstufung,
  - kleine Legende oder Tooltip statt langer Erklärung.

### Aktuell Im Streamlit-Prototyp

Aktueller Stand:

- `Neueste Rezensionen` zeigt eine wählbare Anzahl zuletzt rezensierter Alben.
- Diese werden nach Profil-Passung sortiert, sofern ein Profil vorhanden ist.
- Es gibt eine Score-Verteilung als Plotly-Chart.

Übertragung in neues Frontend:

- In v1 soll `Aktuell` nicht als Liste von drei Highlights verstanden werden.
- Es ist eine sortierte Ergebnisliste über einen wählbaren aktuellen Pool.
- Der Pool soll später besser als Update-Zeitraum oder Update-Runden modelliert
  werden.
- Ein Highlight-Bereich über der Rangliste ist optional, aber fachlich sinnvoll,
  wenn er klar begründet ist.

### Playlist Im Streamlit-Prototyp

Aktueller Stand:

- Es gibt zwei Quellen:
  - neueste Rezensionen,
  - gesamtes Archiv.
- Für neueste Rezensionen wird aktuell die Anzahl der letzten Rezensionen als
  Pool gewählt.
- Nach Generierung werden Tabelle, TXT-Export, CSV-Export und eine
  TuneMyMusic-Anleitung angezeigt.

Übertragung in neues Frontend:

- Quellen sollen nutzerfreundlicher benannt werden:
  - `Aus den letzten Updates`,
  - `Aus dem Plattentests-Archiv`.
- Der spätere Update-Zeitraum gehört in die Playlist-Quelle `Aktuell`.
- Die TuneMyMusic-Anleitung ist wichtig und muss nach der Generierung sichtbar
  werden.
- TXT und CSV sind keine Vorab-Einstellung, sondern zwei Exportoptionen nach
  der Generierung.

### Erste Umsetzungsentscheidungen Für Shell-Iteration 2

Direkt umsetzen:

- Startseitentext stärker aus dem Streamlit-Prototyp übernehmen.
- Rechte Prozessbox auf der Startseite entfernen.
- Headlines und Seitenhierarchie verkleinern.
- Navigation leichter gestalten und mobile Darstellung reparieren.
- Login-Dialog zwischen `Einloggen` und `Profil speichern` unterscheiden.
- Empfehlungskarten um Score und Plattenlabel erweitern.
- Tags für passende Stilrichtungen visuell subtil hervorheben.

Noch nicht umsetzen:

- echten Update-Batch aus Daten ableiten,
- echte Highlight-Logik berechnen,
- echten Streamlit-Filter vollständig übertragen,
- Chart für Score-Verteilung übernehmen,
- echte Playlist-Erzeugung im Frontend anschließen,
- Album-Favoriten speichern und Favoriten-basierte Playlists (siehe
  `docs/plattenradar-v1-product-api.md`, Abschnitt **Album-Favoriten (Zukunft)**).
