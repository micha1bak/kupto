'use client'

import React, { useState, useEffect, useRef } from 'react';
import { searchProducts, addProductToList, ProductSuggestion } from '@/app/actions/shopping-list';

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<ProductSuggestion[]>([]);
  const [isFocused, setIsFocused] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [selectedProduct, setSelectedProduct] = useState<ProductSuggestion | null>(null);
  const [quantity, setQuantity] = useState('1');
  const containerRef = useRef<HTMLDivElement>(null);
  const quantityInputRef = useRef<HTMLInputElement>(null);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (query.length >= 2) {
        const results = await searchProducts(query);
        setSuggestions(results);
      } else {
        setSuggestions([]);
      }
      setSelectedIndex(-1);
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Handle clicking outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsFocused(false);
        if (!selectedProduct) {
           setSuggestions([]);
        }
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [selectedProduct]);

  // Focus quantity input when modal opens
  useEffect(() => {
    if (selectedProduct && quantityInputRef.current) {
      quantityInputRef.current.focus();
      quantityInputRef.current.select();
    }
  }, [selectedProduct]);

  const handleSelectProduct = (product: ProductSuggestion) => {
    setSelectedProduct(product);
    setQuantity('1');
    setIsFocused(false);
    setSuggestions([]);
  };

  const handleConfirmAdd = async () => {
    if (!selectedProduct) return;
    
    try {
      await addProductToList(selectedProduct.id, quantity);
      setQuery('');
      setSelectedProduct(null);
    } catch (error) {
      console.error('Failed to add product:', error);
    }
  };

  const handleCancelAdd = () => {
    setSelectedProduct(null);
    setIsFocused(true);
    setQuery(query); // Trigger search again or keep current
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (selectedProduct) {
      if (e.key === 'Enter') {
        handleConfirmAdd();
      } else if (e.key === 'Escape') {
        handleCancelAdd();
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : prev));
    } else if (e.key === 'Enter') {
      if (selectedIndex >= 0 && suggestions[selectedIndex]) {
        handleSelectProduct(suggestions[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsFocused(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto px-4 mt-6 relative" ref={containerRef}>
      <div className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-zinc-400 group-focus-within:text-indigo-500 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-5 h-5">
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 1 0 10.607 10.607Z" />
          </svg>
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onKeyDown={handleKeyDown}
          disabled={!!selectedProduct}
          className="block w-full rounded-2xl border-0 py-4 pl-12 pr-4 text-zinc-900 dark:text-white shadow-xl shadow-zinc-200/50 dark:shadow-none ring-1 ring-inset ring-zinc-200 dark:ring-zinc-800 placeholder:text-zinc-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:focus:ring-indigo-500 sm:text-sm bg-white dark:bg-zinc-900 transition-all disabled:opacity-50"
          placeholder="Szukaj lub dodaj produkt..."
        />
        <div className="absolute inset-y-0 right-3 flex items-center">
            <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-2 text-[10px] font-medium text-zinc-400">
                <span>Ctrl</span>K
            </kbd>
        </div>
      </div>

      {/* Sugestie */}
      {isFocused && suggestions.length > 0 && !selectedProduct && (
        <div className="absolute left-4 right-4 mt-2 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-zinc-200 dark:border-zinc-800 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
          <ul className="py-2">
            {suggestions.map((product, index) => (
              <li key={product.id}>
                <button
                  onClick={() => handleSelectProduct(product)}
                  className={`w-full text-left px-4 py-3 flex items-center gap-3 transition-colors ${
                    index === selectedIndex 
                      ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400' 
                      : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/50 text-zinc-700 dark:text-zinc-300'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    index === selectedIndex ? 'bg-indigo-100 dark:bg-indigo-900/40' : 'bg-zinc-100 dark:bg-zinc-800'
                  }`}>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                      <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
                    </svg>
                  </div>
                  <span className="font-medium">{product.name}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Okno ilości */}
      {selectedProduct && (
        <div className="absolute left-4 right-4 mt-2 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border-2 border-indigo-500 z-50 overflow-hidden animate-in zoom-in-95 duration-200 p-4">
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-zinc-900 dark:text-white">
                Ile sztuk: <span className="text-indigo-600 dark:text-indigo-400">{selectedProduct.name}</span>?
              </h3>
              <button 
                onClick={handleCancelAdd}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="flex gap-2">
              <input
                ref={quantityInputRef}
                type="text"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 rounded-xl border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 text-center text-xl font-bold py-3 focus:ring-2 focus:ring-indigo-500 outline-none"
                placeholder="Ilość (np. 2, 500g...)"
              />
              <button
                onClick={handleConfirmAdd}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-semibold shadow-lg shadow-indigo-200 dark:shadow-none transition-all active:scale-95"
              >
                Dodaj
              </button>
            </div>

            <div className="flex justify-center gap-2">
              {['1', '2', '3', '5', '10'].map((val) => (
                <button
                  key={val}
                  onClick={() => setQuantity(val)}
                  className="px-3 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-sm hover:bg-indigo-100 dark:hover:bg-indigo-900/40 hover:text-indigo-600 transition-colors"
                >
                  {val}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
