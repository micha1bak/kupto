import type { Quantity } from "../api/types";

const number = new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 3 });

export function formatQuantity(amount: number | null, unit: string | null): string {
  if (amount === null) return "";
  return unit ? `${number.format(amount)} ${unit}` : number.format(amount);
}

export function formatQuantities(quantities: Quantity[]): string {
  return quantities.map((q) => formatQuantity(q.amount, q.unit)).join(" + ");
}

const time = new Intl.DateTimeFormat("pl-PL", { hour: "2-digit", minute: "2-digit" });

/** Godzina (HH:MM, czas lokalny) z daty ISO. */
export function formatTime(iso: string): string {
  return time.format(new Date(iso));
}
