import type {
  Recommendation,
  RecommendationHighlight,
  UpdateSummary,
} from "../types";

export const aktuellRecommendations: Recommendation[] = [
  {
    rank: 1,
    artist: "The Notwist",
    album: "Vertigo Days",
    year: 2021,
    releaseDate: "2021-01-29",
    rating: 8,
    score: 0.88,
    fitLabel: "Sehr passend",
    fitPercent: 88,
    recordLabel: "Morr Music",
    excerpt:
      "Ein Album, das zwischen Indie, Elektronik und leiser Melancholie genau den Raum findet, in dem kleine Details lange nachhallen ...",
    reviewUrl: "https://www.plattentests.de/rezi.php?show=17491",
    tags: [
      { label: "Indie", affinity: 0.72, matchesProfile: true },
      { label: "Elektronik", affinity: 0.41, matchesProfile: true },
      { label: "Melancholisch", affinity: 0.18, matchesProfile: false },
    ],
    source: "aktuell",
  },
  {
    rank: 2,
    artist: "Big Thief",
    album: "Dragon New Warm Mountain I Believe In You",
    year: 2022,
    releaseDate: "2022-02-11",
    rating: 8,
    score: 0.82,
    fitLabel: "Passend",
    fitPercent: 82,
    recordLabel: "4AD",
    excerpt:
      "Die Band klingt hier gleichzeitig lose, konzentriert und so nahbar, dass viele Songs wie zufällige Funde aus einem sehr guten Notizbuch wirken ...",
    reviewUrl: "https://www.plattentests.de/rezi.php?show=18120",
    tags: [
      { label: "Indie Folk", affinity: 0.68, matchesProfile: true },
      { label: "Songwriter", affinity: 0.36, matchesProfile: false },
      { label: "Warm", affinity: 0.14, matchesProfile: false },
    ],
    source: "aktuell",
  },
  {
    rank: 3,
    artist: "Japanese Breakfast",
    album: "Jubilee",
    year: 2021,
    releaseDate: "2021-06-04",
    rating: 7,
    score: 0.74,
    fitLabel: "Interessanter Randbereich",
    fitPercent: 74,
    recordLabel: "Dead Oceans",
    excerpt:
      "Heller, größer und poppiger als erwartet, aber unter der Oberfläche bleibt genug Unruhe, um nicht glatt zu werden ...",
    reviewUrl: "https://www.plattentests.de/rezi.php?show=17627",
    tags: [
      { label: "Indie Pop", affinity: 0.44, matchesProfile: true },
      { label: "Dream Pop", affinity: 0.31, matchesProfile: false },
      { label: "Leuchtend", affinity: 0.12, matchesProfile: false },
    ],
    source: "aktuell",
  },
];

export const entdeckenRecommendations: Recommendation[] = [
  {
    rank: 1,
    artist: "Broken Social Scene",
    album: "You Forgot It In People",
    year: 2002,
    releaseDate: "2002-08-27",
    rating: 9,
    score: 0.91,
    fitLabel: "Sehr passend",
    fitPercent: 91,
    recordLabel: "City Slang",
    excerpt:
      "Ein vielstimmiger Indie-Kosmos, der sich ständig verzweigt und trotzdem erstaunlich organisch zusammenhält ...",
    reviewUrl: "https://www.plattentests.de/rezi.php?show=1294",
    tags: [
      { label: "Indie Rock", affinity: 0.81, matchesProfile: true },
      { label: "Post-Rock", affinity: 0.39, matchesProfile: true },
      { label: "Vielschichtig", affinity: 0.22, matchesProfile: false },
    ],
    source: "entdecken",
  },
  {
    rank: 2,
    artist: "Sufjan Stevens",
    album: "Illinois",
    year: 2005,
    rating: 9,
    score: 0.9,
    fitLabel: "Sehr passend",
    fitPercent: 90,
    recordLabel: "Rough Trade",
    excerpt:
      "Zwischen Kammerpop, Folk und überbordender Detailfreude entsteht ein Album, das sich wie eine ganze kleine Welt anfühlt ...",
    reviewUrl: "https://www.plattentests.de/rezi.php?show=3146",
    tags: [
      { label: "Chamber Pop", affinity: 0.77, matchesProfile: true },
      { label: "Folk", affinity: 0.42, matchesProfile: true },
      { label: "Erzählerisch", affinity: 0.16, matchesProfile: false },
    ],
    source: "entdecken",
  },
  {
    rank: 3,
    artist: "The Dismemberment Plan",
    album: "Emergency & I",
    year: 1999,
    rating: 8,
    score: 0.84,
    fitLabel: "Passend",
    fitPercent: 84,
    recordLabel: "DeSoto",
    excerpt:
      "Nervös, rhythmisch, verkopft und trotzdem direkt: genau die Art Platte, die im Archiv leicht verschüttet wird ...",
    reviewUrl: "https://www.plattentests.de/rezi.php?show=694",
    tags: [
      { label: "Post-Hardcore", affinity: 0.63, matchesProfile: false },
      { label: "Indie Rock", affinity: 0.37, matchesProfile: true },
      { label: "Nervös", affinity: 0.11, matchesProfile: false },
    ],
    source: "entdecken",
  },
];

export const aktuellHighlights: RecommendationHighlight[] = [
  {
    label: "Beste Passung",
    description: "Die stärkste Verbindung zu deinem aktuellen Musikprofil.",
    recommendation: aktuellRecommendations[0],
  },
  {
    label: "Kritikerfavorit",
    description: "Besonders hoch bewertet und ein guter Einstieg in diesen Update-Schwung.",
    recommendation: aktuellRecommendations[1],
  },
  {
    label: "Außerhalb deines Profils",
    description:
      "Hoch bewertet, auch wenn es deinen aktuellen Vorlieben weniger nahe ist.",
    recommendation: aktuellRecommendations[2],
  },
];

export const aktuellSummary: UpdateSummary = {
  title: "Ein kleiner, aber lohnender Update-Schwung.",
  description:
    "Drei der neuen Rezensionen passen besonders gut zu deinem Musikprofil. Eine davon liegt etwas außerhalb und könnte gerade deshalb spannend sein.",
};
