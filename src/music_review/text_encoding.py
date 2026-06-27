"""Repair plattentests.de text that was decoded as ISO-8859-1 instead of CP1252."""

from __future__ import annotations

# Windows-1252 bytes 0x80-0x9F map to C1 controls in ISO-8859-1. Plattentests
# declares ISO-8859-1 but uses CP1252 punctuation in that range (en dash, etc.).
_CP1252_REPLACEMENTS: dict[int, str] = {
    0x80: "\u20ac",
    0x82: "\u201a",
    0x83: "\u0192",
    0x84: "\u201e",
    0x85: "\u2026",
    0x86: "\u2020",
    0x87: "\u2021",
    0x88: "\u02c6",
    0x89: "\u2030",
    0x8A: "\u0161",
    0x8B: "\u2039",
    0x8C: "\u0152",
    0x8E: "\u017d",
    0x91: "\u2018",
    0x92: "\u2019",
    0x93: "\u201c",
    0x94: "\u201d",
    0x95: "\u2022",
    0x96: "\u2013",
    0x97: "\u2014",
    0x98: "\u02dc",
    0x99: "\u2122",
    0x9A: "\u0161",
    0x9B: "\u203a",
    0x9C: "\u0153",
    0x9E: "\u017e",
    0x9F: "\u0178",
}


def repair_plattentests_text(text: str) -> str:
    """Replace ISO-8859-1 C1 controls with their Windows-1252 characters."""
    if not text:
        return text
    if not any(0x80 <= ord(char) <= 0x9F for char in text):
        return text
    return "".join(_CP1252_REPLACEMENTS.get(ord(char), char) for char in text)
