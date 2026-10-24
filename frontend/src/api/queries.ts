import { useCallback } from "react";
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import { useListEvents } from "./listEvents";
import type {
  ChatMessage,
  Household,
  HouseholdPreferences,
  MealPlanEntry,
  NotificationPreferences,
  ProductHit,
  Profile,
  Recipe,
  RecipeSummary,
  ShoppingList,
  TripPage,
  UsualProduct,
} from "./types";

export const keys = {
  profile: ["profile"] as const,
  household: ["household"] as const,
  list: ["list"] as const,
  chat: ["chat"] as const,
  history: ["history"] as const,
  historySearch: ["history-search"] as const,
  usual: ["usual"] as const,
  notificationPreferences: ["notification-preferences"] as const,
  recipes: ["recipes"] as const,
  householdPreferences: ["household-preferences"] as const,
  mealPlan: ["meal-plan"] as const,
};

/**
 * Co ile odpytujemy o listę, gdy strumień zmian na żywo nie działa (spec: ≤ 30 s).
 * Przy działającym strumieniu listę pobieramy tylko po sygnale zmiany.
 */
export const LIST_FALLBACK_POLL_MS = 30_000;

export const useProfile = () =>
  useQuery({ queryKey: keys.profile, queryFn: () => api<Profile>("/api/users/me") });

export const useHousehold = () =>
  useQuery({ queryKey: keys.household, queryFn: () => api<Household>("/api/households/me") });

/** Preferencje żywieniowe gospodarstwa (wspólne dla domowników). */
export const useHouseholdPreferences = () =>
  useQuery({
    queryKey: keys.householdPreferences,
    queryFn: () => api<HouseholdPreferences>("/api/households/me/preferences"),
  });

export function useShoppingList() {
  const queryClient = useQueryClient();
  const live = useListEvents(
    useCallback(() => queryClient.invalidateQueries({ queryKey: keys.list }), [queryClient]),
  );
  return useQuery({
    queryKey: keys.list,
    queryFn: () => api<ShoppingList>("/api/list"),
    refetchInterval: live ? false : LIST_FALLBACK_POLL_MS,
    // Powrót do karty obsługuje strumień zmian (odświeża listę i łączy się ponownie).
    refetchOnWindowFocus: false,
  });
}

/** Zakończenia zakupów od najnowszych; kolejne strony doczytywane kursorem `next_cursor`. */
export const usePurchaseHistory = () =>
  useInfiniteQuery({
    queryKey: keys.history,
    queryFn: ({ pageParam }) =>
      api<TripPage>(pageParam === null ? "/api/history" : `/api/history?before=${pageParam}`),
    initialPageParam: null as number | null,
    getNextPageParam: (last) => last.next_cursor,
  });

/** Kiedy i kto ostatnio kupił produkty pasujące do frazy; pusta fraza — brak zapytania. */
export const useProductSearch = (phrase: string) =>
  useQuery({
    queryKey: [...keys.historySearch, phrase],
    queryFn: () =>
      api<ProductHit[]>(`/api/history/products?q=${encodeURIComponent(phrase)}`),
    enabled: phrase !== "",
  });

/** Produkty kupowane zwykle, których brakuje na liście (podpowiedź „Zwykle kupujecie”). */
export const useUsualProducts = () =>
  useQuery({
    queryKey: keys.usual,
    queryFn: () => api<UsualProduct[]>("/api/history/usual"),
    staleTime: 5 * 60_000,
  });

/** Które typy powiadomień użytkownik chce dostawać (per użytkownik, nie per urządzenie). */
export const useNotificationPreferences = () =>
  useQuery({
    queryKey: keys.notificationPreferences,
    queryFn: () => api<NotificationPreferences>("/api/push/preferences"),
  });

// Wątek czatu gospodarstwa odświeżamy tylko jawnie: po każdej wymianie i na sygnał `chat_changed`
// ze strumienia zmian (ChatView), nie np. przy powrocie do karty — inaczej wiadomości z bieżącej
// wymiany pojawiałyby się podwójnie (lokalnie i z serwera).
export const useChatHistory = () =>
  useQuery({
    queryKey: keys.chat,
    queryFn: () => api<ChatMessage[]>("/api/chat/messages"),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

/** Przepisy gospodarstwa alfabetycznie. */
export const useRecipes = () =>
  useQuery({ queryKey: keys.recipes, queryFn: () => api<RecipeSummary[]>("/api/recipes") });

/** Zapisany przepis ze składnikami; klucz pod `keys.recipes`, więc odświeża się razem z listą. */
export const useRecipe = (id: number) =>
  useQuery({
    queryKey: [...keys.recipes, id],
    queryFn: () => api<Recipe>(`/api/recipes/${id}`),
  });

/** Obiady z zakresu dat `YYYY-MM-DD` (włącznie) rosnąco po dniu; dni bez obiadu pominięte. */
export const useMealPlan = (from: string, to: string) =>
  useQuery({
    queryKey: [...keys.mealPlan, from, to],
    queryFn: () => api<MealPlanEntry[]>(`/api/meal-plan?from=${from}&to=${to}`),
  });
