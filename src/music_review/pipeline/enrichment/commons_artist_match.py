"""Strict artist-name matching for Wikimedia Commons image candidates."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any

_MATCH_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")

_HOMONYM_PREFIX_STOPWORDS = frozenset(
    {
        "album",
        "band",
        "concert",
        "cover",
        "disc",
        "festival",
        "file",
        "image",
        "jpeg",
        "jpg",
        "live",
        "photo",
        "picture",
        "png",
        "portrait",
        "press",
        "single",
        "svg",
        "tour",
        "wiki",
        "org",
        "https",
        "http",
        "www",
        "upload",
        "wikipedia",
        "wikimedia",
        "commons",
    }
)


def normalize_artist_match_text(value: str) -> str:
    """Normalize text for conservative artist-name matching."""
    return _MATCH_NORMALIZE_RE.sub(" ", value.casefold()).strip()


def artist_name_variants(artist_name: str) -> set[str]:
    """Return normalized artist-name phrases that count as a match."""
    base = normalize_artist_match_text(artist_name)
    if not base:
        return set()

    variants = {base}
    without_the = _strip_leading_the(base)
    if without_the:
        variants.add(without_the)
        variants.add(f"the {without_the}")
    return {variant for variant in variants if variant}


def artist_name_in_text(artist_name: str, text: str) -> bool:
    """Return whether the artist name appears as a whole phrase in text."""
    variants = artist_name_variants(artist_name)
    haystack = normalize_artist_match_text(text)
    if not variants or not haystack:
        return False

    base = normalize_artist_match_text(artist_name)
    base_tokens = _strip_leading_the(base).split()
    if len(base_tokens) == 1:
        return _single_token_phrase_matches(base_tokens[0], haystack, variants)

    substantive = _substantive_tokens(base)
    for variant in variants:
        pattern = r"\b" + re.escape(variant).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, haystack) and not _multi_word_suffix_collision(
            substantive,
            haystack,
            variants,
        ):
            return True
    return False


def build_commons_context_text(
    commons_title: str,
    imageinfo: dict[str, Any] | None = None,
) -> str:
    """Build searchable text from a Commons file title and metadata."""
    parts = [_filename_from_commons_title(commons_title)]
    if imageinfo is None:
        return " ".join(parts)

    metadata = imageinfo.get("extmetadata")
    if not isinstance(metadata, dict):
        return " ".join(parts)

    for key in ("ObjectName", "ImageDescription", "Artist", "Credit", "Categories"):
        value = _metadata_value(metadata, key)
        if value is not None:
            parts.append(_strip_html(value))
    return " ".join(parts)


def commons_image_matches_artist(
    artist_name: str,
    commons_title: str,
    imageinfo: dict[str, Any] | None = None,
) -> bool:
    """Return whether one Commons file plausibly depicts the requested artist."""
    if _is_short_single_word_name(artist_name) and not _short_name_filename_match(
        artist_name,
        commons_title,
    ):
        return False

    context = build_commons_context_text(commons_title, imageinfo)
    return artist_name_in_text(artist_name, context)


def cached_commons_image_matches_artist(
    artist_name: str,
    *,
    commons_file: str | None,
    title: str | None = None,
    attribution_text: str | None = None,
    source_url: str | None = None,
) -> bool:
    """Return whether a cached Commons image still matches the artist name."""
    if (
        commons_file
        and _is_short_single_word_name(artist_name)
        and not _short_name_filename_match(artist_name, f"File:{commons_file}")
    ):
        return False

    primary_parts = [
        _matchable_context_text(part)
        for part in (commons_file, title)
        if part and part.strip()
    ]
    if primary_parts:
        return any(artist_name_in_text(artist_name, part) for part in primary_parts)

    fallback_parts = [
        _matchable_context_text(part)
        for part in (attribution_text, source_url)
        if part and part.strip()
    ]
    if not fallback_parts:
        return True
    return any(artist_name_in_text(artist_name, part) for part in fallback_parts)


def record_matches_artist_name(
    artist_name: str,
    *,
    commons_file: str | None,
    attribution_text: str | None = None,
    source_url: str | None = None,
) -> bool:
    """Return whether one resolved image record matches the expected artist name."""
    expected = artist_name.strip()
    if not expected:
        return True
    return cached_commons_image_matches_artist(
        expected,
        commons_file=commons_file,
        attribution_text=attribution_text,
        source_url=source_url,
    )


_LATIN_FOLD_MAP = str.maketrans(
    {
        "\u0131": "i",  # Turkish dotless i
        "\u0130": "i",  # Turkish dotted I
        "\u00ef": "i",  # i diaeresis
        "\u00f6": "o",
        "\u00fc": "u",
        "\u00e4": "a",
        "\u00e5": "a",
        "\u00e6": "ae",
        "\u00f8": "o",
        "\u00df": "ss",
        "\u0142": "l",
        "\u00f1": "n",
        "\u00e7": "c",
    },
)


def normalize_musicbrainz_name(value: str) -> str:
    """Normalize artist names for conservative MusicBrainz equivalence checks."""
    text = value.casefold().translate(_LATIN_FOLD_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    for source, target in (
        ("\u2019", "'"),
        ("\u2018", "'"),
        ("\u2010", "-"),
        ("\u2011", "-"),
        ("\u2012", "-"),
        ("\u2013", "-"),
        ("\u2014", "-"),
        ("&", " and "),
        ("+", " and "),
        ("/", " and "),
    ):
        text = text.replace(source, target)
    return _MATCH_NORMALIZE_RE.sub(" ", text).strip()


def _musicbrainz_core_tokens(normalized_name: str) -> str:
    """Drop connector stopwords so ``and``/``&`` spellings compare equal."""
    tokens = [
        token
        for token in normalized_name.split()
        if token not in _SUBSTANTIVE_STOPWORDS
    ]
    return " ".join(tokens)


def _musicbrainz_name_equivalence_variants(normalized_name: str) -> set[str]:
    """Return normalized MusicBrainz name phrases that should count as equivalent."""
    if not normalized_name:
        return set()

    variants = {normalized_name, _musicbrainz_core_tokens(normalized_name)}
    without_the = _strip_leading_the(normalized_name)
    if without_the:
        variants.add(without_the)
        variants.add(f"the {without_the}")
        variants.add(_musicbrainz_core_tokens(without_the))
    return {variant for variant in variants if variant}


def musicbrainz_name_matches_requested(requested_name: str, resolved_name: str) -> bool:
    """Return whether a MusicBrainz artist name fits the requested lookup name."""
    requested = normalize_musicbrainz_name(requested_name)
    resolved = normalize_musicbrainz_name(resolved_name)
    if not requested or not resolved:
        return False

    requested_variants = _musicbrainz_name_equivalence_variants(requested)
    resolved_variants = _musicbrainz_name_equivalence_variants(resolved)
    if requested_variants.intersection(resolved_variants):
        return True

    # Commons-style phrase checks catch alias-like inclusions without suffix
    # collisions that fire on the artist's own multi-word name.
    return artist_name_in_text(requested_name, resolved_name) or artist_name_in_text(
        resolved_name,
        requested_name,
    )


_SHORT_ARTIST_NAME_MAX_LEN = 4
_SUBSTANTIVE_STOPWORDS = frozenset({"a", "an", "and", "at", "of", "the", "&"})


def _single_token_phrase_matches(
    token: str,
    haystack: str,
    variants: set[str],
) -> bool:
    """Match one-word artist names without accepting longer homonyms."""
    longer_homonym = rf"\b(?:the\s+)?(?:\w+\s+){{1,3}}{re.escape(token)}\b"
    for match in re.finditer(longer_homonym, haystack):
        if _is_longer_homonym_phrase(match.group(0), token, variants):
            return False

    standalone_pattern = rf"\b(?:the\s+)?{re.escape(token)}\b"
    for match in re.finditer(standalone_pattern, haystack):
        phrase = normalize_artist_match_text(match.group(0))
        if phrase in variants:
            return True
        without_the = _strip_leading_the(phrase)
        if without_the in variants:
            return True
    return False


def _is_longer_homonym_phrase(phrase: str, token: str, variants: set[str]) -> bool:
    """Return whether one matched phrase is a longer artist-name homonym."""
    normalized = normalize_artist_match_text(phrase)
    if normalized in variants:
        return False

    without_the = _strip_leading_the(normalized)
    if without_the in variants:
        return False

    words = without_the.split()
    if len(words) <= 1 or words[-1] != token:
        return False

    prefix_words = [
        word for word in words[:-1] if word not in _HOMONYM_PREFIX_STOPWORDS
    ]
    return len(prefix_words) > 0


def _is_short_single_word_name(artist_name: str) -> bool:
    """Return whether an artist name is a very short single-word name."""
    token = _strip_leading_the(normalize_artist_match_text(artist_name))
    parts = token.split()
    return len(parts) == 1 and len(parts[0]) <= _SHORT_ARTIST_NAME_MAX_LEN


def _short_name_filename_match(artist_name: str, commons_title: str) -> bool:
    """Require short artist names to lead the Commons filename."""
    token = _strip_leading_the(normalize_artist_match_text(artist_name))
    filename = normalize_artist_match_text(_filename_from_commons_title(commons_title))
    if not token or not filename:
        return False
    if filename in {token, f"the {token}"}:
        return True
    return filename.startswith(f"{token} ") or filename.startswith(f"the {token} ")


def _substantive_tokens(phrase: str) -> list[str]:
    """Return meaningful tokens from one normalized artist phrase."""
    return [
        token
        for token in _strip_leading_the(phrase).split()
        if token not in _SUBSTANTIVE_STOPWORDS and len(token) > 2
    ]


def _ordered_substantive_tokens_in_text(tokens: list[str], haystack: str) -> bool:
    """Return whether all substantive tokens appear in order in the text."""
    position = 0
    for token in tokens:
        match = re.search(rf"\b{re.escape(token)}\b", haystack[position:])
        if match is None:
            return False
        position += match.end()
    return True


def _multi_word_suffix_collision(
    substantive_tokens: list[str],
    haystack: str,
    variants: set[str],
) -> bool:
    """Return whether the text contains a conflicting band name with a shared suffix."""
    if len(substantive_tokens) < 2:
        return False

    suffix = substantive_tokens[-1]
    pattern = rf"\b(?:the\s+)?(?:\w+\s+){{1,3}}{re.escape(suffix)}\b"
    for match in re.finditer(pattern, haystack):
        phrase = _strip_leading_the(normalize_artist_match_text(match.group(0)))
        words = phrase.split()
        if any(any(char.isdigit() for char in word) for word in words):
            continue
        if phrase in variants:
            continue
        if f"the {phrase}" in variants:
            continue
        if _ordered_substantive_tokens_in_text(substantive_tokens, phrase):
            continue
        if phrase.endswith(f" {suffix}") or phrase == suffix:
            return True
    return False


def _strip_leading_the(text: str) -> str:
    return re.sub(r"^the\s+", "", text.strip())


def _matchable_context_text(value: str) -> str:
    """Reduce URLs and boilerplate to text useful for artist-name matching."""
    text = value.strip()
    if "commons.wikimedia.org/wiki/File:" in text:
        text = text.rsplit("File:", maxsplit=1)[-1]
    elif "upload.wikimedia.org/" in text:
        text = text.rsplit("/", maxsplit=1)[-1]
    return text.replace("_", " ")


def _filename_from_commons_title(commons_title: str) -> str:
    if commons_title.lower().startswith("file:"):
        return commons_title[5:].replace("_", " ")
    return commons_title.replace("_", " ")


def _metadata_value(metadata: dict[str, Any], key: str) -> str | None:
    raw = metadata.get(key)
    if not isinstance(raw, dict):
        return None
    value = raw.get("value")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value)
    return html.unescape(without_tags).strip()
