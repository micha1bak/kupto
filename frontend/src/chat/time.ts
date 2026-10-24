/**
 * Godzina wiadomości czatu w strefie przeglądarki (#78): „18:05” dla dzisiejszych,
 * „23.10, 18:05” dla starszych. `null` dla nieprawidłowej daty.
 */
export function formatMessageTime(iso: string, now: Date = new Date()): string | null {
  const date = new Date(iso);
  if (!iso || Number.isNaN(date.getTime())) return null;
  const time = date.toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" });
  if (date.toDateString() === now.toDateString()) return time;
  const day = `${date.getDate()}.${String(date.getMonth() + 1).padStart(2, "0")}`;
  return `${day}, ${time}`;
}
