'use server'

import { query } from '@/lib/db';
import { signJWT } from '@/lib/auth';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export async function login(formData: FormData) {
  const login = formData.get('login') as string;
  const password = formData.get('password') as string;

  if (!login || !password) {
    return { error: 'Wpisz login i hasło' };
  }

  try {
    const result = await query(
      'SELECT user_id, password FROM users WHERE login = $1',
      [login]
    );

    if (result.rows.length === 0) {
      return { error: 'Nieprawidłowy login lub hasło' };
    }

    const user = result.rows[0];

    // v1.0 używa czystego tekstu. Docelowo: bcrypt.compare
    if (user.password !== password) {
      return { error: 'Nieprawidłowy login lub hasło' };
    }

    const token = await signJWT({ userId: user.user_id });

    const cookieStore = await cookies();
    cookieStore.set('token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 30, // 30 dni
    });

  } catch (error) {
    console.error('Błąd logowania:', error);
    return { error: 'Wystąpił błąd serwera' };
  }

  redirect('/');
}

export async function logout() {
  const cookieStore = await cookies();
  cookieStore.delete('token');
  redirect('/login');
}
