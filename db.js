const { Pool } = require('pg');

const pool = new Pool({
    user: 'postgres',
    host: '172.27.32.1',
    database: 'kupto_dev',
    password: 'postgres',
    port: 5432,
});

// pool.query('select * from full_shopping_list', (err, res) => {
//     if (err) {
//         console.error('BŁĄD POŁĄCZENIA Z BAZĄ:', err.stack);
//     } else {
//         console.log(res.rows);
//     }
// })

module.exports = {
    query: (text, params) => pool.query(text, params),
};