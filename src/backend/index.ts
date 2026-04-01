import express from 'express'
import createUser from "./utils/createUser";
import { validateInput } from "./middleware/validateInput";
import { RegisterSchema } from "./schemas/auth.schema";

const app = express();

app.use(express.json(), express.static('src/frontend'))

app.post('/api/register', validateInput(AuthUserSchema), async (req, res) => {
    try {
        const { login, password } = req.body;
        await createUser({ login, password });
        return res.status(201).json({ message: 'User created successfully.' });
    } catch (error: any) {
        if (error.code === 'P2002') {
            return res.status(409).json({ error: 'Login is already taken.' });
        }
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
})

app.listen(3000, () => {
    console.log('App running on http://localhost:3000');
});