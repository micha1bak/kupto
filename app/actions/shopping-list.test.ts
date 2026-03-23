import { getShoppingList, searchProducts, addProductToList } from './shopping-list';
import { query } from '@/lib/db';
import { getSession } from '@/lib/auth';
import { revalidatePath } from 'next/cache';

// Mocks
jest.mock('@/lib/db', () => ({
  query: jest.fn(),
}));

jest.mock('@/lib/auth', () => ({
  getSession: jest.fn(),
}));

jest.mock('next/cache', () => ({
  revalidatePath: jest.fn(),
}));

const mockedQuery = query as jest.Mock;
const mockedGetSession = getSession as jest.Mock;
const mockedRevalidatePath = revalidatePath as jest.Mock;

describe('Shopping List Actions', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getShoppingList', () => {
    test('Should return empty array if user is not logged in', async () => {
      mockedGetSession.mockResolvedValueOnce(null);
      const result = await getShoppingList();
      expect(result).toEqual([]);
      expect(mockedQuery).not.toHaveBeenCalled();
    });

    test('Should return empty array if query fails', async () => {
      mockedGetSession.mockResolvedValueOnce({ userId: 1 });
      mockedQuery.mockRejectedValueOnce(new Error('DB Error'));
      const result = await getShoppingList();
      expect(result).toEqual([]);
    });

    test('Should return grouped shopping list', async () => {
      mockedGetSession.mockResolvedValueOnce({ userId: 1 });
      
      mockedQuery.mockResolvedValueOnce({
        rows: [
          { category_name: 'Warzywa', id: 1, product_name: 'Ziemniaki', quantity: '2 kg' },
          { category_name: 'Warzywa', id: 2, product_name: 'Marchew', quantity: '1 szt' },
          { category_name: 'Nabiał', id: 3, product_name: 'Mleko', quantity: '2 l' },
        ]
      });

      const result = await getShoppingList();

      expect(result).toHaveLength(2);
      expect(result[0].category).toBe('Warzywa');
      expect(result[1].category).toBe('Nabiał');
    });
  });

  describe('searchProducts', () => {
    test('Should return empty array for short query', async () => {
      const result = await searchProducts('a');
      expect(result).toEqual([]);
      expect(mockedQuery).not.toHaveBeenCalled();
    });

    test('Should return products matching query', async () => {
      mockedGetSession.mockResolvedValueOnce({ userId: 1 });
      mockedQuery.mockResolvedValueOnce({
        rows: [
          { id: 1, name: 'Mleko' },
          { id: 2, name: 'Masło' },
        ]
      });

      const result = await searchProducts('mle');
      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('Mleko');
      expect(mockedQuery).toHaveBeenCalledWith(expect.stringContaining('ILIKE'), ['%mle%']);
    });
  });

  describe('addProductToList', () => {
    test('Should throw error if not authorized', async () => {
      mockedGetSession.mockResolvedValueOnce(null);
      await expect(addProductToList(1)).rejects.toThrow('Unauthorized');
    });

    test('Should add product to existing list with default quantity', async () => {
      mockedGetSession.mockResolvedValueOnce({ userId: 1 });
      // Mock list check
      mockedQuery.mockResolvedValueOnce({ rows: [{ list_id: 10 }] });
      // Mock insert item
      mockedQuery.mockResolvedValueOnce({ rows: [] });

      const result = await addProductToList(5);
      expect(result).toEqual({ success: true });
      expect(mockedQuery).toHaveBeenCalledWith(expect.stringContaining('INSERT INTO list_item'), [10, 5, '1']);
      expect(mockedRevalidatePath).toHaveBeenCalledWith('/');
    });

    test('Should add product to existing list with custom quantity', async () => {
      mockedGetSession.mockResolvedValueOnce({ userId: 1 });
      // Mock list check
      mockedQuery.mockResolvedValueOnce({ rows: [{ list_id: 10 }] });
      // Mock insert item
      mockedQuery.mockResolvedValueOnce({ rows: [] });

      const result = await addProductToList(5, '500g');
      expect(result).toEqual({ success: true });
      expect(mockedQuery).toHaveBeenCalledWith(expect.stringContaining('INSERT INTO list_item'), [10, 5, '500g']);
    });

    test('Should create list if none exists and add product', async () => {
      mockedGetSession.mockResolvedValueOnce({ userId: 1 });
      // Mock list check (empty)
      mockedQuery.mockResolvedValueOnce({ rows: [] });
      // Mock create list
      mockedQuery.mockResolvedValueOnce({ rows: [{ list_id: 20 }] });
      // Mock insert item
      mockedQuery.mockResolvedValueOnce({ rows: [] });

      await addProductToList(5);
      expect(mockedQuery).toHaveBeenCalledWith(expect.stringContaining('INSERT INTO list'), [1, 'Moja Lista']);
      expect(mockedQuery).toHaveBeenCalledWith(expect.stringContaining('INSERT INTO list_item'), [20, 5, '1']);
    });
  });
});
