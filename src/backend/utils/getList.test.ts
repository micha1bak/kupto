import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import getList from './getList';
import { prisma } from './db';

jest.mock('./db', () => ({
    prisma: {
        users: {
            findUnique: jest.fn(),
        },
        list_item: {
            findMany: jest.fn(),
        },
    },
}));

describe('getList utility', () => {
    const mockUserId = 1;

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should return grouped and sorted shopping list for a user', async () => {
        const mockUser = { default_list_id: 10 };
        const mockListItems = [
            {
                product_id: 101,
                quantity: '2 szt',
                product: {
                    name: 'Mleko',
                    category: { name: 'Nabiał' }
                }
            },
            {
                product_id: 102,
                quantity: '1 kg',
                product: {
                    name: 'Chleb',
                    category: { name: 'Pieczywo' }
                }
            },
            {
                product_id: 103,
                quantity: '1 szt',
                product: {
                    name: 'Ser',
                    category: { name: 'Nabiał' }
                }
            }
        ];

        jest.mocked(prisma.users.findUnique).mockResolvedValue(mockUser as any);
        jest.mocked(prisma.list_item.findMany).mockResolvedValue(mockListItems as any);

        const result: any = await getList(mockUserId);

        expect(result).toHaveLength(2);
        expect(result[0].category).toBe('Nabiał');
        expect(result[0].items).toHaveLength(2);
        expect(result[1].category).toBe('Pieczywo');
        expect(result[1].items[0].name).toBe('Chleb');
    });

    it('should return an empty array if user or default list is not found', async () => {
        jest.mocked(prisma.users.findUnique).mockResolvedValue(null);

        const result = await getList(mockUserId);

        expect(result).toEqual([]);
        expect(prisma.list_item.findMany).not.toHaveBeenCalled();
    });

    it('should propagate database errors', async () => {
        const dbError = new Error('Connection failed');
        jest.mocked(prisma.users.findUnique).mockRejectedValue(dbError as never);

        await expect(getList(mockUserId)).rejects.toThrow('Connection failed');
    });
});
