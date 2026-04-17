const express = require('express');
const router = express.Router();
const { query } = require('../config/db');
const authenticateToken = require('../middleware/auth');

// GET /api/loyalty/members (protected) — MUST be before /:phone
router.get('/members', authenticateToken, async (req, res, next) => {
  try {
    const result = await query('SELECT * FROM customers ORDER BY loyalty_points DESC');
    res.json({ success: true, members: result.rows });
  } catch (err) { next(err); }
});

// GET /api/loyalty/:phone — lookup by phone
router.get('/:phone', async (req, res, next) => {
  try {
    const result = await query('SELECT * FROM customers WHERE phone = $1', [req.params.phone]);
    if (result.rows.length === 0) {
      return res.json({ exists: false });
    }
    res.json({ exists: true, customer: result.rows[0] });
  } catch (err) { next(err); }
});

// POST /api/loyalty/register
router.post('/register', async (req, res, next) => {
  try {
    const { phone, name } = req.body;
    if (!phone) return res.status(400).json({ error: 'Phone number is required.' });

    // Check if exists
    const existing = await query('SELECT * FROM customers WHERE phone = $1', [phone]);
    if (existing.rows.length > 0) {
      return res.json({ exists: true, customer: existing.rows[0] });
    }

    const result = await query(
      'INSERT INTO customers (phone, name) VALUES ($1, $2) RETURNING *',
      [phone, name || null]
    );
    res.status(201).json({ exists: false, customer: result.rows[0] });
  } catch (err) { next(err); }
});

// POST /api/loyalty/redeem
router.post('/redeem', async (req, res, next) => {
  try {
    const { customer_id, points_to_redeem } = req.body;
    if (!customer_id || !points_to_redeem) {
      return res.status(400).json({ error: 'customer_id and points_to_redeem are required.' });
    }

    const custResult = await query('SELECT * FROM customers WHERE id = $1', [customer_id]);
    if (custResult.rows.length === 0) return res.status(404).json({ error: 'Customer not found.' });

    const customer = custResult.rows[0];
    if (customer.loyalty_points < points_to_redeem) {
      return res.status(400).json({ error: 'Insufficient points.', available_points: customer.loyalty_points });
    }

    // 10 points = Rs.10 discount
    const discount_amount = points_to_redeem;

    await query('UPDATE customers SET loyalty_points = loyalty_points - $1 WHERE id = $2',
      [points_to_redeem, customer_id]);

    await query(
      `INSERT INTO loyalty_transactions (customer_id, points_change, transaction_type, description)
       VALUES ($1, $2, $3, $4)`,
      [customer_id, -points_to_redeem, 'redeemed', `Redeemed ${points_to_redeem} points for Rs.${discount_amount} discount`]
    );

    res.json({
      success: true,
      discount_amount,
      remaining_points: customer.loyalty_points - points_to_redeem
    });
  } catch (err) { next(err); }
});

// PATCH /api/loyalty/:id/points (protected)
router.patch('/:id/points', authenticateToken, async (req, res, next) => {
  try {
    const { points_change, description } = req.body;
    if (points_change === undefined) return res.status(400).json({ error: 'points_change is required.' });

    const custResult = await query('SELECT * FROM customers WHERE id = $1', [req.params.id]);
    if (custResult.rows.length === 0) return res.status(404).json({ error: 'Customer not found.' });

    await query(
      'UPDATE customers SET loyalty_points = GREATEST(loyalty_points + $1, 0) WHERE id = $2',
      [points_change, req.params.id]
    );

    await query(
      `INSERT INTO loyalty_transactions (customer_id, points_change, transaction_type, description)
       VALUES ($1, $2, $3, $4)`,
      [req.params.id, points_change, 'manual', description || 'Manual adjustment']
    );

    const updated = await query('SELECT * FROM customers WHERE id = $1', [req.params.id]);
    res.json({ success: true, customer: updated.rows[0] });
  } catch (err) { next(err); }
});

module.exports = router;
