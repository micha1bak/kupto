'use client'

import React, { useState } from 'react';

interface ListItemProps {
  name: string;
  quantity: string | number;
  unit?: string;
}

export default function ListItem({ name, quantity, unit = 'szt.' }: ListItemProps) {
  const [isChecked, setIsChecked] = useState(false);

  return (
    <div 
      className={`
        group flex items-center justify-between p-4 mb-3 rounded-2xl border transition-all duration-300
        ${isChecked 
          ? 'bg-zinc-100 dark:bg-zinc-800/50 border-zinc-200 dark:border-zinc-700 opacity-60' 
          : 'bg-white dark:bg-zinc-900 border-zinc-100 dark:border-zinc-800 shadow-sm hover:shadow-md hover:border-indigo-100 dark:hover:border-indigo-900/30'
        }
      `}
    >
      <div className="flex items-center gap-4 flex-1">
        {/* CUSTOM CHECKBOX */}
        <label className="relative flex items-center cursor-pointer">
          <input 
            type="checkbox" 
            className="peer sr-only" 
            checked={isChecked}
            onChange={() => setIsChecked(!isChecked)}
          />
          <div className="h-6 w-6 rounded-lg border-2 border-zinc-300 dark:border-zinc-600 peer-checked:bg-indigo-600 peer-checked:border-indigo-600 transition-all"></div>
          <svg 
            className="absolute w-4 h-4 text-white left-1 opacity-0 peer-checked:opacity-100 transition-opacity pointer-events-none" 
            xmlns="http://www.w3.org/2000/svg" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="4" 
            strokeLinecap="round" 
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </label>

        {/* NAZWA PRODUKTU */}
        <span className={`
          text-base font-medium transition-all duration-300
          ${isChecked 
            ? 'text-zinc-500 line-through' 
            : 'text-zinc-900 dark:text-zinc-100'
          }
        `}>
          {name}
        </span>
      </div>

      {/* ILOŚĆ */}
      <div className={`
        flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold transition-colors
        ${isChecked 
          ? 'bg-zinc-200 dark:bg-zinc-700 text-zinc-500' 
          : 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400'
        }
      `}>
        <span>{quantity}</span>
        <span className="opacity-70 font-medium">{unit}</span>
      </div>
    </div>
  );
}
