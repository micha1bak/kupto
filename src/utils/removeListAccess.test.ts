import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import removeListAccess from './removeListAccess.js';
import { prisma } from './db.js';

jest.mock('./db', () => ({
    prisma: {
        list: { findUnique: jest.fn() },
        list_access: { delete: jest.fn() }
    },
}));

describe('removeListAccess utility', () => {
    const mockListId = 100;
    const mockRequesterId = 1;
    const mockTargetUserId = 2;

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should remove access successfully if requester is the owner', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: mockRequesterId } as any);
        jest.mocked(prisma.list_access.delete).mockResolvedValue({} as any);

        const result = await removeListAccess(mockListId, mockTargetUserId, mockRequesterId);

        expect(result).toEqual({ success: true });
        expect(prisma.list_access.delete).toHaveBeenCalledWith({
            where: {
                list_id_user_id: {
                    list_id: mockListId,
                    user_id: mockTargetUserId
                }
            }
        });
    });

    it('should throw error if list not found', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue(null);
        await expect(removeListAccess(mockListId, mockTargetUserId, mockRequesterId)).rejects.toThrow('List not found');
    });

    it('should throw error if requester is not the owner', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: 999 } as any);
        await expect(removeListAccess(mockListId, mockTargetUserId, mockRequesterId)).rejects.toThrow('Only the owner can manage access');
    });

    it('should throw error if trying to remove the owner', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: mockRequesterId } as any);
        await expect(removeListAccess(mockListId, mockRequesterId, mockRequesterId)).rejects.toThrow('Cannot remove access from the owner');
    });

    it('should throw error if user does not have access', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: mockRequesterId } as any);
        const error = new Error('Not found');
        (error as any).code = 'P2025';
        jest.mocked(prisma.list_access.delete).mockRejectedValue(error as never);

        await expect(removeListAccess(mockListId, mockTargetUserId, mockRequesterId)).rejects.toThrow('User does not have access to this list');
    });
});
