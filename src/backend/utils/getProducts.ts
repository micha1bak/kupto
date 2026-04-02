import { prisma } from './db';

export default async function getProducts() {
    const products = await prisma.product.findMany({
        include: {
            category: true
        },
        orderBy: {
            name: 'asc'
        }
    });

    return products.map(p => ({
        id: p.product_id,
        name: p.name,
        category: p.category.name,
        categoryId: p.category_id
    }));
}
