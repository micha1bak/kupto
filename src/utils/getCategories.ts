import { prisma } from './db.js';

export default async function getCategories() {
    return prisma.category.findMany({
        orderBy: {
            name: 'asc'
        }
    });
}
