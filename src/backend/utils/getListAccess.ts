import { prisma } from './db';

export default async function getListAccess(listId: number, requesterId: number) {
    const list = await prisma.list.findUnique({
        where: { list_id: listId },
        include: {
            users_list_owner_idTousers: {
                select: {
                    user_id: true,
                    login: true
                }
            },
            list_access: {
                include: {
                    users: {
                        select: {
                            user_id: true,
                            login: true
                        }
                    }
                }
            }
        }
    });

    if (!list) {
        throw new Error('List not found');
    }

    const isOwner = list.owner_id === requesterId;
    const isSharedWithMe = list.list_access.some(access => access.user_id === requesterId);

    if (!isOwner && !isSharedWithMe) {
        throw new Error('Access denied');
    }

    return {
        owner: {
            user_id: list.users_list_owner_idTousers.user_id,
            login: list.users_list_owner_idTousers.login
        },
        shared_with: list.list_access
            .filter(access => access.user_id !== list.owner_id)
            .map(access => ({
                user_id: access.users.user_id,
                login: access.users.login
            })),
        is_owner: isOwner
    };
}
