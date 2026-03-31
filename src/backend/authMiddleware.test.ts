import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import authMiddleware, { AuthRequest } from './authMiddleware';
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
            headers: {}
        };
        res = {
            status: jest.fn().mockReturnThis() as any,
            json: jest.fn().mockReturnThis() as any,
        };
        next = jest.fn() as any;
        jest.clearAllMocks();
    });

    it('powinien zwrócić 401 gdy brakuje nagłówka Authorization', async () => {
        await authMiddleware(req as AuthRequest, res as Response, next);

        expect(res.status).toHaveBeenCalledWith(401);
        expect(res.json).toHaveBeenCalledWith({ error: 'Brak tokena autoryzacji' });
        expect(next).not.toHaveBeenCalled();
    });

    it('powinien zwrócić 401 gdy token jest nieprawidłowy', async () => {
        req.headers!['authorization'] = 'Bearer niepoprawny-token';
        (jwtVerify as jest.Mock).mockRejectedValue(new Error('Invalid token') as never);

        await authMiddleware(req as AuthRequest, res as Response, next);

        expect(res.status).toHaveBeenCalledWith(401);
        expect(res.json).toHaveBeenCalledWith({ error: 'Nieprawidłowy lub wygasły token' });
        expect(next).not.toHaveBeenCalled();
    });

    it('powinien dodać userId do req i wywołać next() dla poprawnego tokena', async () => {
        req.headers!['authorization'] = 'Bearer poprawny-token';
        const mockPayload = { userId: 123 };
        (jwtVerify as jest.Mock).mockResolvedValue({ payload: mockPayload } as never);

        await authMiddleware(req as AuthRequest, res as Response, next);

        expect(req.user).toEqual({ userId: 123 });
        expect(next).toHaveBeenCalled();
        expect(res.status).not.toHaveBeenCalled();
    });
});
