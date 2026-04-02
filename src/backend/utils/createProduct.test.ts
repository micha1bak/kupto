import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import createProduct from './createProduct';
import { prisma } from './db';

jest.mock('./db', () => ({
    prisma: {
        product: {
            create: jest.fn(),
        },
    },
}));

describe('createProduct utility', () => {
    const mockData = {
        categoryId: 10,
        name: 'mLeKo uHT'
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should successfully create a product with formatted name', async () => {
        const expectedResult = {
            product_id: 1,
            category_id: 10,
            name: 'Mleko uht'
        };

        jest.mocked(prisma.product.create).mockResolvedValue(expectedResult as any);

        const result = await createProduct(mockData);

        expect(prisma.product.create).toHaveBeenCalledWith({
            data: {
                category_id: 10,
                name: 'Mleko uht'
            }
        });

        expect(result).toEqual(expectedResult);
    });

    it('should propagate database errors', async () => {
        const dbError = new Error('Database Error');
        jest.mocked(prisma.product.create).mockRejectedValue(dbError as never);

        await expect(createProduct(mockData)).rejects.toThrow('Database Error');
    });
});
