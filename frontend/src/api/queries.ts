import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { ChatMessage, Household, Profile, ShoppingList } from "./types";

export const keys = {
  profile: ["profile"] as const,
  household: ["household"] as const,
  list: ["list"] as const,
  chat: ["chat"] as const,
};

/** Co ile odświeżamy listę, by zmiany innych domowników były widoczne (spec: ≤ 10 s). */
export const LIST_POLL_MS = 5000;

export const useProfile = () =>
  useQuery({ queryKey: keys.profile, queryFn: () => api<Profile>("/api/users/me") });

export const useHousehold = () =>
  useQuery({ queryKey: keys.household, queryFn: () => api<Household>("/api/households/me") });

export const useShoppingList = () =>
  useQuery({
    queryKey: keys.list,
    queryFn: () => api<ShoppingList>("/api/list"),
    refetchInterval: LIST_POLL_MS,
  });

// Historię odświeżamy tylko jawnie po każdej wymianie (ChatView), nie np. przy powrocie do karty —
// inaczej wiadomości z bieżącej wymiany pojawiałyby się podwójnie (lokalnie i z serwera).
export const useChatHistory = () =>
  useQuery({
    queryKey: keys.chat,
    queryFn: () => api<ChatMessage[]>("/api/chat/messages"),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
