import type { Quantity } from "../api/types";

const number = new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 3 });

export function formatQuantity(amount: number | null, unit: string | null): string {
  if (amount === null) return "";
  return unit ? `${number.format(amount)} ${unit}` : number.format(amount);
}

export function formatQuantities(quantities: Quantity[]): string {
  return quantities.map((q) => formatQuantity(q.amount, q.unit)).join(" + ");
}
