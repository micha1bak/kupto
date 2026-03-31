const http = require('http');
const fs = require('fs');
const db = require('./db');
const { SignJWT, jwtVerify } = require("jose");
const jwtSecret = new TextEncoder().encode(process.env.JWT_SECRET);
let MAX_PROD_ID;

// TODO: Real-Time Collaboration (WebSockets)

// TODO: Add password hashing

// TODO: Testing with jest

// TODO: Offline Mode (PWA): Supermarkets often have terrible cell service.
//  Make the app work offline using Service Workers and sync to the database once the connection returns.

// TODO: Store list and products in local storage for faster render time.

// TODO: Add loging to file

function getFormatedProductName(s) {
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

function getTokenFromRequest(request) {
    return request.headers['authorization'].split(' ')[1];
}

function getParsedBodyFromRequest(request) {
    return new Promise((resolve, reject) => {
        let body = '';

        request.on('data', chunk => {
            body += chunk.toString();
        })

        request.on('end', () => {
            try {
                if (!body) {
                    return resolve({});
                }
                const parsedBody = JSON.parse(body);
                resolve(parsedBody);
            }
            catch (err) {
                reject(err);
            }
        });

        request.on('error', (err) => {
            reject(err);
        });
    });
}



const server = http.createServer(async (req, res) => {

    console.log(`[REQ]: ${req.method} ${req.url}`);

    const cleanUrl = req.url.split('?')[0];

    if (cleanUrl === '/' && req.method === 'GET') {
        fs.readFile('./index.html', (err, content) => {
            res.writeHead(200, {'Content-Type': 'text/html'});
            res.end(content);
        });
    }
    else if (cleanUrl === '/app.js' && req.method === 'GET') {
        fs.readFile('./app.js', (err, content) => {
            if (err) {
                res.writeHead(404);
                res.end();
            } else {
                res.writeHead(200, {'Content-Type': 'application/javascript'});
                res.end(content);
            }
        });
    }
    else if (cleanUrl === '/style.css' && req.method === 'GET') {
        fs.readFile('./style.css', (err, content) => {
            if (err) {
                res.writeHead(404);
                res.end();
            } else {
                res.writeHead(200, {'Content-Type': 'text/css'});
                res.end(content);
            }
        });
    }
    else if (cleanUrl === '/api/login' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', async () => {
            try {
                const parsedBody = JSON.parse(body);

                const query = `
                   SELECT user_id
                   FROM users u
                   WHERE u.login = $1 AND u.password = $2;
                `;

                const values = [
                    parsedBody.login,
                    parsedBody.password
                ]

                try {
                    const result = await db.query(query, values);

                    if (result.rows.length === 1) {

                        const userId = result.rows[0].user_id;
                        const jwt = await new SignJWT({userId: userId})
                            .setProtectedHeader({alg: 'HS256'})
                            .setIssuedAt()
                            .sign(jwtSecret);

                        res.writeHead(200, {'Content-Type': 'application/json'});
                        res.end(JSON.stringify({token: jwt}));

                    } else {
                        res.writeHead(401, {'Content-Type': 'application/json'});
                        res.end();
                    }

                } catch (err) {
                    console.error('bd login err:', err);
                }

            } catch (err) {
                console.error(err);
            }
        });
    }
    else if (cleanUrl === '/api/list' && req.method === 'GET') {
        try {

            const token = getTokenFromRequest(req);
            let userId;

            try {
                const { payload } =  await jwtVerify(token, jwtSecret);
                userId = payload.userId;
            }
            catch (err) {
                res.writeHead(401);
                return res.end();
            }

            const result = await db.query('SELECT * FROM get_default_list($1)', [userId]);

            const rows = result.rows;

            // Grupowanie
            const grouped = rows.reduce((acc, item) => {
                const cat = item.category;
                if (!acc[cat]) acc[cat] = [];
                acc[cat].push(item);
                return acc;
            }, {});

            // Zamiana na tablicę i opcjonalne sortowanie kategorii alfabetycznie
            const response = Object.entries(grouped)
                .sort(([a], [b]) => a.localeCompare(b, 'pl'))
                .map(([category, items]) => ({ category, items }));
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(response));
        }
        catch (err) {
            res.writeHead(500);
            res.end();
        }
    }
    else if (cleanUrl === '/api/products' && req.method === 'GET') {
        try {

            const token = getTokenFromRequest(req);
            try {
                await jwtVerify(token, jwtSecret);
            }
            catch (err) {
                res.writeHead(401);
                return res.end();
            }

            const result = await db.query(`SELECT * from prod_cat`);

            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(result.rows));

        }
        catch (err) {
            res.writeHead(500);
            res.end();
        }
    }
    else if (cleanUrl === '/api/categories' && req.method === 'GET') {
        try {

            const token = getTokenFromRequest(req);
            try {
                await jwtVerify(token, jwtSecret);
            }
            catch (err) {
                res.writeHead(401);
                return res.end();
            }

            const result = await db.query(`SELECT * from category`);

            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(result.rows));

        }
        catch (err) {
            res.writeHead(500);
            res.end();
        }
    }
    else if (cleanUrl === '/api/list' && req.method === 'POST') {
        try {

            const token = getTokenFromRequest(req);
            let userId;
            let listId;

            try {
                const { payload } = await jwtVerify(token, jwtSecret);
                userId = payload.userId;
            }
            catch (err) {
                res.writeHead(401);
                return res.end();
            }

            try {
                const result = await db.query(`
                    SELECT default_list_id
                    FROM users
                    WHERE user_id = $1
                `, [userId])

                listId = result.rows[0].default_list_id;
                if (!listId) {
                    res.writeHead(401);
                    res.end();
                }

            } catch (err) {
                res.writeHead(400);
                res.end();
            }

            const body = await getParsedBodyFromRequest(req);

            const query = `
                        INSERT INTO list_item (list_id, product_id, quantity)
                        VALUES ($1, $2, $3) RETURNING *;
                    `;

            const values = [
                listId,
                parseInt(body.productId),
                body.quantity || 1,
            ];

            const result = await db.query(query, values);

            res.writeHead(201, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(result.rows[0]));

        }
        catch (err) {
            res.writeHead(500, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({error: 'Error while adding item to list.'}));
        }
    }
    else if (cleanUrl === '/api/products' && req.method === 'POST') {
        try {

            const token = getTokenFromRequest(req);

            try {
                await jwtVerify(token, jwtSecret);
            }
            catch (err) {
                res.writeHead(401);
                return res.end();
            }

            const body = await getParsedBodyFromRequest(req);

            const query = `
                        INSERT INTO product (product_id, category_id, name)
                        VALUES ($1, $2, $3) RETURNING *;
                    `;

            const values = [
                ++MAX_PROD_ID,
                parseInt(body.categoryId) || 100, // 100 -> 'Inne'
                getFormatedProductName(body.name)
            ];

            const result = await db.query(query, values);

            res.writeHead(201, {'Content-Type': 'application/json'});
            res.end(JSON.stringify(result.rows[0]));

        }
        catch (err) {
            MAX_PROD_ID--;
            res.writeHead(500, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({error: 'Error while adding item to list.'}));
        }
    }
    else if (cleanUrl.startsWith('/api/list/') && req.method === 'DELETE') {
        try  {

            const token = getTokenFromRequest(req);
            let userId;

            try {
                const {payload} = await jwtVerify(token, jwtSecret);
                userId = payload.userId;
            }
            catch (err) {
                res.writeHead(401);
                return res.end();
            }

            try {
                const result = await db.query(`
                    SELECT default_list_id
                    FROM users
                    WHERE user_id = $1
                `, [userId])

                listId = result.rows[0].default_list_id;
                if (!listId) {
                    res.writeHead(401);
                    res.end();
                }

            } catch (err) {
                res.writeHead(400);
                res.end();
            }

            const productIdToDeleteFromList = parseInt(req.url.split('/').pop());

            if (isNaN(productIdToDeleteFromList)) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                return res.end();
            }

            const query = `
                DELETE FROM list_item
                WHERE list_id = $1 AND product_id = $2 
                RETURNING *;
            `;

            const values = [listId, productIdToDeleteFromList];

            const result = await db.query(query, values);

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ deletedItem: result.rows[0] }));
        }
        catch (err) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end();
        }
    }
    else if (cleanUrl === '/api/lists' && req.method === 'GET') {
        try  {
            const token = getTokenFromRequest(req);
            let userId;

            try {
                const { payload } = await jwtVerify(token, jwtSecret);
                userId = payload.userId;
            }
            catch (err) {
                res.writeHead(401);
                return res.end();
            }

            const result = await db.query(`
                SELECT la.list_id, l.name 
                FROM list_access la
                JOIN list l on l.list_id = la.list_id
                WHERE user_id = $1;
            `, [userId] );

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ lists: result.rows }));
        }
        catch (err) {
            res.writeHead(500, {'Content-Type': 'application/json'});
            res.end();
        }
    }
    else if (cleanUrl === '/api/lists' && req.method === 'POST') {
        try {
            const token = getTokenFromRequest(req);
            let userId;

            try {
                const { payload } = await jwtVerify(token, jwtSecret);
                userId = payload.userId;
            }
            catch (err) {
                res.writeHead(401);
                return res.end();
            }

            const body = await getParsedBodyFromRequest(req);

            const result = await db.query(`
                UPDATE users 
                SET default_list_id = $1
                WHERE user_id = $2
            `, [body.list_id, userId]);

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ lists: result.rows }));
        }
        catch (err) {
            res.writeHead(500, {'Content-Type': 'application/json'});
            res.end();
        }
    }
    else {
        console.log(`[NO FILE!] url: ${req.url}`);
        res.writeHead(404);
        res.end();
    }

});



db.query("select max(product_id) from product", (err, res) => {
    if (err) {
        console.error('[ERROR] Failed connect to database: ', err.stack);
    }
    MAX_PROD_ID = res.rows[0].max;
})

server.listen(3000, () => console.log('Server listening at http://localhost:3000'));
