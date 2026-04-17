require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });
const { Pool } = require('pg');

const pool = new Pool({
  host:     process.env.DB_HOST     || 'localhost',
  database: process.env.DB_NAME     || 'bitekaro',
  user:     process.env.DB_USER     || 'postgres',
  password: String(process.env.DB_PASSWORD || 'root'),
  port:     parseInt(process.env.DB_PORT)  || 5432,
});

// ── 40 realistic Indian customers ─────────────────────────────────────────────
const CUSTOMERS = [
  { name: 'Aarav Shah',       phone: '9876543210', type: 'heavy',  preference: 'hot_beverages'  },
  { name: 'Priya Patel',      phone: '9876543211', type: 'heavy',  preference: 'meals'          },
  { name: 'Rohan Mehta',      phone: '9876543212', type: 'heavy',  preference: 'cold_beverages' },
  { name: 'Ananya Joshi',     phone: '9876543213', type: 'heavy',  preference: 'snacks'         },
  { name: 'Vikram Desai',     phone: '9876543214', type: 'heavy',  preference: 'hot_beverages'  },
  { name: 'Kavya Sharma',     phone: '9876543215', type: 'heavy',  preference: 'desserts'       },
  { name: 'Arjun Nair',       phone: '9876543216', type: 'heavy',  preference: 'meals'          },
  { name: 'Ishaan Gupta',     phone: '9876543217', type: 'heavy',  preference: 'cold_beverages' },
  { name: 'Diya Verma',       phone: '9876543218', type: 'heavy',  preference: 'snacks'         },
  { name: 'Kabir Singh',      phone: '9876543219', type: 'heavy',  preference: 'hot_beverages'  },
  { name: 'Meera Iyer',       phone: '9123456780', type: 'heavy',  preference: 'desserts'       },
  { name: 'Siddharth Rao',    phone: '9123456781', type: 'heavy',  preference: 'meals'          },
  { name: 'Aisha Khan',       phone: '9123456782', type: 'heavy',  preference: 'cold_beverages' },
  { name: 'Tanvi Kulkarni',   phone: '9123456783', type: 'heavy',  preference: 'snacks'         },
  { name: 'Yash Pandey',      phone: '9123456784', type: 'heavy',  preference: 'hot_beverages'  },
  { name: 'Neha Agarwal',     phone: '9123456785', type: 'medium', preference: 'desserts'       },
  { name: 'Dev Malhotra',     phone: '9123456786', type: 'medium', preference: 'meals'          },
  { name: 'Riya Bose',        phone: '9123456787', type: 'medium', preference: 'cold_beverages' },
  { name: 'Aditya Chandra',   phone: '9123456788', type: 'medium', preference: 'snacks'         },
  { name: 'Pooja Reddy',      phone: '9123456789', type: 'medium', preference: 'hot_beverages'  },
  { name: 'Karan Trivedi',    phone: '9988776655', type: 'medium', preference: 'desserts'       },
  { name: 'Simran Kaur',      phone: '9988776656', type: 'medium', preference: 'meals'          },
  { name: 'Rahul Saxena',     phone: '9988776657', type: 'medium', preference: 'cold_beverages' },
  { name: 'Shruti Pillai',    phone: '9988776658', type: 'medium', preference: 'snacks'         },
  { name: 'Ayaan Sheikh',     phone: '9988776659', type: 'medium', preference: 'hot_beverages'  },
  { name: 'Tara Bhatt',       phone: '9988776660', type: 'medium', preference: 'desserts'       },
  { name: 'Nikhil Jain',      phone: '9988776661', type: 'medium', preference: 'meals'          },
  { name: 'Aditi Mishra',     phone: '9988776662', type: 'medium', preference: 'cold_beverages' },
  { name: 'Shaurya Kapoor',   phone: '9988776663', type: 'medium', preference: 'snacks'         },
  { name: 'Manvi Sinha',      phone: '9988776664', type: 'medium', preference: 'hot_beverages'  },
  { name: 'Rehan Qureshi',    phone: '9871234560', type: 'light',  preference: 'desserts'       },
  { name: 'Bhavya Goel',      phone: '9871234561', type: 'light',  preference: 'meals'          },
  { name: 'Samar Luthra',     phone: '9871234562', type: 'light',  preference: 'cold_beverages' },
  { name: 'Roshni Dutta',     phone: '9871234563', type: 'light',  preference: 'snacks'         },
  { name: 'Parth Soni',       phone: '9871234564', type: 'light',  preference: 'hot_beverages'  },
  { name: 'Jiya Chatterjee',  phone: '9871234565', type: 'light',  preference: 'desserts'       },
  { name: 'Advait Murthy',    phone: '9871234566', type: 'light',  preference: 'meals'          },
  { name: 'Kriti Vyas',       phone: '9871234567', type: 'light',  preference: 'cold_beverages' },
  { name: 'Mihir Thakkar',    phone: '9871234568', type: 'light',  preference: 'snacks'         },
  { name: 'Palak Dubey',      phone: '9871234569', type: 'light',  preference: 'hot_beverages'  },
];

// ── Item preferences ──────────────────────────────────────────────────────────
const PREFERENCE_ITEMS = {
  hot_beverages:  ['HB01', 'HB02', 'HB03', 'HB04', 'HB05'],
  cold_beverages: ['CB01', 'CB02', 'CB03', 'CB04', 'CB05'],
  snacks:         ['SN01', 'SN02', 'SN03', 'SN04', 'SN05'],
  meals:          ['ML01', 'ML02', 'ML03', 'ML04', 'ML05'],
  desserts:       ['DS01', 'DS02', 'DS03', 'DS04', 'DS05'],
};

const SECONDARY_ITEMS = {
  hot_beverages:  ['SN01', 'SN03', 'SN04', 'DS02', 'DS03'],
  cold_beverages: ['DS01', 'DS03', 'SN01', 'SN02', 'DS04'],
  snacks:         ['HB03', 'HB04', 'CB03', 'CB04', 'HB02'],
  meals:          ['CB03', 'CB04', 'HB03', 'SN01', 'SN02'],
  desserts:       ['HB02', 'HB05', 'CB01', 'CB02', 'HB03'],
};

// ── Menu metadata ─────────────────────────────────────────────────────────────
const MENU_ITEMS = {
  HB01: { name: 'Espresso',          price: 80  },
  HB02: { name: 'Cappuccino',        price: 120 },
  HB03: { name: 'Masala Chai',       price: 60  },
  HB04: { name: 'Filter Coffee',     price: 70  },
  HB05: { name: 'Hot Chocolate',     price: 130 },
  CB01: { name: 'Cold Coffee',       price: 140 },
  CB02: { name: 'Mango Shake',       price: 120 },
  CB03: { name: 'Lemonade',          price: 80  },
  CB04: { name: 'Iced Tea',          price: 90  },
  CB05: { name: 'Cold Brew',         price: 160 },
  SN01: { name: 'Samosa',            price: 30  },
  SN02: { name: 'Vada Pav',          price: 40  },
  SN03: { name: 'Bread Pakoda',      price: 50  },
  SN04: { name: 'Dhokla',            price: 60  },
  SN05: { name: 'Poha',              price: 60  },
  ML01: { name: 'Masala Dosa',       price: 120 },
  ML02: { name: 'Pav Bhaji',         price: 110 },
  ML03: { name: 'Paneer Wrap',       price: 130 },
  ML04: { name: 'Chole Bhature',     price: 140 },
  ML05: { name: 'Upma',              price: 80  },
  DS01: { name: 'Chocolate Muffin',  price: 80  },
  DS02: { name: 'Gulab Jamun',       price: 60  },
  DS03: { name: 'Brownie',           price: 90  },
  DS04: { name: 'Kulfi',             price: 70  },
  DS05: { name: 'Rasgulla',          price: 50  },
};

const ORDER_COUNTS = {
  heavy:  { min: 35, max: 50 },
  medium: { min: 20, max: 34 },
  light:  { min: 10, max: 19 },
};

function randomBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function pad(n) {
  return String(n).padStart(2, '0');
}

function generateOrderItems(preference) {
  const items  = [];
  const nItems = randomBetween(1, 3);
  for (let i = 0; i < nItems; i++) {
    const itemId = Math.random() < 0.70
      ? pickRandom(PREFERENCE_ITEMS[preference])
      : pickRandom(SECONDARY_ITEMS[preference]);
    if (!items.find(it => it.item_id === itemId)) {
      const meta = MENU_ITEMS[itemId];
      items.push({
        item_id:    itemId,
        item_name:  meta.name,
        price:      meta.price,
        quantity:   1,
        item_total: meta.price,
      });
    }
  }
  if (items.length === 0) {
    const id   = PREFERENCE_ITEMS[preference][0];
    const meta = MENU_ITEMS[id];
    items.push({ item_id: id, item_name: meta.name, price: meta.price, quantity: 1, item_total: meta.price });
  }
  return items;
}

// ── Date generators — ALL in IST (+05:30) ─────────────────────────────────────

// Historical: Oct 2025 - Mar 2026 IST
function historicalDate() {
  const start = new Date('2025-10-01T00:00:00+05:30');
  const end   = new Date('2026-03-31T23:59:59+05:30');
  return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
}

// Recent: Apr 1 - Apr 16 2026 IST
function recentDate() {
  const start = new Date('2026-04-01T08:00:00+05:30');
  const end   = new Date('2026-04-16T22:00:00+05:30');
  return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
}

// Today: Apr 17 2026 IST — realistic cafe hours
function todayDate() {
  const hours = [8,8,9,9,9,10,10,11,12,12,12,13,13,14,15,15,16,17,17,18,19,20];
  const hour  = pickRandom(hours);
  const min   = randomBetween(0, 59);
  const sec   = randomBetween(0, 59);
  return new Date(`2026-04-17T${pad(hour)}:${pad(min)}:${pad(sec)}+05:30`);
}

// Presentation day: Apr 18 2026 IST
function tomorrowDate() {
  const hours = [8,9,9,10,10,11,12,12,13,14,15,16,17];
  const hour  = pickRandom(hours);
  const min   = randomBetween(0, 59);
  const sec   = randomBetween(0, 59);
  return new Date(`2026-04-18T${pad(hour)}:${pad(min)}:${pad(sec)}+05:30`);
}

// ── Insert one order ──────────────────────────────────────────────────────────
async function insertOrder(client, customerId, preference, orderDate, tokenNumber) {
  const items        = generateOrderItems(preference);
  const total        = items.reduce((s, i) => s + i.item_total, 0);
  const pointsEarned = Math.floor(total / 10);
  const payment      = Math.random() < 0.65 ? 'razorpay' : 'cash';

  const res = await client.query(
    `INSERT INTO orders
      (customer_id, items, subtotal, discount, total, payment_method,
       payment_status, status, token_number, special_instructions,
       created_at, updated_at)
     VALUES ($1,$2,$3,0,$4,$5,'paid','completed',$6,'',$7,$7)
     RETURNING id`,
    [
      customerId,
      JSON.stringify(items),
      total,
      total,
      payment,
      tokenNumber,
      orderDate.toISOString(),
    ]
  );

  await client.query(
    `UPDATE customers
     SET loyalty_points = loyalty_points + $1,
         total_orders   = total_orders   + 1,
         total_spent    = total_spent    + $2,
         last_visit     = GREATEST(COALESCE(last_visit, $3), $3),
         updated_at     = NOW()
     WHERE id = $4`,
    [pointsEarned, total, orderDate.toISOString(), customerId]
  );

  await client.query(
    `INSERT INTO loyalty_transactions
      (customer_id, order_id, points_change, transaction_type, description, created_at)
     VALUES ($1,$2,$3,'earned','Points earned on order #'||$4,$5)`,
    [customerId, res.rows[0].id, pointsEarned, tokenNumber, orderDate.toISOString()]
  );

  return total;
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function run() {
  const client = await pool.connect();
  try {
    console.log('Starting history seed (IST timezone)...');

    // Add missing columns safely
    await client.query(`
      ALTER TABLE customers
      ADD COLUMN IF NOT EXISTS total_orders INTEGER      DEFAULT 0,
      ADD COLUMN IF NOT EXISTS total_spent  DECIMAL(10,2) DEFAULT 0.0,
      ADD COLUMN IF NOT EXISTS updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP;
    `);

    // Clean existing seeded customers
    console.log('Cleaning old seed data...');
    const phones      = CUSTOMERS.map(c => c.phone);
    const existing    = await client.query(`SELECT id FROM customers WHERE phone = ANY($1)`, [phones]);
    const existingIds = existing.rows.map(r => r.id);

    if (existingIds.length > 0) {
      await client.query(`DELETE FROM loyalty_transactions WHERE customer_id = ANY($1)`, [existingIds]);
      await client.query(`DELETE FROM orders               WHERE customer_id = ANY($1)`, [existingIds]);
      await client.query(`DELETE FROM customers            WHERE id          = ANY($1)`, [existingIds]);
    }

    // Create fresh customers
    const records = [];
    for (const c of CUSTOMERS) {
      const r = await client.query(
        `INSERT INTO customers (name, phone, loyalty_points, total_orders, total_spent, created_at)
         VALUES ($1,$2,0,0,0,NOW()) RETURNING id`,
        [c.name, c.phone]
      );
      records.push({ ...c, id: r.rows[0].id });
      console.log(`Created: ${c.name}`);
    }

    let token       = 100;
    let totalOrders = 0;

    // ── Phase 1: Historical (Oct 2025 - Mar 2026) ─────────────────────────
    console.log('\n  Phase 1: Historical orders (Oct 2025 - Mar 2026 IST)...');
    for (const c of records) {
      const range = ORDER_COUNTS[c.type];
      const n     = randomBetween(range.min, range.max);
      for (let i = 0; i < n; i++) {
        await insertOrder(client, c.id, c.preference, historicalDate(), ++token);
        totalOrders++;
      }
    }
    console.log(`  Done: ${totalOrders} historical orders`);

    // ── Phase 2: Recent (Apr 1-16 2026 IST) ──────────────────────────────
    console.log('\n  Phase 2: Recent orders (Apr 1-16 2026 IST)...');
    const recentN = randomBetween(200, 250);
    for (let i = 0; i < recentN; i++) {
      const c = pickRandom(records);
      await insertOrder(client, c.id, c.preference, recentDate(), ++token);
      totalOrders++;
    }
    console.log(`  Done: ${recentN} recent orders`);

    // ── Phase 3: Today (Apr 17 2026 IST) ─────────────────────────────────
    console.log('\n  Phase 3: Today orders (Apr 17 2026 IST)...');
    const todayPool = [
      ...records.slice(0, 15),
      ...records.slice(0, 15),
      ...records.slice(15, 30),
      ...records.slice(30),
    ];
    let todayRevenue = 0;
    const todayN = randomBetween(40, 50);
    for (let i = 0; i < todayN; i++) {
      const c = pickRandom(todayPool);
      todayRevenue += await insertOrder(client, c.id, c.preference, todayDate(), ++token);
      totalOrders++;
    }
    console.log(`  Done: ${todayN} orders | Revenue: Rs.${todayRevenue}`);

    // ── Phase 4: Presentation day (Apr 18 2026 IST) ───────────────────────
    console.log('\n  Phase 4: Presentation day (Apr 18 2026 IST)...');
    let tomorrowRevenue = 0;
    const tomorrowN = randomBetween(25, 35);
    for (let i = 0; i < tomorrowN; i++) {
      const c = pickRandom(records);
      tomorrowRevenue += await insertOrder(client, c.id, c.preference, tomorrowDate(), ++token);
      totalOrders++;
    }
    console.log(`  Done: ${tomorrowN} orders | Revenue: Rs.${tomorrowRevenue}`);

    // ── Summary ───────────────────────────────────────────────────────────
    console.log('\n✅ Seed complete!');
    console.log(`   Customers          : ${CUSTOMERS.length}`);
    console.log(`   Total orders       : ${totalOrders}`);
    console.log(`   Avg orders/customer: ${(totalOrders / CUSTOMERS.length).toFixed(1)}`);

    const dbSummary = await client.query(`
      SELECT COUNT(DISTINCT customer_id) AS customers,
             COUNT(*)                    AS total_orders,
             COALESCE(SUM(total), 0)     AS total_revenue,
             ROUND(AVG(total))           AS avg_order_value
      FROM orders WHERE status = 'completed'
    `);
    console.log('\n   Overall DB Summary:', dbSummary.rows[0]);

    // Verify Apr 17 in IST
    const apr17 = await client.query(`
      SELECT COUNT(*) AS orders,
             COALESCE(SUM(total), 0) AS revenue
      FROM orders
      WHERE DATE(created_at AT TIME ZONE 'Asia/Kolkata') = '2026-04-17'
      AND status = 'completed'
    `);
    console.log('   Apr 17 (Today IST):', apr17.rows[0]);

    // Verify Apr 18 in IST
    const apr18 = await client.query(`
      SELECT COUNT(*) AS orders,
             COALESCE(SUM(total), 0) AS revenue
      FROM orders
      WHERE DATE(created_at AT TIME ZONE 'Asia/Kolkata') = '2026-04-18'
      AND status = 'completed'
    `);
    console.log('   Apr 18 (Presentation IST):', apr18.rows[0]);

    // Top 5 customers
    const top5 = await client.query(`
      SELECT name, loyalty_points, total_orders
      FROM customers
      ORDER BY loyalty_points DESC
      LIMIT 5
    `);
    console.log('\n   Top 5 customers:');
    top5.rows.forEach(r =>
      console.log(`     ${r.name} → ${r.loyalty_points} pts (${r.total_orders} orders)`)
    );

    // Top items today
    const topToday = await client.query(`
      SELECT item->>'item_name' AS item, COUNT(*) AS cnt
      FROM orders, jsonb_array_elements(items) AS item
      WHERE DATE(created_at AT TIME ZONE 'Asia/Kolkata') = '2026-04-17'
      GROUP BY item->>'item_name'
      ORDER BY cnt DESC
      LIMIT 5
    `);
    console.log('\n   Top items today (Apr 17):');
    topToday.rows.forEach(r =>
      console.log(`     ${r.item} → ${r.cnt} orders`)
    );

  } catch (e) {
    console.error('Seed failed:', e.message);
    throw e;
  } finally {
    client.release();
    pool.end();
  }
}

run();
