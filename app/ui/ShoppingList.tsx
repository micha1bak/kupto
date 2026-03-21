'use client'

import React from 'react';
import ListItem from './ListItem';
import { ShoppingListCategoryGroup } from '@/app/actions/shopping-list';

interface ShoppingListProps {
  initialData: ShoppingListCategoryGroup[];
}

export default function ShoppingList({ initialData }: ShoppingListProps) {
  return (
    <div className="w-full max-w-2xl mx-auto px-4 pt-6 pb-32">
      {initialData.length === 0 && (
        <div className="text-center py-20">
          <p className="text-zinc-400 dark:text-zinc-500 italic">Twoja lista jest pusta. Dodaj produkty za pomocą wyszukiwarki!</p>
        </div>
      )}
      
      {initialData.map((group) => (
        <section key={group.category} className="mb-8 last:mb-0">
          {/* Nagłówek kategorii */}
          <div className="flex items-center gap-2 mb-4 sticky top-16 bg-zinc-50/80 dark:bg-black/80 backdrop-blur-sm py-2 z-10">
            <h2 className="text-xs font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
              {group.category}
            </h2>
            <div className="h-[1px] flex-1 bg-zinc-200 dark:bg-zinc-800"></div>
            <span className="text-[10px] font-bold text-zinc-400 bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full">
              {group.items.length}
            </span>
          </div>

          {/* Lista przedmiotów w kategorii */}
          <div className="space-y-1">
            {group.items.map((item) => (
              <ListItem 
                key={item.id}
                name={item.name}
                quantity={item.quantity || ''}
              />
            ))}
          </div>
        </section>
      ))}
      
      {initialData.length > 0 && (
        /* Pusta sekcja na końcu dla lepszego wrażenia wizualnego */
        <div className="text-center py-10 opacity-20 grayscale">
           <p className="text-sm font-medium">To już wszystkie produkty!</p>
        </div>
      )}
    </div>
  );
}
