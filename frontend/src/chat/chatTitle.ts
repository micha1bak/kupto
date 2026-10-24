import type { Profile } from "../api/types";

/**
 * Tytuł czatu w pasku nawigacji i w opcjach czatu (spec: app-navigation).
 * Czat jest grupowy (#78): gospodarstwo „Dom” = czat „Dom”, więc tytułem jest nazwa gospodarstwa.
 */
export function chatTitle(profile: Profile): string {
  return profile.household?.name || "Czat";
}
