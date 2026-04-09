import { prisma } from './db.js';
import bcrypt from 'bcrypt';

interface CreateUser {
    login: string,
    password: string,
}

export default async function createUser(user: CreateUser) {
    const hashedPassword = await bcrypt.hash(user.password, 10);

    return prisma.$transaction(async (tx: any) => {
        const newUser = await tx.users.create({
            data: {
                login: user.login,
                password: hashedPassword,
            }
        });

        const defaultList = await tx.list.create({
            data: {
                name: 'Moja Lista',
                owner_id: newUser.user_id,
                list_access: {
                    create: {
                        user_id: newUser.user_id
                    }
                }
            }
        });

        return tx.users.update({
            where: { user_id: newUser.user_id },
            data: {
                default_list_id: defaultList.list_id
            }
        });
    });
}
