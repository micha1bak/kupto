import { getShoppingList } from './shopping-list';
import { query } from '@/lib/db';
import { getSession } from '@/lib/auth';

// Mocks
jest.mock('@/lib/db', () => ({
  query: jest.fn(),
}));

jest.mock('@/lib/auth', () => ({
  getSession: jest.fn(),
}));

const mockedQuery = query as jest.Mock;
const mockedGetSession = getSession as jest.Mock;

describe('Shopping List Actions', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

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
    expect(result[0]).toEqual({
      category: 'Warzywa',
      items: [
        { id: 1, name: 'Ziemniaki', quantity: '2 kg' },
        { id: 2, name: 'Marchew', quantity: '1 szt' },
      ]
    });
    expect(result[1]).toEqual({
      category: 'Nabiał',
      items: [
        { id: 3, name: 'Mleko', quantity: '2 l' },
      ]
    });
  });
});
