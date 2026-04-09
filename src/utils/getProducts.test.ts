import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import getProducts from './getProducts.js';
import { prisma } from './db.js';

jest.mock('./db', () => ({
    prisma: {
        product: {
            findMany: jest.fn(),
        },
    },
}));

describe('getProducts utility', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should return a list of formatted products', async () => {
        const mockProducts = [
            {
                product_id: 1,
                name: 'Chleb',
                category_id: 10,
                category: { name: 'Pieczywo' }
            },
            {
                product_id: 2,
                name: 'Mleko',
                category_id: 11,
                category: { name: 'Nabiał' }
            }
        ];

        jest.mocked(prisma.product.findMany).mockResolvedValue(mockProducts as any);

        const result = await getProducts();

        expect(prisma.product.findMany).toHaveBeenCalledWith({
            include: { category: true },
            orderBy: { name: 'asc' }
        });

        expect(result).toEqual([
            { id: 1, name: 'Chleb', category: 'Pieczywo', categoryId: 10 },
            { id: 2, name: 'Mleko', category: 'Nabiał', categoryId: 11 }
        ]);
    });

    it('should return an empty array if no products found', async () => {
        jest.mocked(prisma.product.findMany).mockResolvedValue([]);

        const result = await getProducts();

        expect(result).toEqual([]);
    });

    it('should propagate database errors', async () => {
        const dbError = new Error('Database connection failed');
        jest.mocked(prisma.product.findMany).mockRejectedValue(dbError as never);

        await expect(getProducts()).rejects.toThrow('Database connection failed');
    });
});
