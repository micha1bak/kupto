'use client'

import React from 'react';

// Przykładowe dane szablonów
const MOCK_TEMPLATES = [
  { id: 1, name: 'Cotygodniowe zakupy', itemsCount: 24, icon: '🛒' },
  { id: 2, name: 'Dieta Siłownia', itemsCount: 12, icon: '💪' },
  { id: 3, name: 'Impreza / Grill', itemsCount: 15, icon: '🔥' },
  { id: 4, name: 'Środki czystości', itemsCount: 8, icon: '🧼' },
];

export default function UserProfile() {
  return (
    <div className="w-full max-w-2xl mx-auto px-4 py-8 pb-32">
      {/* SEKCJA PROFILU */}
      <div className="flex flex-col items-center mb-12">
        <div className="relative group">
          <div className="h-24 w-24 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-500 p-1 shadow-xl group-hover:scale-105 transition-transform duration-300">
            <div className="h-full w-full rounded-full bg-white dark:bg-zinc-900 flex items-center justify-center overflow-hidden border-4 border-white dark:border-zinc-900">
              {/* Placeholder zdjęcia profilowego */}
              <span className="text-3xl font-black text-indigo-600 dark:text-indigo-400">MB</span>
            </div>
          </div>
          <button className="absolute bottom-0 right-0 h-8 w-8 rounded-full bg-indigo-600 border-4 border-white dark:border-zinc-950 flex items-center justify-center text-white shadow-lg hover:bg-indigo-500 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="m2.695 14.762-1.262 3.155a.5.5 0 0 0 .642.642l3.155-1.262a2 2 0 0 0 .851-.544l11.103-11.103a2.5 2.5 0 0 0-3.535-3.535L2.695 11.221a2 2 0 0 0-.544.851Z" />
            </svg>
          </button>
        </div>
        
        <h2 className="mt-4 text-2xl font-black text-zinc-900 dark:text-white tracking-tight">Michał Bąk</h2>
        <p className="text-zinc-500 dark:text-zinc-400 font-medium">@michal_bak</p>
        
        <div className="mt-6 flex gap-4">
            <div className="px-4 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-xl text-center">
                <span className="block text-lg font-bold text-zinc-900 dark:text-white">128</span>
                <span className="text-[10px] uppercase tracking-widest text-zinc-500">Zakupów</span>
            </div>
            <div className="px-4 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-xl text-center">
                <span className="block text-lg font-bold text-zinc-900 dark:text-white">4</span>
                <span className="text-[10px] uppercase tracking-widest text-zinc-500">Szablony</span>
            </div>
        </div>
      </div>

      {/* SEKCJA SZABLONÓW */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
            <h3 className="text-sm font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
                Twoje Szablony
            </h3>
            <button className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline">
                Dodaj nowy +
            </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {MOCK_TEMPLATES.map((template) => (
            <button 
              key={template.id}
              className="flex items-center gap-4 p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 shadow-sm hover:shadow-md hover:border-indigo-200 dark:hover:border-indigo-900/40 transition-all text-left group"
            >
              <div className="h-12 w-12 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                {template.icon}
              </div>
              <div>
                <span className="block font-bold text-zinc-900 dark:text-white leading-tight">
                    {template.name}
                </span>
                <span className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">
                    {template.itemsCount} produktów
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* PRZYCISK WYLOGUJ */}
      <div className="mt-12">
          <button className="w-full py-4 rounded-2xl border-2 border-red-100 dark:border-red-900/20 text-red-500 font-bold hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors">
              Wyloguj się
          </button>
      </div>
    </div>
  );
}
