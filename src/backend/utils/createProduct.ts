import { prisma } from './db';
import { formatProductName } from './productUtils';

interface CreateProduct {
    categoryId: number;
    name: string;
}

export default async function createProduct(data: CreateProduct) {
    const formattedName = formatProductName(data.name);

    return prisma.product.create({
        data: {
            category_id: data.categoryId,
            name: formattedName
        }
    });
}
