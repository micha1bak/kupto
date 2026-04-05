import { z } from 'zod';

export const CreateListSchema = z.object({
    body: z.object({
        name: z.string().min(1, "Name has to be longer than 1 letter").max(50),
    }),
});

export const AddListAccessSchema = z.object({
    body: z.object({
        login: z.string().min(1, "Login is required"),
    }),
});