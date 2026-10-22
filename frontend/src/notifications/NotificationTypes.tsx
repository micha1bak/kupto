import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, put } from "../api/client";
import { keys, useNotificationPreferences } from "../api/queries";
import type { NotificationPreferences, NotificationType } from "../api/types";
import styles from "./NotificationTypes.module.css";

const LABELS: Record<NotificationType, { label: string; description: string }> = {
  shopping_started: {
    label: "Ktoś idzie na zakupy",
    description: "Domownik włączył „Idę na zakupy” — możesz dopisać, czego potrzebujesz.",
  },
  items_added: {
    label: "Dopisano w trakcie zakupów",
    description: "Gdy robisz zakupy, a ktoś dopisze produkt do listy.",
  },
  shopping_finished: {
    label: "Zakupy zakończone",
    description: "Domownik zakończył zakupy — z listą tego, czego nie było.",
  },
};

const isKnown = (type: string): type is NotificationType => type in LABELS;

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Nie udało się zapisać ustawienia. Spróbuj ponownie.";
}

interface Change {
  type: NotificationType;
  enabled: boolean;
}

/**
 * Włączanie i wyłączanie poszczególnych typów powiadomień (spec: notifications — ustawienia
 * typów). Ustawienia są per użytkownik, więc obowiązują na wszystkich jego urządzeniach.
 */
export function NotificationTypes() {
  const queryClient = useQueryClient();
  const preferences = useNotificationPreferences();
  const change = useMutation({
    mutationFn: ({ type, enabled }: Change) =>
      put<NotificationPreferences>(`/api/push/preferences/${type}`, { enabled }),
    onMutate: async ({ type, enabled }: Change) => {
      await queryClient.cancelQueries({ queryKey: keys.notificationPreferences });
      const previous = queryClient.getQueryData<NotificationPreferences>(
        keys.notificationPreferences,
      );
      if (previous) {
        queryClient.setQueryData<NotificationPreferences>(keys.notificationPreferences, {
          types: previous.types.map((t) => (t.type === type ? { ...t, enabled } : t)),
        });
      }
      return { previous };
    },
    onError: (_error, _change, context) => {
      if (context?.previous) {
        queryClient.setQueryData(keys.notificationPreferences, context.previous);
      }
    },
    onSuccess: (data) => queryClient.setQueryData(keys.notificationPreferences, data),
  });

  if (preferences.isError) {
    return <p className="error">Nie udało się wczytać ustawień powiadomień.</p>;
  }
  if (!preferences.data) return <p className="muted">Ładowanie ustawień…</p>;

  return (
    <fieldset className={styles.types}>
      <legend>Powiadamiaj mnie, gdy…</legend>
      <p className={`muted ${styles.hint}`}>
        Te ustawienia obowiązują na wszystkich Twoich urządzeniach.
      </p>
      {preferences.data.types.map(({ type, enabled }) => {
        if (!isKnown(type)) return null;
        const { label, description } = LABELS[type];
        return (
          <label key={type} className={styles.type}>
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => change.mutate({ type, enabled: e.target.checked })}
            />
            <span>
              {label}
              <span className={`muted ${styles.description}`}>{description}</span>
            </span>
          </label>
        );
      })}
      {change.error && <p className="error">{errorMessage(change.error)}</p>}
    </fieldset>
  );
}
