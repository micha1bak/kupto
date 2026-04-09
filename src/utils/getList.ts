import { prisma } from './db.js';

export default async function getList(userId: number) {
    const user = await prisma.users.findUnique({
        where: { user_id: userId },
        select: { default_list_id: true }
    });

    if (!user || !user.default_list_id) {
        return [];
    }

    const listItems = await prisma.list_item.findMany({
        where: { list_id: user.default_list_id },
        include: {
            product: {
                include: {
                    category: true
                }
            }
        }
    });

    const grouped = listItems.reduce((acc: any, item: any) => {
        const categoryName = item.product.category.name;
        if (!acc[categoryName]) {
            acc[categoryName] = [];
        }
        acc[categoryName].push({
            id: item.product_id,
            name: item.product.name,
            quantity: item.quantity
        });
        return acc;
    }, {});

    return Object.entries(grouped)
        .sort(([a], [b]) => a.localeCompare(b, 'pl'))
        .map(([category, items]) => ({
            category,
            items
        }));
}
