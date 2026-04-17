require('dotenv').config();
const { pool } = require('./server/config/db');

pool.query(`
  SELECT c.name, c.phone, c.loyalty_points, c.total_orders,
  array_agg(item->>'item_name') as past_items
  FROM customers c
  JOIN orders o ON o.customer_id = c.id
  CROSS JOIN LATERAL jsonb_array_elements(o.items) item
  WHERE c.name = 'Aarav Shah'
  GROUP BY c.name, c.phone, c.loyalty_points, c.total_orders
`).then(r => {
  console.log('Customer:', r.rows[0].name);
  console.log('Phone:', r.rows[0].phone);
  console.log('Loyalty Points:', r.rows[0].loyalty_points);
  console.log('Total Orders:', r.rows[0].total_orders);
  console.log('Past Items:', [...new Set(r.rows[0].past_items)]);
  pool.end();
}).catch(e => { console.error(e.message); pool.end(); });