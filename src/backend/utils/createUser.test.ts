import createUser from './createUser';
import { prisma } from './db';
import { jest, describe, it, expect, beforeEach } from '@jest/globals';

jest.mock('./db', () => ({
    prisma: {
        users: {
            create: jest.fn(),
        },
    },
}));

describe('createNewUser utility', () => {
    const mockUser = {
        login: 'testuser',
        password: 'securepassword123',
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should successfully create a user and return the result', async () => {
        const expectedResult = {
            user_id: 1,
            login: 'testuser',
            password: 'hashed_securepassword123',
            default_list_id: null,
        };
        (prisma.users.create as jest.Mock).mockResolvedValue(expectedResult as never);
        const result = await createUser(mockUser);
        expect(prisma.users.create).toHaveBeenCalledWith({
            data: {
                login: mockUser.login,
                password: expect.any(String),
            },
        });
        expect(result).toEqual(expectedResult);
    });
        it('should throw an error when prisma.create fails', async () => {
            const error = new Error('Database connection failed');
            (prisma.users.create as any).mockRejectedValue(error);
            await expect(createUser(mockUser)).rejects.toThrow('Database connection failed');
        });
});
