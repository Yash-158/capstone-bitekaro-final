require('dotenv').config()
const { Pool } = require('pg')

const pool = new Pool({
  host: 'localhost',
  database: 'bitekaro',
  user: 'postgres',
  password: 'root',
  port: 5432,
})

// 40 realistic Indian customers
const CUSTOMERS = [
  { name: 'Aarav Shah',       phone: '9876543210' },
  { name: 'Priya Patel',      phone: '9876543211' },
  { name: 'Rohan Mehta',      phone: '9876543212' },
  { name: 'Ananya Joshi',     phone: '9876543213' },
  { name: 'Vikram Desai',     phone: '9876543214' },
  { name: 'Kavya Sharma',     phone: '9876543215' },
  { name: 'Arjun Nair',       phone: '9876543216' },
  { name: 'Ishaan Gupta',     phone: '9876543217' },
  { name: 'Diya Verma',       phone: '9876543218' },
  { name: 'Kabir Singh',      phone: '9876543219' },
  { name: 'Meera Iyer',       phone: '9123456780' },
  { name: 'Siddharth Rao',    phone: '9123456781' },
  { name: 'Aisha Khan',       phone: '9123456782' },
  { name: 'Tanvi Kulkarni',   phone: '9123456783' },
  { name: 'Yash Pandey',      phone: '9123456784' },
  { name: 'Neha Agarwal',     phone: '9123456785' },
  { name: 'Dev Malhotra',     phone: '9123456786' },
  { name: 'Riya Bose',        phone: '9123456787' },
  { name: 'Aditya Chandra',   phone: '9123456788' },
  { name: 'Pooja Reddy',      phone: '9123456789' },
  { name: 'Karan Trivedi',    phone: '9988776655' },
  { name: 'Simran Kaur',      phone: '9988776656' },
  { name: 'Rahul Saxena',     phone: '9988776657' },
  { name: 'Shruti Pillai',    phone: '9988776658' },
  { name: 'Ayaan Sheikh',     phone: '9988776659' },
  { name: 'Tara Bhatt',       phone: '9988776660' },
  { name: 'Nikhil Jain',      phone: '9988776661' },
  { name: 'Aditi Mishra',     phone: '9988776662' },
  { name: 'Shaurya Kapoor',   phone: '9988776663' },
  { name: 'Manvi Sinha',      phone: '9988776664' },
  { name: 'Rehan Qureshi',    phone: '9871234560' },
  { name: 'Bhavya Goel',      phone: '9871234561' },
  { name: 'Samar Luthra',     phone: '9871234562' },
  { name: 'Roshni Dutta',     phone: '9871234563' },
  { name: 'Parth Soni',       phone: '9871234564' },
  { name: 'Jiya Chatterjee',  phone: '9871234565' },
  { name: 'Advait Murthy',    phone: '9871234566' },
  { name: 'Kriti Vyas',       phone: '9871234567' },
  { name: 'Mihir Thakkar',    phone: '9871234568' },
  { name: 'Palak Dubey',      phone: '9871234569' },
]

const MENU_ITEMS = {
  HB01:{ name:'Espresso',          price:80,  category:'hot_beverages'  },
  HB02:{ name:'Cappuccino',        price:120, category:'hot_beverages'  },
  HB03:{ name:'Masala Chai',       price:60,  category:'hot_beverages'  },
  HB04:{ name:'Filter Coffee',     price:70,  category:'hot_beverages'  },
  HB05:{ name:'Hot Chocolate',     price:130, category:'hot_beverages'  },
  CB01:{ name:'Cold Coffee',       price:140, category:'cold_beverages' },
  CB02:{ name:'Mango Shake',       price:120, category:'cold_beverages' },
  CB03:{ name:'Lemonade',          price:80,  category:'cold_beverages' },
  CB04:{ name:'Iced Tea',          price:90,  category:'cold_beverages' },
  CB05:{ name:'Cold Brew',         price:160, category:'cold_beverages' },
  SN01:{ name:'Samosa',            price:30,  category:'snacks'         },
  SN02:{ name:'Vada Pav',          price:40,  category:'snacks'         },
  SN03:{ name:'Bread Pakoda',      price:50,  category:'snacks'         },
  SN04:{ name:'Dhokla',            price:60,  category:'snacks'         },
  SN05:{ name:'Poha',              price:60,  category:'snacks'         },
  ML01:{ name:'Masala Dosa',       price:120, category:'meals'          },
  ML02:{ name:'Pav Bhaji',         price:110, category:'meals'          },
  ML03:{ name:'Paneer Wrap',       price:130, category:'meals'          },
  ML04:{ name:'Chole Bhature',     price:140, category:'meals'          },
  ML05:{ name:'Upma',              price:80,  category:'meals'          },
  DS01:{ name:'Chocolate Muffin',  price:80,  category:'desserts'       },
  DS02:{ name:'Gulab Jamun',       price:60,  category:'desserts'       },
  DS03:{ name:'Brownie',           price:90,  category:'desserts'       },
  DS04:{ name:'Kulfi',             price:70,  category:'desserts'       },
  DS05:{ name:'Rasgulla',          price:50,  category:'desserts'       },
}

const TIME_SLOTS = [
  { hour: 8,  items: ['HB01','HB02','HB03','HB04','SN05','SN04'] },
  { hour: 9,  items: ['HB01','HB02','HB03','HB04','SN05'] },
  { hour: 10, items: ['HB02','HB03','CB01','SN04','SN05'] },
  { hour: 12, items: ['ML01','ML02','ML03','ML04','ML05','SN01','SN02'] },
  { hour: 13, items: ['ML01','ML02','ML03','ML04','SN01','SN02','CB03'] },
  { hour: 14, items: ['ML02','ML03','ML05','SN01','CB03','CB04'] },
  { hour: 16, items: ['CB01','CB02','CB04','CB05','SN01','SN03','DS01'] },
  { hour: 17, items: ['CB01','CB05','CB04','SN01','SN03','DS03'] },
  { hour: 18, items: ['CB01','CB02','CB05','DS01','DS03','SN02'] },
  { hour: 19, items: ['DS01','DS02','DS03','DS04','CB01','HB05'] },
  { hour: 20, items: ['DS02','DS03','DS04','DS05','HB05','CB01'] },
  { hour: 21, items: ['HB05','DS02','DS04','DS05','CB05'] },
]

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function randomBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function getOrdersForDay(date) {
  const dayOfWeek = date.getDay()
  const month = date.getMonth() // 11=Dec, 0=Jan, 1=Feb
  const isWeekend = dayOfWeek === 0 || dayOfWeek === 6
  
  let base = isWeekend ? randomBetween(5, 9) : randomBetween(2, 5)
  if (month === 11) base = Math.ceil(base * 1.3) // Dec busier
  if (month === 0)  base = Math.ceil(base * 0.7) // Jan slower
  
  return base
}

function generateOrderItems(hour) {
  const slot = TIME_SLOTS.find(s => s.hour === hour) 
    || TIME_SLOTS[randomBetween(0, TIME_SLOTS.length - 1)]
  
  const numItems = randomBetween(1, 3)
  const selected = []
  
  for (let i = 0; i < numItems; i++) {
    const itemId = pickRandom(slot.items)
    const existing = selected.find(s => s.item_id === itemId)
    if (existing && Math.random() < 0.3) {
      existing.quantity++
    } else {
      selected.push({ item_id: itemId, quantity: 1 })
    }
  }
  
  return selected.map(s => ({
    item_id:   s.item_id,
    item_name: MENU_ITEMS[s.item_id].name,
    price:     MENU_ITEMS[s.item_id].price,
    quantity:  s.quantity,
    subtotal:  MENU_ITEMS[s.item_id].price * s.quantity,
  }))
}

async function run() {
  const client = await pool.connect()
  
  try {
    console.log('Starting history seed...')
    
    // Add missing schema columns if they do not exist
    await client.query(`
      ALTER TABLE customers 
      ADD COLUMN IF NOT EXISTS total_orders INTEGER DEFAULT 0,
      ADD COLUMN IF NOT EXISTS total_spent DECIMAL(10,2) DEFAULT 0.0,
      ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    `);

    // Create customers
    const customerIds = []
    for (const c of CUSTOMERS) {
      const existing = await client.query(
        'SELECT id FROM customers WHERE phone = $1', [c.phone]
      )
      if (existing.rows.length > 0) {
        customerIds.push({ ...c, id: existing.rows[0].id })
        continue
      }
      const res = await client.query(
        `INSERT INTO customers (name, phone, loyalty_points, created_at)
         VALUES ($1, $2, 0, NOW()) RETURNING id`,
        [c.name, c.phone]
      )
      customerIds.push({ ...c, id: res.rows[0].id })
      console.log('Created customer:', c.name)
    }
    
    // Assign order frequency per customer
    const heavyUsers  = customerIds.slice(0, 8)   // 8-15 orders each
    const mediumUsers = customerIds.slice(8, 30)   // 3-7 orders each
    const lightUsers  = customerIds.slice(30)      // 1-2 orders each
    
    let tokenNumber = 100
    let totalOrders = 0
    
    // Generate orders across 3 months
    const startDate = new Date('2025-12-01')
    const endDate   = new Date('2026-02-28')
    
    for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
      const ordersToday = getOrdersForDay(d)
      
      for (let o = 0; o < ordersToday; o++) {
        // Pick customer weighted by frequency
        let customer
        const r = Math.random()
        if (r < 0.3) {
          customer = pickRandom(heavyUsers)
        } else if (r < 0.8) {
          customer = pickRandom(mediumUsers)
        } else {
          customer = pickRandom(lightUsers)
        }
        
        // Pick time slot
        const slot = pickRandom(TIME_SLOTS)
        const minute = randomBetween(0, 59)
        const orderDate = new Date(d)
        orderDate.setHours(slot.hour, minute, randomBetween(0, 59), 0)
        
        const items = generateOrderItems(slot.hour)
        const subtotal = items.reduce((sum, i) => sum + i.subtotal, 0)
        const total = subtotal
        const pointsEarned = Math.floor(total / 10)
        const paymentMethod = Math.random() < 0.7 ? 'razorpay' : 'cash'
        tokenNumber++
        
        // Insert order
        const orderRes = await client.query(
          `INSERT INTO orders 
            (customer_id, items, subtotal, total, payment_method, 
             payment_status, status, token_number, 
             special_instructions, created_at, updated_at)
           VALUES ($1, $2, $3, $4, $5, 'paid', 'completed', $6, '', $7, $7)
           RETURNING id`,
          [
            customer.id,
            JSON.stringify(items),
            subtotal,
            total,
            paymentMethod,
            tokenNumber,
            orderDate.toISOString(),
          ]
        )
        
        // Update customer loyalty stats
        await client.query(
          `UPDATE customers 
           SET loyalty_points = loyalty_points + $1,
               total_orders   = total_orders + 1,
               total_spent    = total_spent + $2,
               updated_at     = NOW()
           WHERE id = $3`,
          [pointsEarned, total, customer.id]
        )
        
        // Insert loyalty transaction
        await client.query(
          `INSERT INTO loyalty_transactions 
            (customer_id, order_id, points_change, transaction_type, description, created_at)
           VALUES ($1, $2, $3, 'earned', 'Points earned on order #' || $4, $5)`,
          [customer.id, orderRes.rows[0].id, pointsEarned, tokenNumber, orderDate.toISOString()]
        )
        
        totalOrders++
      }
    }
    
    console.log('\n✅ Seed complete!')
    console.log('   Customers created/verified:', CUSTOMERS.length)
    console.log('   Total orders inserted:', totalOrders)
    
    // Print summary
    const summary = await client.query(`
      SELECT 
        COUNT(DISTINCT customer_id) as unique_customers,
        COUNT(*) as total_orders,
        SUM(total) as total_revenue,
        ROUND(AVG(total)) as avg_order_value
      FROM orders WHERE status = 'completed'
    `)
    console.log('   DB Summary:', summary.rows[0])
    
    const topCustomers = await client.query(`
      SELECT c.name, c.loyalty_points
      FROM customers c
      ORDER BY c.loyalty_points DESC
      LIMIT 5
    `)
    console.log('   Top 5 customers by points:')
    topCustomers.rows.forEach(r => 
      console.log('  ', r.name, '→', r.loyalty_points, 'pts')
    )
    
  } catch(e) {
    console.error('Seed failed:', e.message)
    throw e
  } finally {
    client.release()
    pool.end()
  }
}

run()
