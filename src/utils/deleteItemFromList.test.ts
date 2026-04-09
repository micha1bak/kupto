import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import deleteItemFromList from './deleteItemFromList.js';
import { prisma } from './db.js';

jest.mock('./db', () => ({
    prisma: {
        users: {
            findUniqueOrThrow: jest.fn(),
        },
        list_item: {
            delete: jest.fn(),
        },
    },
}));

describe('deleteItemFromList utility', () => {
    const mockData = {
        userId: 1,
        productId: 101,
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should successfully delete an item from the default list', async () => {
        const mockUser = { default_list_id: 10 };
        const mockResult = {
            list_id: 10,
            product_id: 101,
            quantity: '3 szt'
        };

        jest.mocked(prisma.users.findUniqueOrThrow).mockResolvedValue(mockUser as any);
        jest.mocked(prisma.list_item.delete).mockResolvedValue(mockResult as any);

        const result = await deleteItemFromList(mockData);

        expect(prisma.users.findUniqueOrThrow).toHaveBeenCalledWith({
            where: { user_id: mockData.userId },
            select: { default_list_id: true }
        });

        expect(prisma.list_item.delete).toHaveBeenCalledWith({
            where: {
                list_id_product_id: {
                    list_id: 10,
                    product_id: 101
                }
            }
        });

        expect(result).toEqual(mockResult);
    });

    it('should throw an error if user has no default list', async () => {
        jest.mocked(prisma.users.findUniqueOrThrow).mockResolvedValue({ default_list_id: null } as any);

        await expect(deleteItemFromList(mockData)).rejects.toThrow('User has no default list');
    });

    it('should propagate database errors', async () => {
        const dbError = new Error('Database Error');
        jest.mocked(prisma.users.findUniqueOrThrow).mockRejectedValue(dbError as never);

        await expect(deleteItemFromList(mockData)).rejects.toThrow('Database Error');
    });
});
