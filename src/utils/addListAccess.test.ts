import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import addListAccess from './addListAccess.js';
import { prisma } from './db.js';

jest.mock('./db', () => ({
    prisma: {
        list: { findUnique: jest.fn() },
        users: { findUnique: jest.fn() },
        list_access: { create: jest.fn() }
    },
}));

describe('addListAccess utility', () => {
    const mockListId = 100;
    const mockRequesterId = 1;
    const mockNewUserLogin = 'new_user';
    const mockNewUserId = 2;

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should add access successfully if requester is the owner', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: mockRequesterId } as any);
        jest.mocked(prisma.users.findUnique).mockResolvedValue({ user_id: mockNewUserId, login: mockNewUserLogin } as any);
        jest.mocked(prisma.list_access.create).mockResolvedValue({} as any);

        const result = await addListAccess(mockListId, mockNewUserLogin, mockRequesterId);

        expect(result).toEqual({ user_id: mockNewUserId, login: mockNewUserLogin });
        expect(prisma.list_access.create).toHaveBeenCalledWith({
            data: { list_id: mockListId, user_id: mockNewUserId }
        });
    });

    it('should throw error if list not found', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue(null);
        await expect(addListAccess(mockListId, mockNewUserLogin, mockRequesterId)).rejects.toThrow('List not found');
    });

    it('should throw error if requester is not the owner', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: 999 } as any);
        await expect(addListAccess(mockListId, mockNewUserLogin, mockRequesterId)).rejects.toThrow('Only the owner can manage access');
    });

    it('should throw error if user to add not found', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: mockRequesterId } as any);
        jest.mocked(prisma.users.findUnique).mockResolvedValue(null);
        await expect(addListAccess(mockListId, 'non_existent', mockRequesterId)).rejects.toThrow('User not found');
    });

    it('should throw error if user to add is the owner', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: mockRequesterId } as any);
        jest.mocked(prisma.users.findUnique).mockResolvedValue({ user_id: mockRequesterId, login: 'owner' } as any);
        await expect(addListAccess(mockListId, 'owner', mockRequesterId)).rejects.toThrow('User is already the owner of this list');
    });

    it('should throw error if user already has access', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue({ owner_id: mockRequesterId } as any);
        jest.mocked(prisma.users.findUnique).mockResolvedValue({ user_id: mockNewUserId, login: mockNewUserLogin } as any);
        const error = new Error('Unique constraint');
        (error as any).code = 'P2002';
        jest.mocked(prisma.list_access.create).mockRejectedValue(error as never);

        await expect(addListAccess(mockListId, mockNewUserLogin, mockRequesterId)).rejects.toThrow('User already has access to this list');
    });
});
