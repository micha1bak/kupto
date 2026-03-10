const http = require('http');
const fs = require('fs');
const db = require('./db');

// TODO: Formatuj dane po stronie serwera tak, aby lista zakupów była już posortowana
//       wg. kategorii.



const server = http.createServer(async (req, res) => {
    if (req.url === '/' && req.method === 'GET') {
        fs.readFile('./index.html', (err, content) => {
            res.writeHead(200, {'Content-Type': 'text/html'});
            res.end(content);
        });
    } else if (req.url === '/app.js' && req.method === 'GET') {
        fs.readFile('./app.js', (err, content) => {
            if (err) {
                res.writeHead(404);
                res.end();
            } else {
                res.writeHead(200, {'Content-Type': 'application/javascript'});
                res.end(content);
            }
        });
    } else if (req.url === '/style.css' && req.method === 'GET') {
        fs.readFile('./style.css', (err, content) => {
            if (err) {
                res.writeHead(404);
                res.end();
            } else {
                res.writeHead(200, {'Content-Type': 'text/css'});
                res.end(content);
            }
        });
    } else if (req.url === '/api/list' && req.method === 'GET') {
        try {
            const result = await db.query('SELECT * FROM full_shopping_list');
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(result.rows));
        } catch (err) {
            res.writeHead(500);
            res.end();
        }
    } else if (req.url === '/api/products' && req.method === 'GET') {
        try {
            const result = await db.query(`SELECT * from prod_cat`);
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(result.rows));
        } catch (err) {
            res.writeHead(500);
            res.end();
        }
    } else if (req.url === '/api/categories' && req.method === 'GET') {
        try {
            const result = await db.query(`SELECT *
                                           from category`);
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(result.rows));
        } catch (err) {
            res.writeHead(500);
            res.end();
        }
    } else if (req.url === '/api/list' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', async () => {
            try {
                const parsedBody = JSON.parse(body);
                const query = `
                    INSERT INTO shopping_list (product_id, added_by_user_id, quantity)
                    VALUES ($1, $2, $3) RETURNING *;
                `;
                const values = [
                    parseInt(parsedBody.productId),
                    parseInt(parsedBody.addedByUserId),
                    parsedBody.quantity || 1,
                ];
                const result = await db.query(query, values);
                res.writeHead(201, {'Content-Type': 'application/json'});
                res.end(JSON.stringify(result.rows[0]));

            } catch (err) {
                res.writeHead(500, {'Content-Type': 'application/json'});
                res.end(JSON.stringify({error: 'Error while adding item to list.'}));
            }
        });
    } else if (req.url === '/api/products' && req.method === 'POST') {

    } else if (req.url.startsWith('/api/list/') && req.method === 'DELETE') {
        try {
            const idString = req.url.split('/').pop();
            const productId = parseInt(idString);

            if (isNaN(productId)) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                return res.end();
            }

            const query = `
                DELETE FROM shopping_list 
                WHERE product_id = $1 
                RETURNING *;
            `;
            const values = [productId];
            const result = await db.query(query, values);

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                deletedItem: result.rows[0]
            }));

        } catch (err) {
            console.error(err);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end();
        }
    }
});

server.listen(3000, () => console.log('Server listening at http://localhost:3000'));
