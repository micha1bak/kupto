import { Request, Response, NextFunction } from "express";
import { jwtVerify } from "jose";

export interface AuthRequest extends Request {
    user?: {
        userId: number;
    };
}

const jwtSecret = new TextEncoder().encode(process.env.JWT_SECRET);

export default async function authMiddleware(req: AuthRequest, res: Response, next: NextFunction) {
    const jwt = req.cookies.jwt;
    if (!jwt) return res.status(401).json({error: "Invalid token"});
    try {
        const { payload } = await jwtVerify(jwt, jwtSecret);
        req.user = {
            userId: payload.userId as number
        };
        next();
    } catch (err) {
        return res.status(401).json({ error: 'Invalid token' });
    }
}