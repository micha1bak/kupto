import express from 'express';
import cookieParser from 'cookie-parser';
import createUser from "./utils/createUser";
import loginUser from "./utils/loginUser";
import getList from "./utils/getList";
import createList from "./utils/createList";
import addItemToList from "./utils/addItemToList";
import deleteItemFromList from "./utils/deleteItemFromList";
import getProducts from "./utils/getProducts";
import getCategories from "./utils/getCategories";
import createProduct from "./utils/createProduct";
import { validateInput } from "./middleware/validateInput";
import { authMiddleware, AuthRequest } from "./middleware/authMiddleware";
import { AuthUserSchema } from "./schemas/auth.schema";
import { CreateListSchema} from "./schemas/list.schema";
import { AddItemSchema } from "./schemas/item.schema";
import { CreateProductSchema } from "./schemas/product.schema";

const app = express();

app.use(express.json());
app.use(express.static('src/frontend'));
app.use(cookieParser());

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
});

app.post('/api/login', validateInput(AuthUserSchema), async (req, res) => {
    try {
        const { login, password } = req.body;
        const jwt = await loginUser({ login, password });
        res.cookie('jwt', jwt, {
            httpOnly: true,
            sameSite: 'strict',
            maxAge: 30 * 24 * 60 * 60 * 1000
        });
        return res.status(200).json({ message: 'User logged in successfully.'});
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.use(authMiddleware);

app.post('/api/list', validateInput(CreateListSchema), async (req: AuthRequest, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({error: "User does not exist."});
        }
        const ownerId = req.user.userId;
        const { name } = req.body;
        const newList = await createList({ ownerId, name });
        return res.status(201).json(newList);
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.get('/api/list', async (req: AuthRequest, res)=> {
   try {
       if (!req.user) {
           return res.status(401).json({error: "User does not exist."});
       }
       const list = await getList(req.user.userId);
       return res.status(200).json(list);
   } catch (error: any) {
       console.error(error);
       return res.status(500).json({ error: 'Internal server error.' });
   }
});

app.post('/api/list/item', validateInput(AddItemSchema), async (req: AuthRequest, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({error: "User does not exist."});
        }
        const { productId, quantity } = req.body;
        const result = await addItemToList({
            userId: req.user.userId,
            productId,
            quantity
        });
        return res.status(201).json(result);
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.delete('/api/list/item/:productId', async (req: AuthRequest, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({error: "User does not exist."});
        }
        const productId = parseInt(req.params.productId);
        if (isNaN(productId)) {
            return res.status(400).json({ error: "Invalid product ID" });
        }
        const result = await deleteItemFromList({
            userId: req.user.userId,
            productId
        });
        return res.status(200).json(result);
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.get('/api/products', async (req: AuthRequest, res) => {
    try {
        const products = await getProducts();
        return res.status(200).json(products);
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.post('/api/products', validateInput(CreateProductSchema), async (req: AuthRequest, res) => {
    try {
        const { categoryId, name } = req.body;
        const product = await createProduct({ categoryId, name });
        return res.status(201).json(product);
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.get('/api/categories', async (req: AuthRequest, res) => {
    try {
        const categories = await getCategories();
        return res.status(200).json(categories);
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.listen(3000, () => {
    console.log('App running on http://localhost:3000');
});
