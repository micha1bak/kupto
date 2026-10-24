import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { usePurchaseHistory, useProductSearch } from "../api/queries";
import type { PurchasedItem, ShoppingTrip } from "../api/types";
import { formatQuantities, formatQuantity, formatTime } from "../list/format";
import { formatDay, formatDayTime } from "./format";
import styles from "./HistoryPage.module.css";

/** Opóźnienie wyszukiwania po ostatnim naciśnięciu klawisza. */
export const SEARCH_DEBOUNCE_MS = 300;

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Brak połączenia z serwerem.";
}

/** „1 pozycja”, „3 pozycje”, „5 pozycji”, „22 pozycje”, „12 pozycji”. */
export function itemCount(n: number): string {
  const few = n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14);
  return `${n} ${n === 1 ? "pozycja" : few ? "pozycje" : "pozycji"}`;
}

function useDebounced(value: string, delay: number): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function ItemRow({ item }: { item: PurchasedItem }) {
  const quantity = formatQuantities(item.quantities);
  return (
    <li className={styles.item}>
      <div className={styles.itemHead}>
        <span className={styles.itemName}>{item.name}</span>
        {quantity && <span className={styles.quantity}>{quantity}</span>}
      </div>
      <div className={styles.meta}>
        kupił(a) {item.bought_by ?? "—"} o {formatTime(item.bought_at)}
        {item.needs.length > 0 && (
          <>
            {" · zgłaszali: "}
            {item.needs
              .map((n) => {
                const details = [formatQuantity(n.amount, n.unit), n.note && `„${n.note}”`]
                  .filter(Boolean)
                  .join(", ");
                return details ? `${n.name ?? "—"} (${details})` : (n.name ?? "—");
              })
              .join(", ")}
          </>
        )}
      </div>
    </li>
  );
}

function TripSection({ trip }: { trip: ShoppingTrip }) {
  const headingId = `trip-${trip.id}`;
  return (
    <section className={`card ${styles.trip}`} aria-labelledby={headingId}>
      <h3 id={headingId} className={styles.tripHeading}>
        {formatDayTime(trip.finished_at)}
      </h3>
      <p className={styles.meta}>
        zakończył(a) {trip.finished_by ?? "—"} · {itemCount(trip.item_count)}
      </p>
      {trip.groups.map((group) => (
        <div key={group.category} className={styles.group}>
          <h4 className={styles.category}>{group.category}</h4>
          <ul className={styles.items}>
            {group.items.map((item) => (
              <ItemRow key={item.id} item={item} />
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

function Trips() {
  const history = usePurchaseHistory();

  if (history.isPending) return <p className="muted">Ładowanie…</p>;
  // Błąd doczytania starszej strony nie chowa już wczytanych zakończeń.
  if (!history.data) return <p className="error">{errorMessage(history.error)}</p>;
  const trips = history.data.pages.flatMap((page) => page.trips);
  if (trips.length === 0) {
    return <p className="muted">Nie ma jeszcze zakończonych zakupów.</p>;
  }
  return (
    <>
      {trips.map((trip) => (
        <TripSection key={trip.id} trip={trip} />
      ))}
      {history.isFetchNextPageError && (
        <p className="error">{errorMessage(history.error)}</p>
      )}
      {history.hasNextPage && (
        <button onClick={() => history.fetchNextPage()} disabled={history.isFetchingNextPage}>
          {history.isFetchingNextPage ? "Ładowanie…" : "Pokaż więcej"}
        </button>
      )}
    </>
  );
}

function SearchResults({ phrase }: { phrase: string }) {
  const search = useProductSearch(phrase);

  if (search.isPending) return <p className="muted">Szukam…</p>;
  if (search.isError) return <p className="error">{errorMessage(search.error)}</p>;
  if (search.data.length === 0) {
    return <p className="muted">Nikt jeszcze nie kupował „{phrase}”.</p>;
  }
  return (
    <ul className={`card ${styles.items}`} aria-label="Wyniki wyszukiwania">
      {search.data.map((hit) => {
        const quantity = formatQuantities(hit.last_quantities);
        return (
          <li key={hit.name} className={styles.item}>
            <div className={styles.itemHead}>
              <span className={styles.itemName}>{hit.name}</span>
              <span className={styles.quantity}>{hit.category}</span>
            </div>
            <div className={styles.meta}>
              ostatnio {formatDay(hit.last_bought_at)}, kupił(a) {hit.last_bought_by ?? "—"}
              {quantity && ` (${quantity})`} · razem {hit.times_bought}×
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function HistoryPage() {
  const [query, setQuery] = useState("");
  const phrase = useDebounced(query.trim(), SEARCH_DEBOUNCE_MS);

  return (
    <main className={styles.page}>
      <Link to="/">← Wróć do listy</Link>
      <h2 className={styles.title}>Historia zakupów</h2>
      <input
        type="search"
        aria-label="Szukaj produktu w historii"
        placeholder="Kiedy ostatnio kupowaliśmy…?"
        value={query}
        maxLength={100}
        onChange={(e) => setQuery(e.target.value)}
      />
      {phrase ? <SearchResults phrase={phrase} /> : <Trips />}
    </main>
  );
}
