import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";

export interface AuthRequest extends Request {
    user?: {
        userId: number;
    };
}

const jwtSecret = process.env.JWT_SECRET || "";

export function authMiddleware(req: AuthRequest, res: Response, next: NextFunction) {
    const token = req.cookies.jwt;
    if (!token) return res.status(401).json({error: "Invalid token"});
    try {
        const decoded = jwt.verify(token, jwtSecret) as { userId: number };
        req.user = {
            userId: decoded.userId
        };
        next();
    } catch (err) {
        return res.status(401).json({ error: 'Invalid token' });
    }
}