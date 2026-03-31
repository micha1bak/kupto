require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
    user: process.env.DB_USER,
    host: process.env.DB_HOST,
    database: process.env.DB_NAME,
    password: process.env.DB_PASSWORD,
    port: process.env.DB_PORT,
});

// connection test
pool.query('SELECT NOW()', (err, res) => {
    if (err) {
        console.error('[ERROR] Failed connect to database: ', err.stack);
    } else {
        console.log('Connencted to database. Current time: ', res.rows[0].now);
    }
});

module.exports = {
    query: (text, params) => pool.query(text, params),
};