import { Request, Response, NextFunction } from 'express'
import { ZodAny } from 'zod';

export const validateInput = (schema: ZodAny) =>
    async (req: Request, res: Response, next: NextFunction) => {
        try {
            await schema.parseAsync({ body: req.body });
            return next();
        } catch (error) {
            return res.status(400).json(error);
        }
    };
