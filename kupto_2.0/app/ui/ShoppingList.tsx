'use client'

import React from 'react';
import ListItem from './ListItem';

// Przykładowe dane zainspirowane strukturą v1.0
const MOCK_DATA = [
  {
    category: 'Warzywa i owoce',
    items: [
      { id: 1, name: 'Pomidory malinowe', quantity: 4, unit: 'szt.' },
      { id: 2, name: 'Banan', quantity: 2, unit: 'kg' },
      { id: 3, name: 'Szczypiorek', quantity: 1, unit: 'pęczek' },
    ]
  },
  {
    category: 'Nabiał',
    items: [
      { id: 4, name: 'Mleko 3.2%', quantity: 2, unit: 'l' },
      { id: 5, name: 'Ser żółty Gouda', quantity: 200, unit: 'g' },
      { id: 6, name: 'Jogurt naturalny', quantity: 3, unit: 'szt.' },
    ]
  },
  {
    category: 'Pieczywo',
    items: [
      { id: 7, name: 'Chleb żytni', quantity: 1, unit: 'szt.' },
      { id: 8, name: 'Bułki grahamki', quantity: 6, unit: 'szt.' },
    ]
  },
  {
    category: 'Inne',
    items: [
      { id: 9, name: 'Papier toaletowy', quantity: 1, unit: 'opak.' },
      { id: 10, name: 'Baterie AA', quantity: 4, unit: 'szt.' },
    ]
  }
];

export default function ShoppingList() {
  return (
    <div className="w-full max-w-2xl mx-auto px-4 pt-6 pb-32">
      {MOCK_DATA.map((group) => (
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
                quantity={item.quantity}
                unit={item.unit}
              />
            ))}
          </div>
        </section>
      ))}
      
      {/* Pusta sekcja na końcu dla lepszego wrażenia wizualnego */}
      <div className="text-center py-10 opacity-20 grayscale">
         <p className="text-sm font-medium">To już wszystkie produkty!</p>
      </div>
    </div>
  );
}
