import Header from "@/app/ui/Header";
import SearchBar from "@/app/ui/SearchBar";
import ShoppingList from "@/app/ui/ShoppingList";
import NavBar from "@/app/ui/NavBar";
import { getShoppingList } from "@/app/actions/shopping-list";

export default async function Home() {
  const initialData = await getShoppingList();

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black font-sans selection:bg-indigo-100 selection:text-indigo-900">
      {/* Nagłówek strony */}
      <Header />

      <main className="container mx-auto max-w-2xl relative">
        {/* Wyszukiwarka produktów */}
        <SearchBar />

        {/* Lista zakupów podzielona na kategorie */}
        <ShoppingList initialData={initialData} />
      </main>

      {/* Nawigacja dolna (Pływająca) */}
      <NavBar />
    </div>
  );
}
