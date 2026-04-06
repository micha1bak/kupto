import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import { authMiddleware, AuthRequest } from './authMiddleware.js';
import { Response, NextFunction } from 'express';
import { verify } from 'jsonwebtoken';

jest.mock('jsonwebtoken', () => ({
    verify: jest.fn(),
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

    it('should return 401 if jwt cookie is missing', () => {
        authMiddleware(req as AuthRequest, res as Response, next);
        expect(res.status).toHaveBeenCalledWith(401);
        expect(res.json).toHaveBeenCalledWith({ error: 'Invalid token' });
        expect(next).not.toHaveBeenCalled();
    });

    it('should return 401 if jwt token is invalid', () => {
        req.cookies!.jwt = 'invalid-token';
        (verify as jest.Mock).mockImplementation(() => { throw new Error('Invalid token'); });
        authMiddleware(req as AuthRequest, res as Response, next);
        expect(res.status).toHaveBeenCalledWith(401);
        expect(res.json).toHaveBeenCalledWith({ error: 'Invalid token' });
        expect(next).not.toHaveBeenCalled();
    });

    it('should add userId to req and call next() for correct jwt cookie', () => {
        req.cookies!.jwt = 'valid-token';
        const mockPayload = { userId: 123 };
        (verify as jest.Mock).mockReturnValue(mockPayload as never);
        authMiddleware(req as AuthRequest, res as Response, next);
        expect(req.user).toEqual({ userId: 123 });
        expect(next).toHaveBeenCalled();
        expect(res.status).not.toHaveBeenCalled();
    });
});
