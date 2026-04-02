import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import getUserProfile from './getUserProfile';
import { prisma } from './db';

jest.mock('./db', () => ({
    prisma: {
        users: {
            findUniqueOrThrow: jest.fn(),
        },
    },
}));

describe('getUserProfile utility', () => {
    const mockUserId = 1;

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should return user login and default list id', async () => {
        const mockUser = { login: 'testuser', default_list_id: 10 };
        jest.mocked(prisma.users.findUniqueOrThrow).mockResolvedValue(mockUser as any);

        const result = await getUserProfile(mockUserId);

        expect(prisma.users.findUniqueOrThrow).toHaveBeenCalledWith({
            where: { user_id: mockUserId },
            select: { login: true, default_list_id: true }
        });
        expect(result).toEqual(mockUser);
    });

    it('should propagate database errors', async () => {
        const dbError = new Error('User not found');
        jest.mocked(prisma.users.findUniqueOrThrow).mockRejectedValue(dbError as never);

        await expect(getUserProfile(mockUserId)).rejects.toThrow('User not found');
    });
});
