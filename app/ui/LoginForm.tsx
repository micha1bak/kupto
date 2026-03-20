'use client'

import React, { useState } from 'react';
import { login } from '@/app/actions/auth';

export default function LoginForm() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(formData: FormData) {
    setLoading(true);
    setError(null);
    const result = await login(formData);
    if (result?.error) {
      setError(result.error);
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-full flex-1 flex-col justify-center px-6 py-12 lg:px-8 bg-white dark:bg-zinc-900 rounded-3xl shadow-2xl max-w-md w-full mx-auto border border-zinc-200 dark:border-zinc-800">
      <div className="sm:mx-auto sm:w-full sm:max-w-sm">
        <div className="flex justify-center mb-6">
          <div className="h-16 w-16 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <span className="text-white text-3xl font-black italic">K</span>
          </div>
        </div>
        <h1 className="text-center text-3xl font-black tracking-tight text-zinc-900 dark:text-white">Kupto 2.0</h1>
        <p className="mt-2 text-center text-sm text-zinc-500 dark:text-zinc-400">
          Zaloguj się do swojej wspólnej listy
        </p>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
        <form className="space-y-6" action={handleSubmit}>
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-xs font-bold rounded-xl border border-red-100 dark:border-red-900/30 text-center animate-shake">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="login" className="block text-sm font-semibold leading-6 text-zinc-900 dark:text-zinc-100">
              Email / Login
            </label>
            <div className="mt-2">
              <input
                id="login"
                name="login"
                type="text"
                autoComplete="username"
                required
                className="block w-full rounded-xl border-0 py-2.5 px-4 text-zinc-900 dark:text-white shadow-sm ring-1 ring-inset ring-zinc-300 dark:ring-zinc-700 placeholder:text-zinc-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:focus:ring-indigo-500 sm:text-sm sm:leading-6 bg-zinc-50 dark:bg-zinc-800 transition-all"
                placeholder="Twój login"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label htmlFor="password" className="block text-sm font-semibold leading-6 text-zinc-900 dark:text-zinc-100">
                Hasło
              </label>
            </div>
            <div className="mt-2 relative">
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="block w-full rounded-xl border-0 py-2.5 px-4 text-zinc-900 dark:text-white shadow-sm ring-1 ring-inset ring-zinc-300 dark:ring-zinc-700 placeholder:text-zinc-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:focus:ring-indigo-500 sm:text-sm sm:leading-6 bg-zinc-50 dark:bg-zinc-800 transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="group relative flex w-full justify-center rounded-xl bg-indigo-600 px-3 py-3 text-sm font-bold leading-6 text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Logowanie...' : 'Zaloguj się'}
            </button>
          </div>
        </form>

        <div className="mt-8 text-center">
            <p className="text-xs text-zinc-500 uppercase tracking-widest font-medium">Kupto &copy; 2026</p>
        </div>
      </div>
    </div>
  );
}
