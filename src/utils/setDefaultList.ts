import { prisma } from './db.js';

interface SetDefaultList {
    userId: number;
    listId: number;
}

export default async function setDefaultList(data: SetDefaultList) {
    const access = await prisma.list_access.findUniqueOrThrow({
        where: {
            list_id_user_id: {
                list_id: data.listId,
                user_id: data.userId
            }
        }
    });

    return prisma.users.update({
        where: { user_id: data.userId },
        data: { default_list_id: access.list_id }
    });
}
