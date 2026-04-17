const express = require('express');
const router = express.Router();
const { query } = require('../config/db');

// POST /api/recommend — proxy to Python FastAPI recommendation engine
router.post('/', async (req, res, next) => {
  try {
    const pythonApiUrl = process.env.PYTHON_API_URL || 'http://localhost:5000';

    try {
      const fetch = (...args) => import('node-fetch').then(({ default: f }) => f(...args));
      const response = await fetch(`${pythonApiUrl}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body) // Forward complete body as-is
      });

      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      }
      throw new Error(`Python API returned status ${response.status}`);
    } catch (fetchErr) {
      // Fallback: Python API unreachable
      console.warn('Python API unreachable, using fallback');

      const result = await query(
        `SELECT id AS item_id, name AS item_name, category, price
         FROM menu_items WHERE is_available = TRUE
         ORDER BY display_order ASC LIMIT $1`,
        [req.body.top_k || 5]
      );

      const recommendations = result.rows.map((item, i) => ({
        item_id: item.item_id,
        item_name: item.item_name,
        category: item.category,
        price: parseFloat(item.price),
        score: parseFloat((0.9 - i * 0.05).toFixed(2)),
        reason: 'Popular item',
        source: 'fallback'
      }));

      res.json({
        recommendations,
        model_used: 'fallback',
        customer_type: req.body.customer_id ? 'returning' : 'new'
      });
    }
  } catch (err) { next(err); }
});

module.exports = router;
