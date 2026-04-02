import { prisma } from './db';

export default async function getAvailableLists(userId: number) {
    const access = await prisma.list_access.findMany({
        where: { user_id: userId },
        include: {
            list: {
                select: {
                    list_id: true,
                    name: true
                }
            }
        }
    });

    return access.map(a => ({
        list_id: a.list.list_id,
        name: a.list.name
    }));
}
