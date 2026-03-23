import SearchBar from "@/app/ui/SearchBar";
import ShoppingList from "@/app/ui/ShoppingList";
import { getShoppingList } from "@/app/actions/shopping-list";

export default async function Home() {
  const initialData = await getShoppingList();

  return (
      <main className="container mx-auto max-w-2xl relative">
        {/* Wyszukiwarka produktów */}
        <SearchBar />

        {/* Lista zakupów podzielona na kategorie */}
        <ShoppingList initialData={initialData} />
      </main>
  );
}
