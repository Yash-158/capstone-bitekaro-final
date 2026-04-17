const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');
const { query } = require('../config/db');
const authenticateToken = require('../middleware/auth');
const { createOrder: createRazorpayOrder, verifyPayment } = require('../services/razorpay');

// POST /api/orders — create a new order
router.post('/', async (req, res, next) => {
  try {
    const {
      customer_id, items, subtotal, discount, total,
      payment_method, payment_status, payment_id, mood, special_instructions
    } = req.body;

    if (!items || !Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ error: 'items array is required and cannot be empty.' });
    }
    if (subtotal === undefined || total === undefined) {
      return res.status(400).json({ error: 'subtotal and total are required.' });
    }

    const orderId = uuidv4();

    // Generate token number: today's order count + 1
    const countResult = await query(
      "SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURRENT_DATE"
    );
    const tokenNumber = parseInt(countResult.rows[0].count) + 1;

    // Insert order
    const orderResult = await query(
      `INSERT INTO orders (id, customer_id, items, subtotal, discount, total, payment_method, payment_id, payment_status, mood, token_number, special_instructions)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING *`,
      [orderId, customer_id || null, JSON.stringify(items), subtotal, discount || 0, total,
       payment_method || 'cash', payment_id || null, payment_status || 'pending',
       mood || null, tokenNumber, special_instructions || null]
    );

    // Decrement inventory for each item
    for (const item of items) {
      await query(
        'UPDATE menu_items SET inventory_count = GREATEST(inventory_count - $1, 0) WHERE id = $2',
        [item.quantity || 1, item.item_id]
      );
    }

    // If customer_id: award loyalty points and update stats
    if (customer_id) {
      const pointsEarned = Math.floor(total / 10);

      await query(
        `UPDATE customers SET total_orders = total_orders + 1, total_spent = total_spent + $1,
         loyalty_points = loyalty_points + $2, last_visit = NOW() WHERE id = $3`,
        [total, pointsEarned, customer_id]
      );

      if (pointsEarned > 0) {
        await query(
          `INSERT INTO loyalty_transactions (customer_id, order_id, points_change, transaction_type, description)
           VALUES ($1,$2,$3,$4,$5)`,
          [customer_id, orderId, pointsEarned, 'earned', `Earned ${pointsEarned} points on order #${tokenNumber}`]
        );
      }
    }

    const order = orderResult.rows[0];

    // Emit real-time event
    if (global.io) global.io.emit('new_order', order);

    res.status(201).json({ success: true, order });
  } catch (err) { next(err); }
});

// GET /api/orders (protected) — paginated
router.get('/', authenticateToken, async (req, res, next) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 20;
    const offset = (page - 1) * limit;
    const { status, date } = req.query;

    let sql = 'SELECT * FROM orders WHERE 1=1';
    const params = [];
    let idx = 1;

    if (status) { sql += ` AND status = $${idx}`; params.push(status); idx++; }
    if (date) { sql += ` AND DATE(created_at) = $${idx}`; params.push(date); idx++; }

    const countResult = await query(sql.replace('SELECT *', 'SELECT COUNT(*)'), params);
    const totalOrders = parseInt(countResult.rows[0].count);

    sql += ` ORDER BY created_at DESC LIMIT $${idx} OFFSET $${idx + 1}`;
    params.push(limit, offset);

    const result = await query(sql, params);
    res.json({
      success: true,
      orders: result.rows,
      pagination: { page, limit, total: totalOrders, pages: Math.ceil(totalOrders / limit) }
    });
  } catch (err) { next(err); }
});

// GET /api/orders/today (protected)
router.get('/today', authenticateToken, async (req, res, next) => {
  try {
    const result = await query(
      "SELECT * FROM orders WHERE DATE(created_at) = CURRENT_DATE ORDER BY created_at DESC"
    );
    res.json({ success: true, orders: result.rows });
  } catch (err) { next(err); }
});

// GET /api/orders/history/:phone — order history for recommendation engine
router.get('/history/:phone', async (req, res, next) => {
  try {
    const custResult = await query('SELECT * FROM customers WHERE phone = $1', [req.params.phone]);
    if (custResult.rows.length === 0) {
      return res.json({ exists: false, order_history: [] });
    }

    const customer = custResult.rows[0];
    const ordersResult = await query(
      'SELECT items FROM orders WHERE customer_id = $1 ORDER BY created_at DESC', [customer.id]
    );

    // Extract all item_ids from items JSONB across all orders
    const order_history = [];
    for (const row of ordersResult.rows) {
      const items = typeof row.items === 'string' ? JSON.parse(row.items) : row.items;
      if (Array.isArray(items)) {
        for (const item of items) {
          order_history.push(item.item_id);
        }
      }
    }

    res.json({
      exists: true,
      customer: { id: customer.id, name: customer.name, phone: customer.phone, loyalty_points: customer.loyalty_points },
      order_history
    });
  } catch (err) { next(err); }
});

// GET /api/orders/:id
router.get('/:id', async (req, res, next) => {
  try {
    const result = await query('SELECT * FROM orders WHERE id = $1', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Order not found' });
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

// PATCH /api/orders/:id/status (protected)
router.patch('/:id/status', authenticateToken, async (req, res, next) => {
  try {
    const { status } = req.body;
    const validStatuses = ['received', 'preparing', 'ready', 'completed', 'cancelled'];
    if (!status || !validStatuses.includes(status)) {
      return res.status(400).json({ error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` });
    }

    const result = await query(
      'UPDATE orders SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING *',
      [status, req.params.id]
    );
    if (result.rows.length === 0) return res.status(404).json({ error: 'Order not found' });

    const updatedOrder = result.rows[0];
    if (global.io) global.io.emit('order_updated', updatedOrder);

    res.json({ success: true, order: updatedOrder });
  } catch (err) { next(err); }
});

// POST /api/orders/create-payment
router.post('/create-payment', async (req, res, next) => {
  try {
    const { amount, order_description } = req.body;
    if (!amount) return res.status(400).json({ error: 'amount is required.' });

    const rzpOrder = await createRazorpayOrder(amount, order_description || `order_${Date.now()}`);
    res.json({
      razorpay_order_id: rzpOrder.id,
      amount: amount,
      currency: 'INR',
      key_id: process.env.RAZORPAY_KEY_ID
    });
  } catch (err) { next(err); }
});

// POST /api/orders/verify-payment
router.post('/verify-payment', async (req, res, next) => {
  try {
    const { razorpay_order_id, razorpay_payment_id, razorpay_signature } = req.body;
    if (!razorpay_order_id || !razorpay_payment_id || !razorpay_signature) {
      return res.status(400).json({ error: 'All payment verification fields are required.' });
    }
    const valid = verifyPayment(razorpay_order_id, razorpay_payment_id, razorpay_signature);
    res.json({ valid });
  } catch (err) { next(err); }
});

module.exports = router;
