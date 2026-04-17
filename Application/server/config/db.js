const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// Create connection pool using .env values
const pool = new Pool({
  host:     process.env.DB_HOST     || 'localhost',
  port:     parseInt(process.env.DB_PORT) || 5432,
  database: process.env.DB_NAME     || 'bitekaro',
  user:     process.env.DB_USER     || 'postgres',
  password: String(process.env.DB_PASSWORD || 'root'),
});

// Test connection
pool.query('SELECT NOW()')
  .then(() => console.log('PostgreSQL connected successfully'))
  .catch((err) => console.error('PostgreSQL connection error:', err.message));

// Query helper function
const query = (text, params) => pool.query(text, params);

// Initialize database — run schema SQL to create all tables
const initDB = async () => {
  try {
    const schemaPath = path.join(__dirname, '..', 'db', 'schema.sql');
    const schema = fs.readFileSync(schemaPath, 'utf-8');
    await pool.query(schema);
    console.log('PostgreSQL connected and schema initialized');
  } catch (err) {
    console.error('Error initializing database schema:', err.message);
    throw err;
  }
};

module.exports = { pool, query, initDB };
