// Dni planu to daty kalendarzowe `YYYY-MM-DD` w czasie lokalnym — bez `toISOString()`, które
// przelicza na UTC i np. tuż po północy dawałoby poprzedni dzień.

const WEEKDAYS = ["niedziela", "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota"];
const MONTHS = [
  "sty",
  "lut",
  "mar",
  "kwi",
  "maj",
  "cze",
  "lip",
  "sie",
  "wrz",
  "paź",
  "lis",
  "gru",
];

/** Data lokalna jako `YYYY-MM-DD`. */
export function toDay(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** `YYYY-MM-DD` jako lokalna północ tego dnia. */
export function parseDay(day: string): Date {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(year, month - 1, date);
}

/** Dzień przesunięty o `days` (także ujemnie); odporne na zmianę czasu letniego. */
export function addDays(day: string, days: number): string {
  const date = parseDay(day);
  date.setDate(date.getDate() + days);
  return toDay(date);
}

/** Poniedziałek tygodnia, do którego należy dzień. */
export function mondayOf(day: string): string {
  return addDays(day, -((parseDay(day).getDay() + 6) % 7));
}

/** Nazwa dnia tygodnia, np. „wtorek”. */
export function weekdayName(day: string): string {
  return WEEKDAYS[parseDay(day).getDay()];
}

/** Krótka data, np. „27 paź”. */
export function shortDate(day: string): string {
  const date = parseDay(day);
  return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
}

/** Zakres tygodnia od poniedziałku, np. „26 paź – 1 lis”. */
export function weekLabel(monday: string): string {
  return `${shortDate(monday)} – ${shortDate(addDays(monday, 6))}`;
}
