import { z } from 'zod';

export const AuthUserSchema = z.object({
    body: z.object({
        login: z.string().min(3, "Login is too short").max(20),
        password: z.string().min(8, "Password has to have at least 8 characters")
    }),
});