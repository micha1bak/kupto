import { prisma } from './db';

export default async function addListAccess(listId: number, login: string, requesterId: number) {
    const list = await prisma.list.findUnique({
        where: { list_id: listId },
        select: { owner_id: true }
    });

    if (!list) {
        throw new Error('List not found');
    }

    if (list.owner_id !== requesterId) {
        throw new Error('Only the owner can manage access');
    }

    const userToAdd = await prisma.users.findUnique({
        where: { login }
    });

    if (!userToAdd) {
        throw new Error('User not found');
    }

    if (userToAdd.user_id === list.owner_id) {
        throw new Error('User is already the owner of this list');
    }

    try {
        await prisma.list_access.create({
            data: {
                list_id: listId,
                user_id: userToAdd.user_id
            }
        });
    } catch (error: any) {
        if (error.code === 'P2002') {
            throw new Error('User already has access to this list');
        }
        throw error;
    }

    return {
        user_id: userToAdd.user_id,
        login: userToAdd.login
    };
}
