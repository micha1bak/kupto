import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import getAvailableLists from './getAvailableLists.js';
import { prisma } from './db.js';

jest.mock('./db', () => ({
    prisma: {
        list_access: {
            findMany: jest.fn(),
        },
    },
}));

describe('getAvailableLists utility', () => {
    const mockUserId = 1;

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should return a list of available lists for the user', async () => {
        const mockAccess = [
            {
                list: { list_id: 10, name: 'Dom' }
            },
            {
                list: { list_id: 11, name: 'Praca' }
            }
        ];

        jest.mocked(prisma.list_access.findMany).mockResolvedValue(mockAccess as any);

        const result = await getAvailableLists(mockUserId);

        expect(prisma.list_access.findMany).toHaveBeenCalledWith({
            where: { user_id: mockUserId },
            include: {
                list: {
                    select: { list_id: true, owner_id: true, name: true }
                }
            }
        });

        expect(result).toEqual([
            { can_manage_access: false, list_id: 10, name: 'Dom' },
            { can_manage_access: false, list_id: 11, name: 'Praca' }
        ]);
    });

    it('should return an empty array if no lists found', async () => {
        jest.mocked(prisma.list_access.findMany).mockResolvedValue([]);

        const result = await getAvailableLists(mockUserId);

        expect(result).toEqual([]);
    });

    it('should propagate database errors', async () => {
        const dbError = new Error('Database Error');
        jest.mocked(prisma.list_access.findMany).mockRejectedValue(dbError as never);

        await expect(getAvailableLists(mockUserId)).rejects.toThrow('Database Error');
    });
});
