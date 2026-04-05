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
import getAvailableLists from "./utils/getAvailableLists";
import getListAccess from "./utils/getListAccess";
import addListAccess from "./utils/addListAccess";
import removeListAccess from "./utils/removeListAccess";
import setDefaultList from "./utils/setDefaultList";
import getUserProfile from "./utils/getUserProfile";
import { validateInput } from "./middleware/validateInput";
import { authMiddleware, AuthRequest } from "./middleware/authMiddleware";
import { AuthUserSchema } from "./schemas/auth.schema";
import { CreateListSchema, AddListAccessSchema} from "./schemas/list.schema";
import { AddItemSchema } from "./schemas/item.schema";
import { CreateProductSchema } from "./schemas/product.schema";
import { SetDefaultListSchema } from "./schemas/user.schema";

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
        return res.status(401).json({ error: 'Invalid login or password' });
    }
});

app.post('/api/logout', (req, res) => {
    res.clearCookie('jwt');
    return res.status(200).json({ message: 'Logged out successfully.' });
});

app.use(authMiddleware);

app.get('/api/users/me', async (req: AuthRequest, res) => {
    try {
        if (!req.user) return res.status(401).json({error: "Not authenticated"});
        const profile = await getUserProfile(req.user.userId);
        return res.status(200).json(profile);
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.post('/api/lists', validateInput(CreateListSchema), async (req: AuthRequest, res) => {
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

app.get('/api/lists', async (req: AuthRequest, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({error: "User does not exist."});
        }
        const lists = await getAvailableLists(req.user.userId);
        return res.status(200).json(lists);
    } catch (error: any) {
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.get('/api/lists/:id/access', async (req: AuthRequest, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({ error: "User does not exist." });
        }
        const listId = parseInt(req.params.id);
        if (isNaN(listId)) {
            return res.status(400).json({ error: "Invalid list ID" });
        }
        const accessDetails = await getListAccess(listId, req.user.userId);
        return res.status(200).json(accessDetails);
    } catch (error: any) {
        if (error.message === 'List not found') {
            return res.status(404).json({ error: error.message });
        }
        if (error.message === 'Access denied') {
            return res.status(403).json({ error: error.message });
        }
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.post('/api/lists/:id/access', validateInput(AddListAccessSchema), async (req: AuthRequest, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({ error: "User does not exist." });
        }
        const listId = parseInt(req.params.id);
        if (isNaN(listId)) {
            return res.status(400).json({ error: "Invalid list ID" });
        }
        const { login } = req.body;
        const result = await addListAccess(listId, login, req.user.userId);
        return res.status(201).json(result);
    } catch (error: any) {
        if (error.message === 'List not found' || error.message === 'User not found') {
            return res.status(404).json({ error: error.message });
        }
        if (error.message === 'Only the owner can manage access') {
            return res.status(403).json({ error: error.message });
        }
        if (error.message === 'User is already the owner of this list' || error.message === 'User already has access to this list') {
            return res.status(409).json({ error: error.message });
        }
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.delete('/api/lists/:id/access/:userId', async (req: AuthRequest, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({ error: "User does not exist." });
        }
        const listId = parseInt(req.params.id);
        const targetUserId = parseInt(req.params.userId);
        if (isNaN(listId) || isNaN(targetUserId)) {
            return res.status(400).json({ error: "Invalid list ID or user ID" });
        }
        const result = await removeListAccess(listId, targetUserId, req.user.userId);
        return res.status(200).json(result);
    } catch (error: any) {
        if (error.message === 'List not found' || error.message === 'User does not have access to this list') {
            return res.status(404).json({ error: error.message });
        }
        if (error.message === 'Only the owner can manage access' || error.message === 'Cannot remove access from the owner') {
            return res.status(403).json({ error: error.message });
        }
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.put('/api/users/default-list', validateInput(SetDefaultListSchema), async (req: AuthRequest, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({error: "User does not exist."});
        }
        const { listId } = req.body;
        await setDefaultList({
            userId: req.user.userId,
            listId
        });
        return res.status(200).json({ message: "Default list updated successfully" });
    } catch (error: any) {
        if (error.code === 'P2025') {
            return res.status(403).json({ error: "Access denied or list not found" });
        }
        console.error(error);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

app.listen(3000, () => {
    console.log('App running on http://localhost:3000');
});
