import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import { authMiddleware, AuthRequest } from './authMiddleware';
import { Response, NextFunction } from 'express';
import { jwtVerify } from 'jose';

jest.mock('jose', () => ({
    jwtVerify: jest.fn(),
}));

describe('authMiddleware', () => {
    let req: Partial<AuthRequest>;
    let res: Partial<Response>;
    let next: NextFunction;

    beforeEach(() => {
        req = {
            cookies: {},
            headers: {},
        } as any;
        res = {
            status: jest.fn().mockReturnThis(),
            json: jest.fn().mockReturnThis(),
        } as any;
        next = jest.fn() as any;
        jest.clearAllMocks();
    });

    it('should return 401 if jwt cookie is missing', async () => {
        await authMiddleware(req as AuthRequest, res as Response, next);
        expect(res.status).toHaveBeenCalledWith(401);
        expect(res.json).toHaveBeenCalledWith({ error: 'Invalid token' });
        expect(next).not.toHaveBeenCalled();
    });

    it('should return 401 if jwt token is invalid', async () => {
        req.cookies!.jwt = 'invalid-token';
        (jwtVerify as jest.Mock).mockRejectedValue(new Error('Invalid token') as never);
        await authMiddleware(req as AuthRequest, res as Response, next);
        expect(res.status).toHaveBeenCalledWith(401);
        expect(res.json).toHaveBeenCalledWith({ error: 'Invalid token' });
        expect(next).not.toHaveBeenCalled();
    });

    it('should add userId to req and call next() for correct jwt cookie', async () => {
        req.cookies!.jwt = 'valid-token';
        const mockPayload = { userId: 123 };
        (jwtVerify as jest.Mock).mockResolvedValue({ payload: mockPayload } as never);
        await authMiddleware(req as AuthRequest, res as Response, next);
        expect(req.user).toEqual({ userId: 123 });
        expect(next).toHaveBeenCalled();
        expect(res.status).not.toHaveBeenCalled();
    });
});
