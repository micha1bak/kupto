import { prisma } from './db';
import bcrypt from 'bcrypt';
import * as jose from 'jose';
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
    const secret = new TextEncoder().encode(process.env.JWT_SECRET);
    return await new jose.SignJWT({userId: result.user_id})
        .setProtectedHeader({alg: 'HS256'})
        .setExpirationTime('30d')
        .sign(secret);
}
