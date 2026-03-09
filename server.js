const http = require('http');
const fs = require('fs');
const db = require('./db');

const server = http.createServer(async (req, res) => {
    if (req.url === '/' && req.method === 'GET') {
        fs.readFile('./index.html', (err, content) => {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(content);
        });
    } else if (req.url === '/app.js' && req.method === 'GET') {
        fs.readFile('./app.js', (err, content) => {
            if (err) {
                res.writeHead(404);
                res.end();
            } else {
                res.writeHead(200, { 'Content-Type': 'application/javascript' });
                res.end(content);
            }
        });
    } else if (req.url === '/style.css' && req.method === 'GET') {
        fs.readFile('./style.css', (err, content) => {
            if (err) {
                res.writeHead(404);
                res.end();
            } else {
                res.writeHead(200, { 'Content-Type': 'text/css' });
                res.end(content);
            }
        });
    } else if (req.url === '/api/list' && req.method === 'GET') {
        try {
            const result = await db.query('SELECT * FROM full_shopping_list');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result.rows));
        } catch (err) {
            res.writeHead(500);
            res.end();
        }
    } else if (req.url === '/api/products' && req.method === 'GET') {
        try {
            const result = await db.query(`SELECT * from prod_cat`);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result.rows));
        } catch (err) {
            res.writeHead(500);
            res.end();
        }
    } else if (req.url === '/api/list' && req.method === 'POST') {
        // 1. Odbieranie strumienia danych (bo req.body nie istnieje)
        let body = '';

        req.on('data', chunk => {
            body += chunk.toString(); // Sklejamy fragmenty paczki
        });

        req.on('end', async () => {
            try {
                // Zamieniamy odebrany tekst na obiekt JavaScript
                const parsedBody = JSON.parse(body);

                console.log('[DEBUG] Otrzymane dane z frontendu:', parsedBody);

                // 2. Bezpieczne zapytanie SQL (Parametryzacja + Jawne nazwy kolumn + RETURNING)
                const query = `
                    INSERT INTO shopping_list (product_id, added_by_user_id, quantity) 
                    VALUES ($1, $2, $3)
                    RETURNING *;
                `;

                // Wartości podpinamy w osobnej tablicy (kolejność musi pasować do $1, $2, $3)
                const values = [
                    parseInt(parsedBody.productId),
                    parseInt(parsedBody.addedByUserId),
                    parseInt(parsedBody.quantity) || 1,
                ];

                // 3. Wykonanie zapytania
                const result = await db.query(query, values);

                // 4. Odsyłanie sukcesu do frontendu
                res.writeHead(201, { 'Content-Type': 'application/json' });
                // Odsyłamy tylko pierwszy wiersz, bo dodaliśmy tylko jeden produkt
                res.end(JSON.stringify(result.rows[0]));

            } catch (err) {
                console.error('[BŁĄD] /api/add-item:', err);

                // Odsyłamy czytelny błąd, żeby frontend wiedział, że coś poszło nie tak
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Błąd podczas dodawania produktu do listy.' }));
            }
        });
    }
});

server.listen(3000, () => console.log('Server listening at http://localhost:3000'));
