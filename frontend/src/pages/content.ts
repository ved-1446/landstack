// Plain-words text shared by the landing page, "How it works" and "About". Written for a 10-year-old.
// The points are the real ones from backend/app/config.py (POINTS); the page never changes them, it only explains them.

export interface Step {
  key: "map" | "compare" | "count" | "passport";
  title: string;
  short: string;
  long: string;
}

export const STEPS: Step[] = [
  {
    key: "map",
    title: "Draw the plot on a map",
    short: "Every plot is a shape on a map, with an id like MH000100000006.",
    long: "Think of a big colouring book of land. Every plot is one shape in it, and every shape has its own id, like a name tag. LandStack keeps the shape (where the plot is) and its papers (who owns it, how big it is, whether tax was paid).",
  },
  {
    key: "compare",
    title: "Compare the papers",
    short: "Nine fixed checks look for things that do not match.",
    long: "The shape on the map and the papers should tell the same story. Do two plots overlap? Does the paper say 1,000 square metres but the map says 1,500? Is the owner's name different in two papers? Nine checks ask questions like these, always the same way.",
  },
  {
    key: "count",
    title: "Count the problems",
    short: "Each problem adds points. More points means more risk.",
    long: "Each problem found adds some points, like a score in a game, but here a low score is good. Add them up (never more than 100) and you get the risk score. Only code does this adding. An AI never changes a score.",
  },
  {
    key: "passport",
    title: "Get a passport you can check",
    short: "A one-page land passport, with a code that proves it is genuine.",
    long: "Every plot gets a one-page land passport: the score, the problems found and the proof for each. It has a QR code and a document id. Anyone can type that id on the Verify page to see whether the records still match what was printed.",
  },
];

export interface Check {
  name: string;
  points: number;
  plain: string;
  simulated?: boolean;
}

export const CHECKS: Check[] = [
  { name: "Boundary overlap", points: 40, plain: "Two plots cannot sit on the same piece of ground. This finds plots that overlap, or sit inside each other." },
  { name: "Restricted zone clash", points: 30, plain: "Some land, like a flood plain or a river edge, is not for building. This finds plots that lie too much inside such a zone." },
  { name: "Area mismatch", points: 25, plain: "The paper says how big the plot is. If the map shape is much bigger or smaller, something is wrong." },
  { name: "Owner mismatch", points: 25, plain: "The land record and the registration should name the same owner. If the names are very different, this flags it." },
  { name: "Duplicate survey number", points: 20, plain: "A survey number is like a house number. Two plots in the same village should not share one." },
  { name: "Invalid boundary", points: 15, plain: "A plot's outline must be a proper closed shape. If the lines cross themselves, the outline is broken." },
  { name: "Tax overdue", points: 15, plain: "If the land tax has not been paid for more than two years, this flags it." },
  { name: "Missing record", points: 10, plain: "Each plot should have a land record, a registration and a tax record. This finds a plot with one missing." },
  { name: "Unrecorded construction", points: 15, plain: "Compares two pretend surveys and spots a new building that is not in the records. This part is simulated.", simulated: true },
];

export interface Band {
  key: "green" | "amber" | "red";
  range: string;
  name: string;
  plain: string;
}

export const BANDS: Band[] = [
  { key: "green", range: "0 to 24", name: "Low risk", plain: "Nothing, or almost nothing, to worry about." },
  { key: "amber", range: "25 to 59", name: "Watch", plain: "Something does not match. A person should look." },
  { key: "red", range: "60 and up", name: "High risk", plain: "Serious problems. Check this plot before anyone buys, sells or builds." },
];

export const ROLES = [
  { key: "citizen", area: "MY LAND", title: "Citizen", text: "See only your own plots, a plain-words story of each one, and what to do next." },
  { key: "officer", area: "OFFICER WORK DESK", title: "Officer", text: "A priority list of risky plots, charts, a map of everything and every finding with its proof." },
  { key: "admin", area: "CONTROL ROOM", title: "Admin", text: "Everything an officer sees, plus who looked at what, the people with access, and system health." },
] as const;
