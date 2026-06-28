/** Repair plattentests.de text decoded as ISO-8859-1 instead of Windows-1252. */
const CP1252_REPLACEMENTS: Readonly<Record<number, string>> = {
  0x80: "\u20ac",
  0x82: "\u201a",
  0x83: "\u0192",
  0x84: "\u201e",
  0x85: "\u2026",
  0x86: "\u2020",
  0x87: "\u2021",
  0x88: "\u02c6",
  0x89: "\u2030",
  0x8a: "\u0161",
  0x8b: "\u2039",
  0x8c: "\u0152",
  0x8e: "\u017d",
  0x91: "\u2018",
  0x92: "\u2019",
  0x93: "\u201c",
  0x94: "\u201d",
  0x95: "\u2022",
  0x96: "\u2013",
  0x97: "\u2014",
  0x98: "\u02dc",
  0x99: "\u2122",
  0x9a: "\u0161",
  0x9b: "\u203a",
  0x9c: "\u0153",
  0x9e: "\u017e",
  0x9f: "\u0178",
};

/** Replace ISO-8859-1 C1 controls with their Windows-1252 characters. */
export function repairPlattentestsText(text: string): string {
  if (text.length === 0) {
    return text;
  }

  let needsRepair = false;
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index);
    if (code >= 0x80 && code <= 0x9f) {
      needsRepair = true;
      break;
    }
  }
  if (!needsRepair) {
    return text;
  }

  let repaired = "";
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index);
    repaired += CP1252_REPLACEMENTS[code] ?? text[index] ?? "";
  }
  return repaired;
}
