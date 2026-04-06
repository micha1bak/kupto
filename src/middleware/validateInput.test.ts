import { jest, describe, it, expect, beforeEach } from '@jest/globals';
import { validateInput } from "./validateInput.js";
import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';

describe('validateInput middleware', () => {
    let req: Partial<Request>;
    let res: Partial<Response>;
    let next: NextFunction;
    const testSchema = z.object({
        body: z.object({
            username: z.string().min(3),
        }),
    });

    beforeEach(() => {
        req = {
            body: {}
        };
        res = {
            status: jest.fn().mockReturnThis(),
            json: jest.fn().mockReturnThis(),
        } as any;
        next = jest.fn() as any;
    });

    it('should call next() if validation succeeds', async () => {
        req.body = { username: 'testuser' };
        const middleware = validateInput(testSchema as any);
        await middleware(req as Request, res as Response, next);
        expect(next).toHaveBeenCalled();
        expect(res.status).not.toHaveBeenCalled();
    });

    it('should return 400 if validation fails', async () => {
        req.body = { username: 'ab' };
        const middleware = validateInput(testSchema as any);
        await middleware(req as Request, res as Response, next);
        expect(next).not.toHaveBeenCalled();
        expect(res.status).toHaveBeenCalledWith(400);
        expect(res.json).toHaveBeenCalled();
    });

    it('should return 400 if required field is missing', async () => {
        req.body = {};
        const middleware = validateInput(testSchema as any);
        await middleware(req as Request, res as Response, next);
        expect(next).not.toHaveBeenCalled();
        expect(res.status).toHaveBeenCalledWith(400);
    });
});
