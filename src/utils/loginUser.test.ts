import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import loginUser from './loginUser.js';
import { prisma } from './db.js';
import bcrypt from 'bcrypt';

jest.mock('jsonwebtoken', () => ({
    sign: jest.fn().mockReturnValue('mocked_jwt_token'),
}));

jest.mock('./db', () => ({
    prisma: {
        users: {
            findUniqueOrThrow: jest.fn(),
        },
    },
}));

jest.mock('bcrypt', () => ({
    compare: jest.fn(),
}));

describe('loginUser utility', () => {
    const mockCredentials = {
        login: 'testuser',
        password: 'password123',
    };

    const mockDbUser = {
        user_id: 1,
        login: 'testuser',
        password: 'hashed_password',
    };

    beforeEach(() => {
        jest.clearAllMocks();
        process.env.JWT_SECRET = 'test_secret_key';
    });

    it('should return a JWT token on successful login', async () => {
        (prisma.users.findUniqueOrThrow as jest.Mock).mockResolvedValue(mockDbUser as never);
        (bcrypt.compare as jest.Mock).mockResolvedValue(true as never);
        const token = await loginUser(mockCredentials);
        expect(prisma.users.findUniqueOrThrow).toHaveBeenCalledWith({
            where: { login: mockCredentials.login }
        });
        expect(bcrypt.compare).toHaveBeenCalledWith(mockCredentials.password, mockDbUser.password);
        expect(typeof token).toBe('string');
        expect(token.length).toBeGreaterThan(0);
    });

    it('should throw "Invalid password" error when password does not match', async () => {
        (prisma.users.findUniqueOrThrow as jest.Mock).mockResolvedValue(mockDbUser as never);
        (bcrypt.compare as jest.Mock).mockResolvedValue(false as never);
        await expect(loginUser(mockCredentials)).rejects.toThrow('Invalid password');
    });

    it('should propagate error if user is not found in database', async () => {
        const dbError = new Error('User not found');
        (prisma.users.findUniqueOrThrow as jest.Mock).mockRejectedValue(dbError as never);
        await expect(loginUser(mockCredentials)).rejects.toThrow('User not found');
    });
});
