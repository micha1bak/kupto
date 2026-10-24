import type { Profile } from "../api/types";

/**
 * Tytuł czatu w pasku nawigacji i w opcjach czatu (spec: app-navigation).
 * Na razie nazwa gospodarstwa; po czacie grupowym (#78) — nazwa czatu grupowego.
 */
export function chatTitle(profile: Profile): string {
  return profile.household?.name || "Czat";
}
