import { z } from 'zod';

export const AddItemSchema = z.object({
    body: z.object({
        productId: z.number().int().positive(),
        quantity: z.string().min(1).max(50)
    })
});
