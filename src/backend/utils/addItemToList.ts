import { prisma } from './db';

interface AddItem {
    userId: number;
    productId: number;
    quantity: string;
}

export default async function addItemToList(data: AddItem) {
    const user = await prisma.users.findUniqueOrThrow({
        where: { user_id: data.userId },
        select: { default_list_id: true }
    });

    if (!user.default_list_id) {
        throw new Error('User has no default list');
    }

    return prisma.list_item.upsert({
        where: {
            list_id_product_id: {
                list_id: user.default_list_id,
                product_id: data.productId
            }
        },
        update: {
            quantity: data.quantity
        },
        create: {
            list_id: user.default_list_id,
            product_id: data.productId,
            quantity: data.quantity
        }
    });
}
