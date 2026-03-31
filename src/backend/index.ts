import express from 'express'
import { prisma } from './db';

const app = express();

app.use(express.static('src/frontend'))

app.listen(3000, () => {
    console.log('App running on http://localhost:3000');
});