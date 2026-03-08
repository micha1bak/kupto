const http = require('http');
const fs = require('fs');
const path = require('path');
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
                res.end('Nie znaleziono pliku');
            } else {
                res.writeHead(200, { 'Content-Type': 'application/javascript' });
                res.end(content);
            }
        });

    } else if (req.url === '/style.css' && req.method === 'GET') {
        fs.readFile('./style.css', (err, content) => {
            if (err) {
                res.writeHead(404);
                res.end('Nie znaleziono pliku');
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
            console.error('Błąd bazy danych:', err);
            res.writeHead(500);
            res.end('Błąd serwera');
        }
        return;
    } else if (req.url === '/api/catalog' && req.method === 'GET') {
        try {
            const result = await db.query(`SELECT * from prod_cat`);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result.rows));
        } catch (err) {
            res.writeHead(500);
            res.end();
        }
        return;
    }
});

server.listen(3000, () => console.log('Serwer API śmiga na http://localhost:3000'));
