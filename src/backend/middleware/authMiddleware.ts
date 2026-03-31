import { Request, Response, NextFunction } from "express";
import { jwtVerify } from "jose";

export interface AuthRequest extends Request {
    user?: {
        userId: number;
    };
}

const jwtSecret = new TextEncoder().encode(process.env.JWT_SECRET);

export default async function authMiddleware(req: AuthRequest, res: Response, next: NextFunction) {
    const authHeader = req.headers['authorization'];
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Brak tokena autoryzacji' });
    }
    const token = authHeader.split(' ')[1];
    try {
        const { payload } = await jwtVerify(token, jwtSecret);
        req.user = {
            userId: payload.userId as number
        };
        next();
    } catch (err) {
        console.error('Błąd weryfikacji tokena:', err);
        return res.status(401).json({ error: 'Nieprawidłowy lub wygasły token' });
    }
}