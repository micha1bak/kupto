import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import getCategories from './getCategories.js';
import { prisma } from './db.js';

jest.mock('./db', () => ({
    prisma: {
        category: {
            findMany: jest.fn(),
        },
    },
}));

describe('getCategories utility', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should return a list of categories', async () => {
        const mockCategories = [
            { category_id: 1, name: 'Nabiał' },
            { category_id: 2, name: 'Pieczywo' }
        ];

        jest.mocked(prisma.category.findMany).mockResolvedValue(mockCategories as any);

        const result = await getCategories();

        expect(prisma.category.findMany).toHaveBeenCalledWith({
            orderBy: { name: 'asc' }
        });

        expect(result).toEqual(mockCategories);
    });

    it('should return an empty array if no categories found', async () => {
        jest.mocked(prisma.category.findMany).mockResolvedValue([]);

        const result = await getCategories();

        expect(result).toEqual([]);
    });

    it('should propagate database errors', async () => {
        const dbError = new Error('Database Error');
        jest.mocked(prisma.category.findMany).mockRejectedValue(dbError as never);

        await expect(getCategories()).rejects.toThrow('Database Error');
    });
});
