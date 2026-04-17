const express = require('express');
const router = express.Router();
const { query } = require('../config/db');
const authenticateToken = require('../middleware/auth');
const { generateInsights } = require('../services/insights');

let insightsCache = { data: null, timestamp: 0 };

// All analytics routes are protected
router.use(authenticateToken);

// GET /api/analytics/summary
router.get('/summary', async (req, res, next) => {
  try {
    const todayResult = await query(
      `SELECT COALESCE(SUM(total),0) AS revenue, COUNT(*) AS orders, COALESCE(AVG(total),0) AS avg_value
       FROM orders WHERE DATE(created_at) = CURRENT_DATE AND status != 'cancelled'`
    );
    const yesterdayResult = await query(
      `SELECT COALESCE(SUM(total),0) AS revenue, COUNT(*) AS orders
       FROM orders WHERE DATE(created_at) = CURRENT_DATE - INTERVAL '1 day' AND status != 'cancelled'`
    );
    const customerResult = await query('SELECT COUNT(*) AS total FROM customers');
    const lowStockResult = await query(
      'SELECT id, name, category, inventory_count FROM menu_items WHERE inventory_count < 10 AND is_available = TRUE ORDER BY inventory_count ASC'
    );

    const t = todayResult.rows[0];
    const y = yesterdayResult.rows[0];
    const todayRev = parseFloat(t.revenue);
    const yestRev = parseFloat(y.revenue);
    const todayOrd = parseInt(t.orders);
    const yestOrd = parseInt(y.orders);

    res.json({
      today_revenue: todayRev,
      today_orders: todayOrd,
      avg_order_value: parseFloat(parseFloat(t.avg_value).toFixed(2)),
      total_customers: parseInt(customerResult.rows[0].total),
      yesterday_revenue: yestRev,
      yesterday_orders: yestOrd,
      revenue_change_pct: yestRev > 0 ? parseFloat(((todayRev - yestRev) / yestRev * 100).toFixed(1)) : 0,
      orders_change_pct: yestOrd > 0 ? parseFloat(((todayOrd - yestOrd) / yestOrd * 100).toFixed(1)) : 0,
      low_stock_items: lowStockResult.rows
    });
  } catch (err) { next(err); }
});

// GET /api/analytics/hourly
router.get('/hourly', async (req, res, next) => {
  try {
    const result = await query(
      `SELECT EXTRACT(HOUR FROM created_at)::INTEGER AS hour, COUNT(*) AS orders, COALESCE(SUM(total),0) AS revenue
       FROM orders WHERE DATE(created_at) = CURRENT_DATE AND status != 'cancelled'
       GROUP BY EXTRACT(HOUR FROM created_at) ORDER BY hour`
    );
    const dataMap = {};
    for (const row of result.rows) {
      dataMap[row.hour] = { hour: row.hour, orders: parseInt(row.orders), revenue: parseFloat(row.revenue) };
    }
    const hourly = [];
    for (let h = 0; h < 24; h++) {
      hourly.push(dataMap[h] || { hour: h, orders: 0, revenue: 0 });
    }
    res.json(hourly);
  } catch (err) { next(err); }
});

// GET /api/analytics/top-items
router.get('/top-items', async (req, res, next) => {
  try {
    const range = req.query.range || 'today';
    let dateFilter = '';
    if (range === 'today') dateFilter = "AND DATE(o.created_at) = CURRENT_DATE";
    else if (range === 'week') dateFilter = "AND o.created_at >= CURRENT_DATE - INTERVAL '7 days'";
    else if (range === 'month') dateFilter = "AND o.created_at >= CURRENT_DATE - INTERVAL '30 days'";

    const result = await query(
      `SELECT item->>'item_id' AS item_id, item->>'item_name' AS item_name,
              SUM((item->>'quantity')::INTEGER) AS count,
              SUM((item->>'item_total')::DECIMAL) AS revenue
       FROM orders o, jsonb_array_elements(o.items) AS item
       WHERE o.status != 'cancelled' ${dateFilter}
       GROUP BY item->>'item_id', item->>'item_name'
       ORDER BY count DESC LIMIT 10`
    );
    res.json(result.rows.map(r => ({
      item_id: r.item_id, item_name: r.item_name,
      count: parseInt(r.count), revenue: parseFloat(r.revenue)
    })));
  } catch (err) { next(err); }
});

// GET /api/analytics/category-revenue
router.get('/category-revenue', async (req, res, next) => {
  try {
    const range = req.query.range || 'today';
    let dateFilter = '';
    if (range === 'today') dateFilter = "AND DATE(o.created_at) = CURRENT_DATE";
    else if (range === 'week') dateFilter = "AND o.created_at >= CURRENT_DATE - INTERVAL '7 days'";
    else if (range === 'month') dateFilter = "AND o.created_at >= CURRENT_DATE - INTERVAL '30 days'";

    const result = await query(
      `SELECT m.category, COALESCE(SUM((item->>'item_total')::DECIMAL),0) AS revenue,
              SUM((item->>'quantity')::INTEGER) AS total_items
       FROM orders o, jsonb_array_elements(o.items) AS item
       LEFT JOIN menu_items m ON m.id = item->>'item_id'
       WHERE o.status != 'cancelled' ${dateFilter}
       GROUP BY m.category ORDER BY revenue DESC`
    );
    res.json(result.rows.map(r => ({
      category: r.category, revenue: parseFloat(r.revenue), total_items: parseInt(r.total_items)
    })));
  } catch (err) { next(err); }
});

// GET /api/analytics/recent-orders
router.get('/recent-orders', async (req, res, next) => {
  try {
    const result = await query(
      'SELECT * FROM orders ORDER BY created_at DESC LIMIT 10'
    );
    res.json(result.rows);
  } catch (err) { next(err); }
});

// GET /api/analytics/insights
router.get('/insights', async (req, res, next) => {
  console.log('GROQ_API_KEY exists:', !!process.env.GROQ_API_KEY);
  console.log('Key first 10 chars:', process.env.GROQ_API_KEY?.substring(0,10));

  try {
    const now = Date.now();
    // Cache for 5 minutes (300,000 ms)
    if (insightsCache.data && (now - insightsCache.timestamp < 300000)) {
      return res.json({ insights: insightsCache.data });
    }

    // 1. Summary (Today/Yesterday Revenue & Orders, Avg Value)
    const todayResult = await query(
      `SELECT COALESCE(SUM(total),0) AS revenue, COUNT(*) AS orders, COALESCE(AVG(total),0) AS avg_value
       FROM orders WHERE DATE(created_at) = CURRENT_DATE AND status != 'cancelled'`
    );
    const yesterdayResult = await query(
      `SELECT COALESCE(SUM(total),0) AS revenue, COUNT(*) AS orders
       FROM orders WHERE DATE(created_at) = CURRENT_DATE - INTERVAL '1 day' AND status != 'cancelled'`
    );
    const t = todayResult.rows[0];
    const y = yesterdayResult.rows[0];
    const todayRev = parseFloat(t.revenue);
    const yestRev = parseFloat(y.revenue);
    const todayOrd = parseInt(t.orders);
    const yestOrd = parseInt(y.orders);
    const avgVal = parseFloat(parseFloat(t.avg_value).toFixed(2));

    // 2. Top Items
    const topItemsResult = await query(
      `SELECT item->>'item_name' AS item_name, SUM((item->>'quantity')::INTEGER) AS count
       FROM orders o, jsonb_array_elements(o.items) AS item
       WHERE o.status != 'cancelled' AND DATE(o.created_at) = CURRENT_DATE
       GROUP BY item->>'item_name' ORDER BY count DESC LIMIT 5`
    );

    // 3. Low Stock Items
    const lowStockResult = await query(
      `SELECT name, inventory_count FROM menu_items WHERE inventory_count < 10 AND is_available = TRUE ORDER BY inventory_count ASC`
    );

    // 4. Hourly Data
    const hourlyResult = await query(
      `SELECT EXTRACT(HOUR FROM created_at)::INTEGER AS hour, COUNT(*) AS orders
       FROM orders WHERE DATE(created_at) = CURRENT_DATE AND status != 'cancelled'
       GROUP BY EXTRACT(HOUR FROM created_at) ORDER BY hour`
    );

    // 5. Category Revenue
    const catResult = await query(
      `SELECT m.category, COALESCE(SUM((item->>'item_total')::DECIMAL),0) AS revenue
       FROM orders o, jsonb_array_elements(o.items) AS item
       LEFT JOIN menu_items m ON m.id = item->>'item_id'
       WHERE o.status != 'cancelled' AND DATE(o.created_at) = CURRENT_DATE
       GROUP BY m.category ORDER BY revenue DESC`
    );

    const analyticsData = {
      today_revenue: todayRev,
      yesterday_revenue: yestRev,
      today_orders: todayOrd,
      yesterday_orders: yestOrd,
      avg_order_value: avgVal,
      top_items: topItemsResult.rows.map(r => ({ item_name: r.item_name, count: parseInt(r.count) })),
      low_stock_items: lowStockResult.rows.map(r => ({ name: r.name, inventory_count: r.inventory_count })),
      hourly_data: hourlyResult.rows.map(r => ({ hour: r.hour, orders: parseInt(r.orders) })),
      category_revenue: catResult.rows.map(r => ({ category: r.category, revenue: parseFloat(r.revenue) }))
    };

    const insights = await generateInsights(analyticsData);
    
    // Update cache
    insightsCache = { data: insights, timestamp: now };
    
    res.json({ insights });
  } catch (err) { next(err); }
});

module.exports = router;
