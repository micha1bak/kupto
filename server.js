const http = require('http');
const fs = require('fs');
const db = require('./db');
const {SignJWT} = require("jose");
let MAX_PROD_ID;

// TODO: Real-Time Collaboration (WebSockets): Make it so you and your girlfriend
//  can have the app open on different phones, and if she checks off "Milk"
//  it instantly checks off on your screen without refreshing.

// TODO: Security & Auth: Implement secure login (JWT or session-based)
//  and password hashing (bcrypt). Show that you know how to protect user data.

// Podsumowanie zmian architektonicznych w pigułce:
// 1. `app.js`: Usunięcie const userId = 1. Dodanie panelu logowania. Zmiana każdej funkcji wywołującej fetch,
//      aby pobierała JWT z pamięci przeglądarki i wstrzykiwała go do nagłówków Authorization.
// 2. `server.js`: Implementacja endopointu /api/login dla logowania. Zabezpieczenie obecnych endopintów
//      (sprawdzanie nagłówka przez jwtVerify). Używanie zdekodowanego z tokenu id użytkownika do modyfikacji bazy danych,
//      zamiast polegania na danych wysłanych przez frontend.
// 3.  Obsługa błędów: app.js musi reagować na błędy HTTP statusu 401 i 403 przez wylogowanie użytkownika
//      (np. czyszczenie localStorage i pokazanie okna logowania) — oznacza to, że sesja (JWT) wygasła.

// TODO: Testing: Write unit and integration tests (using a tool like Jest).
//  Junior devs who know how to write tests are unicorns.

// TODO: Offline Mode (PWA): Supermarkets often have terrible cell service.
//  Make the app work offline using Service Workers and sync to the database once the connection returns.

// TODO: Store list and products in local storage for faster render time.

const getFormatedProductName = (s) => {
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
};

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
    } else if (req.url === '/api/login' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', async () => {
            try {
                console.log(body);
                const parsedBody = JSON.parse(body);

                const query = `
                   SELECT validate_user($1, $2);
                `;
                const values = [
                    parsedBody.login,
                    parsedBody.password
                ]
                try {
                    const result = await db.query(query, values);
                    const is_valid_user = parseInt(result.rows[0].validate_user);
                    if (is_valid_user) {
                        const secret = new TextEncoder().encode('secret');
                        const jwt = await new SignJWT({userId: '1'})
                            .setProtectedHeader({alg: 'HS256'})
                            .setIssuedAt()
                            .sign(secret);
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
    } else if (req.url === '/api/list' && req.method === 'GET') {
        try {
            const result = await db.query('SELECT * FROM full_shopping_list');

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
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', async () => {
            try {
                const parsedBody = JSON.parse(body);
                const query = `
                    INSERT INTO product (product_id, category, name)
                    VALUES ($1, $2, $3) RETURNING *;
                `;
                const values = [
                    ++MAX_PROD_ID,
                    parseInt(parsedBody.categoryId) || 100, // 100 -> 'Inne'
                    getFormatedProductName(parsedBody.name)
                ];

                const result = await db.query(query, values);

                res.writeHead(201, {'Content-Type': 'application/json'});
                res.end(JSON.stringify(result.rows[0]));

            } catch (err) {
                MAX_PROD_ID--;
                res.writeHead(500, {'Content-Type': 'application/json'});
                res.end(JSON.stringify({error: 'Error while adding product to db.'}));
            }
        });
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

db.query("select max(product_id) from product", (err, res) => {
    if (err) {
        console.error('[ERROR] Failed connect to database: ', err.stack);
    }
    MAX_PROD_ID = res.rows[0].max;
})

server.listen(3000, () => console.log('Server listening at http://localhost:3000'));
