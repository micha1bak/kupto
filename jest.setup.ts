import '@testing-library/jest-dom';

// Obiekt, który będzie współdzielony między testem a kodem aplikacji
const mockCookieStore = {
  set: jest.fn(),
  get: jest.fn(),
  delete: jest.fn(),
};

// Mockowanie next/headers
jest.mock('next/headers', () => ({
  cookies: jest.fn(async () => mockCookieStore),
}));

// Mockowanie next/navigation (redirect nie zadziała w teście)
jest.mock('next/navigation', () => ({
  redirect: jest.fn(),
}));

// Mockowanie bazy danych
jest.mock('@/lib/db', () => ({
  query: jest.fn(),
}));

// Mockowanie lib/auth, aby uniknąć problemów z ESM/jose
jest.mock('@/lib/auth', () => ({
  signJWT: jest.fn().mockResolvedValue('mocked-jwt-token'),
  verifyJWT: jest.fn(),
  getSession: jest.fn(),
}));
