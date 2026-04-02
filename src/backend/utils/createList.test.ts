import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import createList from './createList';
import { prisma } from './db';

jest.mock('./db', () => ({
    prisma: {
        list: {
            create: jest.fn(),
        },
    },
}));

describe('createList utility', () => {
    const mockListData = {
        ownerId: 1,
        name: 'Moja Lista',
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should successfully create a list and return the result', async () => {
        const expectedResult = {
            list_id: 10,
            owner_id: 1,
            name: 'Moja Lista',
        };
        jest.mocked(prisma.list.create).mockResolvedValue(expectedResult as any);
        const result = await createList(mockListData);
        expect(prisma.list.create).toHaveBeenCalledWith({
            data: {
                owner_id: mockListData.ownerId,
                name: mockListData.name,
            },
        });
        expect(result).toEqual(expectedResult);
    });

    it('should throw an error when prisma.list.create fails', async () => {
        const dbError = new Error('Database error');
        jest.mocked(prisma.list.create).mockRejectedValue(dbError as never);
        await expect(createList(mockListData)).rejects.toThrow('Database error');
    });
});
