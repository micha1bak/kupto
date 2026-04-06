import { prisma } from './db.js';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import 'dotenv/config';

interface LoginUser {
    login: string;
    password: string;
}

export default async function loginUser(user: LoginUser) {
    const result = await prisma.users.findUniqueOrThrow({
        where: {
            login: user.login
        }
    });
    if (!await bcrypt.compare(user.password, result.password)) {
        throw new Error('Invalid password');
    }
    const secret = process.env.JWT_SECRET || "";
    return jwt.sign(
        { userId: result.user_id },
        secret,
        {
            algorithm: 'HS256',
            expiresIn: '30d'
        }
    );
}
