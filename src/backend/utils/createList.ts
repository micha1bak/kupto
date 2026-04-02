import { prisma } from './db';

interface CreateList {
    ownerId: number;
    name: string
}

export default async function createList(list: CreateList) {
    return prisma.list.create({
        data: {
            owner_id: list.ownerId,
            name: list.name
        }
    });
}