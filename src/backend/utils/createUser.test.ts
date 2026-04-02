import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import createUser from './createUser';
import { prisma } from './db';

jest.mock('./db', () => ({
    prisma: {
        $transaction: jest.fn(),
    },
}));

describe('createUser utility with auto-list', () => {
    const mockUser = {
        login: 'newuser',
        password: 'password123',
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should create user, list and update user in a transaction', async () => {
        const mockCreatedUser = { user_id: 1, login: 'newuser' };
        const mockCreatedList = { list_id: 10, name: 'Moja Lista' };
        const mockFinalUser = { user_id: 1, login: 'newuser', default_list_id: 10 };

        // Mockowanie transakcji - symulujemy wykonanie funkcji przekazanej do $transaction
        jest.mocked(prisma.$transaction).mockImplementation(async (callback: any) => {
            const tx = {
                users: {
                    create: jest.fn().mockResolvedValue(mockCreatedUser),
                    update: jest.fn().mockResolvedValue(mockFinalUser),
                },
                list: {
                    create: jest.fn().mockResolvedValue(mockCreatedList),
                }
            };
            return callback(tx);
        });

        const result = await createUser(mockUser);

        expect(prisma.$transaction).toHaveBeenCalled();
        expect(result).toEqual(mockFinalUser);
        expect(result.default_list_id).toBe(10);
    });

    it('should throw an error if transaction fails', async () => {
        jest.mocked(prisma.$transaction).mockRejectedValue(new Error('Transaction failed') as never);

        await expect(createUser(mockUser)).rejects.toThrow('Transaction failed');
    });
});
