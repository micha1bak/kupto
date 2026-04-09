import { z } from 'zod';

export const SetDefaultListSchema = z.object({
    body: z.object({
        listId: z.number().int().positive()
    })
});
