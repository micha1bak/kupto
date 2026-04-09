import { prisma } from './db.js';

export default async function getAvailableLists(userId: number) {
    const access = await prisma.list_access.findMany({
        where: { user_id: userId },
        include: {
            list: {
                select: {
                    list_id: true,
                    owner_id: true,
                    name: true
                }
            }
        }
    });

    return access.map((a: any) => ({
        list_id: a.list.list_id,
        can_manage_access: a.list.owner_id === userId,
        name: a.list.name
    }));
}
