'use client'

import React from 'react';

export default function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Lewa strona - opcjonalne miejsce na menu lub powrót */}
        <div className="flex-1 hidden sm:flex">
            {/* Można tu dodać np. datę lub status połączenia */}
        </div>

        {/* Centrum - LOGO */}
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-md shadow-indigo-500/20">
            <span className="text-white text-lg font-black italic leading-none">K</span>
          </div>
          <span className="text-xl font-black tracking-tight text-zinc-900 dark:text-white">
            Kupto <span className="text-indigo-600 dark:text-indigo-500">2.0</span>
          </span>
        </div>

        {/* Prawa strona - Profil / Wyloguj */}
        <div className="flex-1 flex justify-end items-center gap-4">
          <div className="flex flex-col items-end hidden xs:block">
            <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 leading-none">Michał</span>
            <span className="text-[10px] text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Użytkownik</span>
          </div>
          <button className="h-9 w-9 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-600 dark:text-zinc-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}
