const express = require('express');
const router = express.Router();
const { query } = require('../config/db');
const authenticateToken = require('../middleware/auth');

// GET /api/menu — all available items grouped by category
router.get('/', async (req, res, next) => {
  try {
    const result = await query(
      'SELECT * FROM menu_items WHERE is_available = TRUE ORDER BY display_order ASC'
    );
    const items = result.rows;

    // Group by category
    const categories = {};
    for (const item of items) {
      const cat = item.category;
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(item);
    }

    res.json({ success: true, categories, all: items });
  } catch (err) { next(err); }
});

// GET /api/menu/all — all items including unavailable (protected)
router.get('/all', authenticateToken, async (req, res, next) => {
  try {
    const result = await query('SELECT * FROM menu_items ORDER BY display_order ASC');
    res.json({ success: true, items: result.rows });
  } catch (err) { next(err); }
});

// GET /api/menu/:id — single item
router.get('/:id', async (req, res, next) => {
  try {
    const result = await query('SELECT * FROM menu_items WHERE id = $1', [req.params.id]);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Menu item not found' });
    }
    res.json(result.rows[0]);
  } catch (err) { next(err); }
});

// POST /api/menu — create item (protected)
router.post('/', authenticateToken, async (req, res, next) => {
  try {
    const { id, name, description, price, category, image_url, tags, calories, modifiers, inventory_count, is_available, available_from, available_until, display_order } = req.body;
    if (!name || !price || !category) {
      return res.status(400).json({ error: 'name, price, and category are required.' });
    }
    const itemId = id || (category.substring(0, 2).toUpperCase() + String(Date.now()).slice(-3));
    const result = await query(
      `INSERT INTO menu_items (id, name, description, price, category, image_url, tags, calories, modifiers, inventory_count, is_available, available_from, available_until, display_order)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14) RETURNING *`,
      [itemId, name, description || '', price, category, image_url || null,
       JSON.stringify(tags || []), calories || 0, JSON.stringify(modifiers || []),
       inventory_count != null ? inventory_count : 100, is_available != null ? is_available : true,
       available_from || null, available_until || null, display_order || 0]
    );
    res.status(201).json({ success: true, item: result.rows[0] });
  } catch (err) { next(err); }
});

// PUT /api/menu/:id — update item (protected)
router.put('/:id', authenticateToken, async (req, res, next) => {
  try {
    const { id } = req.params;
    const existing = await query('SELECT * FROM menu_items WHERE id = $1', [id]);
    if (existing.rows.length === 0) return res.status(404).json({ error: 'Menu item not found' });

    const allowedFields = ['name','description','price','category','image_url','tags','calories','modifiers','inventory_count','is_available','available_from','available_until','display_order'];
    const setClauses = [];
    const values = [];
    let idx = 1;

    for (const field of allowedFields) {
      if (req.body[field] !== undefined) {
        let val = req.body[field];
        if (field === 'tags' || field === 'modifiers') val = JSON.stringify(val);
        setClauses.push(`${field} = $${idx}`);
        values.push(val);
        idx++;
      }
    }
    if (setClauses.length === 0) return res.status(400).json({ error: 'No valid fields to update.' });

    values.push(id);
    const result = await query(
      `UPDATE menu_items SET ${setClauses.join(', ')} WHERE id = $${idx} RETURNING *`, values
    );
    res.json({ success: true, item: result.rows[0] });
  } catch (err) { next(err); }
});

// PATCH /api/menu/:id/availability (protected)
router.patch('/:id/availability', authenticateToken, async (req, res, next) => {
  try {
    const { is_available } = req.body;
    if (is_available === undefined) return res.status(400).json({ error: 'is_available is required.' });
    const result = await query(
      'UPDATE menu_items SET is_available = $1 WHERE id = $2 RETURNING *', [is_available, req.params.id]
    );
    if (result.rows.length === 0) return res.status(404).json({ error: 'Menu item not found' });
    res.json({ success: true, item: result.rows[0] });
  } catch (err) { next(err); }
});

// PATCH /api/menu/:id/inventory (protected)
router.patch('/:id/inventory', authenticateToken, async (req, res, next) => {
  try {
    const { inventory_count } = req.body;
    if (inventory_count === undefined) return res.status(400).json({ error: 'inventory_count is required.' });
    const result = await query(
      'UPDATE menu_items SET inventory_count = $1 WHERE id = $2 RETURNING *', [inventory_count, req.params.id]
    );
    if (result.rows.length === 0) return res.status(404).json({ error: 'Menu item not found' });
    res.json({ success: true, item: result.rows[0] });
  } catch (err) { next(err); }
});

// DELETE /api/menu/:id (protected)
router.delete('/:id', authenticateToken, async (req, res, next) => {
  try {
    const result = await query('DELETE FROM menu_items WHERE id = $1 RETURNING *', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Menu item not found' });
    res.json({ success: true, message: 'Item deleted', item: result.rows[0] });
  } catch (err) { next(err); }
});

module.exports = router;
