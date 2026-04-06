import { prisma } from './db.js';

export default async function removeListAccess(listId: number, targetUserId: number, requesterId: number) {
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

    if (targetUserId === list.owner_id) {
        throw new Error('Cannot remove access from the owner');
    }

    try {
        await prisma.list_access.delete({
            where: {
                list_id_user_id: {
                    list_id: listId,
                    user_id: targetUserId
                }
            }
        });
    } catch (error: any) {
        if (error.code === 'P2025') {
            throw new Error('User does not have access to this list');
        }
        throw error;
    }

    return { success: true };
}
