const express = require('express');
const router = express.Router();
const { query } = require('../config/db');

// POST /api/recommend — proxy to Python FastAPI recommendation engine
// Enriches request with real order history from PostgreSQL before proxying
router.post('/', async (req, res, next) => {
  try {
    const pythonApiUrl = process.env.PYTHON_API_URL || 'http://localhost:5000';

    // ── Enrich with real order history from DB ──────────────────────────────
    let requestBody = { ...req.body };

    if (requestBody.customer_id) {
      try {
        const historyResult = await query(
          `SELECT items FROM orders
           WHERE customer_id = $1
           AND status = 'completed'
           ORDER BY created_at DESC
           LIMIT 20`,
          [requestBody.customer_id]
        );

        const orderHistory = [];
        for (const row of historyResult.rows) {
          const items = typeof row.items === 'string'
            ? JSON.parse(row.items) : row.items;
          if (Array.isArray(items)) {
            items.forEach(item => {
              if (item.item_id) orderHistory.push(item.item_id);
            });
          }
        }

        if (orderHistory.length > 0) {
          requestBody.order_history = orderHistory;
          console.log(`[Recommend] Customer ${requestBody.customer_id} — injected ${orderHistory.length} history items`);
        }
      } catch (dbErr) {
        console.warn('[Recommend] Could not fetch order history:', dbErr.message);
      }
    }

    // ── Proxy to Python FastAPI ─────────────────────────────────────────────
    try {
      const fetch = (...args) => import('node-fetch').then(({ default: f }) => f(...args));
      const response = await fetch(`${pythonApiUrl}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      }
      throw new Error(`Python API returned status ${response.status}`);

    } catch (fetchErr) {
      // ── Fallback: Python API unreachable ──────────────────────────────────
      console.warn('[Recommend] Python API unreachable, using DB fallback');

      // Smart fallback — if we have order history, boost those categories
      let fallbackQuery = `
        SELECT id AS item_id, name AS item_name, category, price
        FROM menu_items WHERE is_available = TRUE
        ORDER BY display_order ASC LIMIT $1`;

      const result = await query(fallbackQuery, [requestBody.top_k || 5]);

      const recommendations = result.rows.map((item, i) => ({
        item_id:   item.item_id,
        item_name: item.item_name,
        category:  item.category,
        price:     parseFloat(item.price),
        score:     parseFloat((0.9 - i * 0.05).toFixed(2)),
        reason:    'Popular item',
        source:    'fallback'
      }));

      res.json({
        recommendations,
        model_used:    'fallback',
        customer_type: requestBody.customer_id ? 'returning' : 'new'
      });
    }

  } catch (err) { next(err); }
});

module.exports = router;