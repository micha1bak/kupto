import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import { useListEvents } from "./listEvents";
import type { ChatMessage, Household, Profile, ShoppingList } from "./types";

export const keys = {
  profile: ["profile"] as const,
  household: ["household"] as const,
  list: ["list"] as const,
  chat: ["chat"] as const,
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

// Historię odświeżamy tylko jawnie po każdej wymianie (ChatView), nie np. przy powrocie do karty —
// inaczej wiadomości z bieżącej wymiany pojawiałyby się podwójnie (lokalnie i z serwera).
export const useChatHistory = () =>
  useQuery({
    queryKey: keys.chat,
    queryFn: () => api<ChatMessage[]>("/api/chat/messages"),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
