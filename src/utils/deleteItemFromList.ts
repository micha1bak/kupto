import { prisma } from './db.js';

interface DeleteItem {
    userId: number;
    productId: number;
}

export default async function deleteItemFromList(data: DeleteItem) {
    const user = await prisma.users.findUniqueOrThrow({
        where: { user_id: data.userId },
        select: { default_list_id: true }
    });

    if (!user.default_list_id) {
        throw new Error('User has no default list');
    }

    return prisma.list_item.delete({
        where: {
            list_id_product_id: {
                list_id: user.default_list_id,
                product_id: data.productId
            }
        }
    });
}
