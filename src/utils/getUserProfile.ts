import { prisma } from './db.js';

export default async function getUserProfile(userId: number) {
    return prisma.users.findUniqueOrThrow({
        where: {user_id: userId},
        select: {
            login: true,
            default_list_id: true
        }
    });
}
