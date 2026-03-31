import express from 'express'
import { prisma } from './db';

const app = express();

app.listen(3000, () => {
    console.log('App running on http://localhost:3000');
});