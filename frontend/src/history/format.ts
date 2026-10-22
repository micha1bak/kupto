const dayTime = new Intl.DateTimeFormat("pl-PL", {
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const day = new Intl.DateTimeFormat("pl-PL", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

/** Data z godziną po polsku (czas lokalny), np. „śr., 21 paź 2026, 18:30”. */
export function formatDayTime(iso: string): string {
  return dayTime.format(new Date(iso));
}

/** Sama data po polsku (czas lokalny), np. „21 paź 2026”. */
export function formatDay(iso: string): string {
  return day.format(new Date(iso));
}
