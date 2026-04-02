import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import setDefaultList from './setDefaultList';
import { prisma } from './db';

jest.mock('./db', () => ({
    prisma: {
        list_access: {
            findUniqueOrThrow: jest.fn(),
        },
        users: {
            update: jest.fn(),
        },
    },
}));

describe('setDefaultList utility', () => {
    const mockData = {
        userId: 1,
        listId: 10,
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should update the default list if user has access', async () => {
        const mockAccess = { list_id: 10, user_id: 1 };
        const mockUpdatedUser = { user_id: 1, default_list_id: 10 };

        jest.mocked(prisma.list_access.findUniqueOrThrow).mockResolvedValue(mockAccess as any);
        jest.mocked(prisma.users.update).mockResolvedValue(mockUpdatedUser as any);

        const result = await setDefaultList(mockData);

        expect(prisma.list_access.findUniqueOrThrow).toHaveBeenCalledWith({
            where: {
                list_id_user_id: {
                    list_id: 10,
                    user_id: 1
                }
            }
        });

        expect(prisma.users.update).toHaveBeenCalledWith({
            where: { user_id: 1 },
            data: { default_list_id: 10 }
        });

        expect(result).toEqual(mockUpdatedUser);
    });

    it('should propagate error if access check fails', async () => {
        const accessError = new Error('No access');
        jest.mocked(prisma.list_access.findUniqueOrThrow).mockRejectedValue(accessError as never);

        await expect(setDefaultList(mockData)).rejects.toThrow('No access');
        expect(prisma.users.update).not.toHaveBeenCalled();
    });

    it('should propagate database error on update', async () => {
        const mockAccess = { list_id: 10, user_id: 1 };
        const updateError = new Error('Update failed');

        jest.mocked(prisma.list_access.findUniqueOrThrow).mockResolvedValue(mockAccess as any);
        jest.mocked(prisma.users.update).mockRejectedValue(updateError as never);

        await expect(setDefaultList(mockData)).rejects.toThrow('Update failed');
    });
});
