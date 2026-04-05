import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import getListAccess from './getListAccess';
import { prisma } from './db';

jest.mock('./db', () => ({
    prisma: {
        list: {
            findUnique: jest.fn(),
        },
    },
}));

describe('getListAccess utility', () => {
    const mockRequesterId = 1;
    const mockListId = 100;

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should return list access details if requester is owner', async () => {
        const mockList = {
            list_id: mockListId,
            owner_id: mockRequesterId,
            users_list_owner_idTousers: {
                user_id: mockRequesterId,
                login: 'owner_user'
            },
            list_access: [
                {
                    users: {
                        user_id: 2,
                        login: 'shared_user'
                    }
                }
            ]
        };

        jest.mocked(prisma.list.findUnique).mockResolvedValue(mockList as any);

        const result = await getListAccess(mockListId, mockRequesterId);

        expect(result).toEqual({
            owner: { user_id: 1, login: 'owner_user' },
            shared_with: [
                { user_id: 2, login: 'shared_user' }
            ],
            is_owner: true
        });
    });

    it('should return list access details if requester is in list_access', async () => {
        const mockList = {
            list_id: mockListId,
            owner_id: 2,
            users_list_owner_idTousers: {
                user_id: 2,
                login: 'other_owner'
            },
            list_access: [
                {
                    user_id: mockRequesterId,
                    users: {
                        user_id: mockRequesterId,
                        login: 'requester_user'
                    }
                }
            ]
        };

        jest.mocked(prisma.list.findUnique).mockResolvedValue(mockList as any);

        const result = await getListAccess(mockListId, mockRequesterId);

        expect(result).toEqual({
            owner: { user_id: 2, login: 'other_owner' },
            shared_with: [
                { user_id: mockRequesterId, login: 'requester_user' }
            ],
            is_owner: false
        });
    });

    it('should throw error if list not found', async () => {
        jest.mocked(prisma.list.findUnique).mockResolvedValue(null);

        await expect(getListAccess(mockListId, mockRequesterId)).rejects.toThrow('List not found');
    });

    it('should throw error if requester has no access', async () => {
        const mockList = {
            list_id: mockListId,
            owner_id: 2,
            users_list_owner_idTousers: {
                user_id: 2,
                login: 'other_owner'
            },
            list_access: []
        };

        jest.mocked(prisma.list.findUnique).mockResolvedValue(mockList as any);

        await expect(getListAccess(mockListId, mockRequesterId)).rejects.toThrow('Access denied');
    });

    it('should propagate database errors', async () => {
        const dbError = new Error('Database Error');
        jest.mocked(prisma.list.findUnique).mockRejectedValue(dbError as never);

        await expect(getListAccess(mockListId, mockRequesterId)).rejects.toThrow('Database Error');
    });
});
