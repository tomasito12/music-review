"""Registry of Hub destination cards (extend by appending entries)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HubDestination:
    """One navigable goal from the post-setup Hub page."""

    title: str
    description: str
    page_path: str


# Central list: add new rows here to surface more destinations in the Hub UI.
HUB_DESTINATIONS: tuple[HubDestination, ...] = (
    HubDestination(
        title="Neueste passende Alben",
        description=(
            "Frische Rezensionen aus dem Corpus, sortiert danach, "
            "wie gut sie zu deinen Stil-Schwerpunkten passen."
        ),
        page_path="pages/8_Neueste_Rezensionen.py",
    ),
    HubDestination(
        title="Musikpräferenzen ändern",
        description=(
            "Grobe Stilrichtungen, feine Auswahl und Filter erneut einstellen "
            "(Schritt 1 bis 3)."
        ),
        page_path="pages/0b_Einstieg.py",
    ),
    HubDestination(
        title="Gesamtes Archiv durchsuchen",
        description=(
            "Empfehlungen über alle Alben im lokalen Bestand "
            "mit deinen Filtern und Gewichtungen."
        ),
        page_path="pages/6_Recommendations_Flow.py",
    ),
    HubDestination(
        title="Spotify-Playlist",
        description=(
            "Neue Musik, die zu dir passt, in eine eigene Playlist übernehmen."
        ),
        page_path="pages/9_Spotify_Playlists.py",
    ),
    HubDestination(
        title="Einstellungen speichern",
        description=(
            "Anmelden, damit Filter und Stile mit deinem Nutzerkonto "
            "gespeichert werden. Ein neues Konto legst du über "
            "»Konto anlegen« in der Seitenleiste an."
        ),
        page_path="pages/0c_Anmelden.py",
    ),
)


def hub_destinations() -> tuple[HubDestination, ...]:
    """Return Hub cards in display order."""
    return HUB_DESTINATIONS
