import { z } from 'zod';

export const CreateProductSchema = z.object({
    body: z.object({
        categoryId: z.number().int().positive(),
        name: z.string().min(1).max(100)
    })
});
