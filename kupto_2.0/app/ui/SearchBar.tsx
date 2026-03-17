'use client'

import React from 'react';

export default function SearchBar() {
  return (
    <div className="w-full max-w-2xl mx-auto px-4 mt-6">
      <div className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-zinc-400 group-focus-within:text-indigo-500 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-5 h-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 1 0 10.607 10.607Z" />
          </svg>
        </div>
        <input
          type="text"
          className="block w-full rounded-2xl border-0 py-4 pl-12 pr-4 text-zinc-900 dark:text-white shadow-xl shadow-zinc-200/50 dark:shadow-none ring-1 ring-inset ring-zinc-200 dark:ring-zinc-800 placeholder:text-zinc-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:focus:ring-indigo-500 sm:text-sm bg-white dark:bg-zinc-900 transition-all"
          placeholder="Szukaj lub dodaj produkt..."
        />
        <div className="absolute inset-y-0 right-3 flex items-center">
            <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-2 text-[10px] font-medium text-zinc-400">
                <span>Ctrl</span>K
            </kbd>
        </div>
      </div>
    </div>
  );
}
