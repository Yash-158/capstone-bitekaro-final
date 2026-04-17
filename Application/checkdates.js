require('dotenv').config();
const { pool } = require('./server/config/db');

pool.query(`
  SELECT DATE(created_at AT TIME ZONE 'Asia/Kolkata') as date_ist,
         COUNT(*) as orders,
         SUM(total) as revenue
  FROM orders
  GROUP BY DATE(created_at AT TIME ZONE 'Asia/Kolkata')
  ORDER BY date_ist DESC
  LIMIT 10
`).then(r => {
  console.table(r.rows);
  pool.end();
}).catch(e => {
  console.error(e.message);
  pool.end();
});