import { prisma } from './db';
import bcrypt from 'bcrypt';

interface CreateUser {
    login: string,
    password: string,
}

export default async function createUser(user: CreateUser) {
    const hashedPassword = await bcrypt.hash(user.password, 10);
    return prisma.users.create({
        data: {
            login: user.login,
            password: hashedPassword,
        }
    });
}

