import { login } from './auth';
import { query } from '@/lib/db';
import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

// Pomocniczy typ dla mocków
const mockedQuery = query as unknown as jest.Mock;
const mockedRedirect = redirect as unknown as jest.Mock;
const mockedCookies = cookies as unknown as jest.Mock;

describe('Auth Actions', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('Should return error if fields are empty', async () => {
    const formData = new FormData();
    const result = await login(formData);

    expect(result).toEqual({ error: 'Wpisz login i hasło' });
    expect(mockedQuery).not.toHaveBeenCalled();
  });

  test('Should return error if user is not found', async () => {
    const formData = new FormData();
    formData.append('login', 'nie-ma-mnie');
    formData.append('password', 'secret');

    // Mockujemy pusty wynik z bazy
    mockedQuery.mockResolvedValueOnce({ rows: [] });

    const result = await login(formData);

    expect(result).toEqual({ error: 'Nieprawidłowy login lub hasło' });
  });

  test('Should set cookie and redirect on successful login', async () => {
    const formData = new FormData();
    formData.append('login', 'admin');
    formData.append('password', '123');

    // Mockujemy użytkownika w bazie
    mockedQuery.mockResolvedValueOnce({
      rows: [{ user_id: 1, password: '123' }]
    });

    await login(formData);

    // Sprawdzamy czy ciasteczko zostało ustawione
    const mockCookieStore = await mockedCookies();
    expect(mockCookieStore.set).toHaveBeenCalled();

    // Sprawdzamy przekierowanie na stronę główną
    expect(mockedRedirect).toHaveBeenCalledWith('/');
  });
});
