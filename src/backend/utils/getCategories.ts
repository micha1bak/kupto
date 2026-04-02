import { prisma } from './db';

export default async function getCategories() {
    return prisma.category.findMany({
        orderBy: {
            name: 'asc'
        }
    });
}
