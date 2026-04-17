require('dotenv').config({ path: require('path').join(__dirname, '..', '..', '.env') });

const { pool, initDB } = require('../config/db');
const bcrypt = require('bcryptjs');

const menuItems = [
  // HOT BEVERAGES
  {
    id: 'HB01', name: 'Espresso', price: 80, category: 'hot_beverages',
    description: 'A concentrated shot of rich, bold espresso. Pure coffee perfection.',
    image_url: '/public/images/Espresso.jpg',
    tags: ['coffee', 'strong', 'energizing', 'hot'], calories: 10, display_order: 1,
    modifiers: [
      { name: 'Sugar', options: ['No Sugar', 'Less Sugar', 'Normal', 'Extra Sugar'] },
      { name: 'Size', options: ['Small', 'Regular'] }
    ]
  },
  {
    id: 'HB02', name: 'Cappuccino', price: 120, category: 'hot_beverages',
    description: 'Velvety steamed milk foam over a double shot of espresso.',
    image_url: '/public/images/Cappuccino.jpg',
    tags: ['coffee', 'creamy', 'popular', 'hot'], calories: 120, display_order: 2,
    modifiers: [
      { name: 'Sugar', options: ['No Sugar', 'Less Sugar', 'Normal', 'Extra Sugar'] },
      { name: 'Milk', options: ['Full Fat', 'Skimmed', 'Oat'] },
      { name: 'Size', options: ['Regular', 'Large'] }
    ]
  },
  {
    id: 'HB03', name: 'Masala Chai', price: 60, category: 'hot_beverages',
    description: 'Traditional Indian spiced tea brewed with ginger, cardamom, and aromatic spices.',
    image_url: '/public/images/Masala Chai.jpg',
    tags: ['tea', 'spicy', 'comfort', 'hot', 'indian'], calories: 90, display_order: 3,
    modifiers: [
      { name: 'Sugar', options: ['No Sugar', 'Less Sugar', 'Normal', 'Extra Sugar'] },
      { name: 'Ginger', options: ['Regular', 'Extra Ginger'] }
    ]
  },
  {
    id: 'HB04', name: 'Filter Coffee', price: 70, category: 'hot_beverages',
    description: 'Authentic South Indian filter coffee with a rich, earthy depth.',
    image_url: '/public/images/Filter Coffee.jpg',
    tags: ['coffee', 'strong', 'south-indian', 'hot'], calories: 80, display_order: 4,
    modifiers: [
      { name: 'Sugar', options: ['No Sugar', 'Less Sugar', 'Normal', 'Extra Sugar'] }
    ]
  },
  {
    id: 'HB05', name: 'Hot Chocolate', price: 130, category: 'hot_beverages',
    description: 'Rich, velvety hot chocolate made with premium Belgian cocoa.',
    image_url: '/public/images/Hot Chocolate.jpg',
    tags: ['sweet', 'comfort', 'hot', 'indulgent'], calories: 220, display_order: 5,
    modifiers: [
      { name: 'Toppings', options: ['None', 'Whipped Cream', 'Marshmallows', 'Both'] },
      { name: 'Size', options: ['Regular', 'Large'] }
    ]
  },

  // COLD BEVERAGES
  {
    id: 'CB01', name: 'Cold Coffee', price: 140, category: 'cold_beverages',
    description: 'Chilled blended coffee — smooth, creamy, and refreshing.',
    image_url: '/public/images/Cold Coffee.jpeg',
    tags: ['coffee', 'cold', 'popular', 'refreshing'], calories: 180, display_order: 6,
    modifiers: [
      { name: 'Sugar', options: ['No Sugar', 'Less Sugar', 'Normal', 'Extra Sugar'] },
      { name: 'Size', options: ['Regular', 'Large'] },
      { name: 'Ice', options: ['Normal Ice', 'Extra Ice', 'Less Ice'] }
    ]
  },
  {
    id: 'CB02', name: 'Mango Shake', price: 120, category: 'cold_beverages',
    description: 'Thick, fresh mango shake made with Alphonso mangoes. A summer favourite.',
    image_url: '/public/images/Mango Shake.jpg',
    tags: ['fruity', 'cold', 'sweet', 'seasonal', 'filling'], calories: 210, display_order: 7,
    modifiers: [
      { name: 'Sugar', options: ['No Sugar', 'Normal'] },
      { name: 'Size', options: ['Regular', 'Large'] }
    ]
  },
  {
    id: 'CB03', name: 'Lemonade', price: 80, category: 'cold_beverages',
    description: 'Fresh squeezed lemonade with a hint of mint. Light and tangy.',
    image_url: '/public/images/Lemonade.jpg',
    tags: ['refreshing', 'cold', 'light', 'tangy'], calories: 60, display_order: 8,
    modifiers: [
      { name: 'Sweetness', options: ['Less Sweet', 'Normal', 'Extra Sweet'] },
      { name: 'Salt', options: ['No Salt', 'With Black Salt'] }
    ]
  },
  {
    id: 'CB04', name: 'Iced Tea', price: 90, category: 'cold_beverages',
    description: 'Chilled brewed tea served over ice. Light and perfectly refreshing.',
    image_url: '/public/images/Iced Tea.jpg',
    tags: ['tea', 'cold', 'light', 'refreshing'], calories: 70, display_order: 9,
    modifiers: [
      { name: 'Flavour', options: ['Lemon', 'Peach', 'Classic'] },
      { name: 'Sugar', options: ['No Sugar', 'Normal'] }
    ]
  },
  {
    id: 'CB05', name: 'Cold Brew', price: 160, category: 'cold_beverages',
    description: 'Slow-steeped 16-hour cold brew. Smooth, strong, and premium.',
    image_url: '/public/images/Cold Brew.jpeg',
    tags: ['coffee', 'cold', 'strong', 'premium'], calories: 15, display_order: 10,
    modifiers: [
      { name: 'Milk', options: ['Black', 'With Milk', 'With Oat Milk'] },
      { name: 'Ice', options: ['Normal Ice', 'Extra Ice'] }
    ]
  },

  // SNACKS
  {
    id: 'SN01', name: 'Samosa', price: 30, category: 'snacks',
    description: 'Crispy golden pastry filled with spiced potatoes and peas.',
    image_url: '/public/images/Samosa.jpg',
    tags: ['indian', 'veg', 'fried', 'spicy', 'popular'], calories: 130, display_order: 11,
    modifiers: [
      { name: 'Quantity', options: ['1 Piece', '2 Pieces', '4 Pieces'] },
      { name: 'Chutney', options: ['Green Chutney', 'Tamarind', 'Both', 'None'] }
    ]
  },
  {
    id: 'SN02', name: 'Vada Pav', price: 40, category: 'snacks',
    description: "Mumbai's favourite street food. Spicy potato vada in a soft pav.",
    image_url: '/public/images/Vada Pav.jpg',
    tags: ['indian', 'veg', 'filling', 'spicy', 'mumbai'], calories: 290, display_order: 12,
    modifiers: [
      { name: 'Chutney', options: ['Dry Garlic', 'Green', 'Both'] },
      { name: 'Extra', options: ['None', 'Extra Vada'] }
    ]
  },
  {
    id: 'SN03', name: 'Bread Pakoda', price: 50, category: 'snacks',
    description: 'Crispy battered bread with a spiced filling. Perfect with chai.',
    image_url: '/public/images/Bread Pakoda.jpg',
    tags: ['indian', 'veg', 'fried', 'comfort', 'monsoon'], calories: 200, display_order: 13,
    modifiers: [
      { name: 'Filling', options: ['Plain', 'Aloo Filling'] },
      { name: 'Chutney', options: ['Green Chutney', 'Ketchup', 'Both'] }
    ]
  },
  {
    id: 'SN04', name: 'Dhokla', price: 60, category: 'snacks',
    description: 'Soft, spongy steamed Gujarati snack. Light, healthy, and flavourful.',
    image_url: '/public/images/Dhokla.jpg',
    tags: ['indian', 'veg', 'light', 'gujarati', 'healthy'], calories: 160, display_order: 14,
    modifiers: [
      { name: 'Quantity', options: ['4 Pieces', '8 Pieces'] },
      { name: 'Extra', options: ['None', 'Extra Chutney'] }
    ]
  },
  {
    id: 'SN05', name: 'Poha', price: 60, category: 'snacks',
    description: 'Flattened rice cooked with onions, mustard seeds, and fresh coriander.',
    image_url: '/public/images/Poha.jpg',
    tags: ['indian', 'veg', 'light', 'breakfast', 'healthy'], calories: 180, display_order: 15,
    modifiers: [
      { name: 'Spice', options: ['Mild', 'Medium', 'Spicy'] },
      { name: 'Extra', options: ['None', 'Extra Sev', 'Extra Peanuts'] }
    ]
  },

  // MEALS
  {
    id: 'ML01', name: 'Masala Dosa', price: 120, category: 'meals',
    description: 'Crispy golden crepe filled with spiced potato masala. South Indian classic.',
    image_url: '/public/images/Masala Dosa.jpg',
    tags: ['indian', 'veg', 'south-indian', 'filling', 'meal'], calories: 380, display_order: 16,
    modifiers: [
      { name: 'Type', options: ['Regular Dosa', 'Paper Dosa', 'Butter Dosa'] },
      { name: 'Sides', options: ['Sambar + Chutney', 'Extra Sambar', 'Extra Chutney'] }
    ]
  },
  {
    id: 'ML02', name: 'Pav Bhaji', price: 110, category: 'meals',
    description: 'Spiced mixed vegetable bhaji served with buttered pav. A Mumbai staple.',
    image_url: '/public/images/Pav Bhaji.jpg',
    tags: ['indian', 'veg', 'filling', 'spicy', 'meal'], calories: 420, display_order: 17,
    modifiers: [
      { name: 'Butter', options: ['Normal Butter', 'Extra Butter', 'No Butter'] },
      { name: 'Pav', options: ['2 Pav', '3 Pav', '4 Pav'] }
    ]
  },
  {
    id: 'ML03', name: 'Paneer Wrap', price: 130, category: 'meals',
    description: 'Grilled paneer tikka with fresh veggies wrapped in a soft whole wheat roti.',
    image_url: '/public/images/Paneer Wrap.jpg',
    tags: ['indian', 'veg', 'filling', 'meal', 'popular'], calories: 390, display_order: 18,
    modifiers: [
      { name: 'Spice', options: ['Mild', 'Medium', 'Spicy'] },
      { name: 'Sauce', options: ['Mint Sauce', 'Garlic Mayo', 'Both'] },
      { name: 'Extra', options: ['None', 'Extra Paneer +30'] }
    ]
  },
  {
    id: 'ML04', name: 'Chole Bhature', price: 140, category: 'meals',
    description: 'Fluffy fried bread served with rich, spiced chickpea curry.',
    image_url: '/public/images/Chole Bhature.jpeg',
    tags: ['indian', 'veg', 'heavy', 'spicy', 'meal'], calories: 550, display_order: 19,
    modifiers: [
      { name: 'Bhature', options: ['1 Bhatura', '2 Bhaturas'] },
      { name: 'Sides', options: ['With Pickle', 'Without Pickle'] }
    ]
  },
  {
    id: 'ML05', name: 'Upma', price: 80, category: 'meals',
    description: 'Savory semolina porridge with vegetables, mustard seeds, and curry leaves.',
    image_url: '/public/images/Upma.jpg',
    tags: ['indian', 'veg', 'light', 'breakfast', 'south-indian'], calories: 200, display_order: 20,
    modifiers: [
      { name: 'Spice', options: ['Mild', 'Medium'] },
      { name: 'Extra', options: ['None', 'Extra Vegetables', 'Extra Cashews'] }
    ]
  },

  // DESSERTS
  {
    id: 'DS01', name: 'Chocolate Muffin', price: 80, category: 'desserts',
    description: 'Rich, moist chocolate muffin baked fresh daily with chocolate chips.',
    image_url: '/public/images/Chocolate Muffin.jpg',
    tags: ['sweet', 'baked', 'popular', 'indulgent'], calories: 350, display_order: 21,
    modifiers: [
      { name: 'Temperature', options: ['Room Temp', 'Warm'] },
      { name: 'Extra', options: ['None', 'With Ice Cream +40'] }
    ]
  },
  {
    id: 'DS02', name: 'Gulab Jamun', price: 60, category: 'desserts',
    description: 'Soft milk-solid dumplings soaked in rose-flavoured sugar syrup.',
    image_url: '/public/images/Gulab Jamun.jpg',
    tags: ['indian', 'sweet', 'traditional', 'warm'], calories: 180, display_order: 22,
    modifiers: [
      { name: 'Quantity', options: ['2 Pieces', '4 Pieces'] },
      { name: 'Extra', options: ['None', 'With Ice Cream +40'] }
    ]
  },
  {
    id: 'DS03', name: 'Brownie', price: 90, category: 'desserts',
    description: 'Dense, fudgy chocolate brownie with a crispy top and gooey centre.',
    image_url: '/public/images/Brownie.jpg',
    tags: ['sweet', 'baked', 'chocolate', 'indulgent'], calories: 320, display_order: 23,
    modifiers: [
      { name: 'Temperature', options: ['Room Temp', 'Warm'] },
      { name: 'Toppings', options: ['Plain', 'With Chocolate Sauce', 'With Ice Cream +40'] }
    ]
  },
  {
    id: 'DS04', name: 'Kulfi', price: 70, category: 'desserts',
    description: 'Traditional Indian ice cream — dense, creamy, and intensely flavoured.',
    image_url: '/public/images/Kulfi.jpg',
    tags: ['indian', 'sweet', 'cold', 'traditional'], calories: 150, display_order: 24,
    modifiers: [
      { name: 'Flavour', options: ['Malai', 'Mango', 'Pista', 'Rose'] },
      { name: 'Quantity', options: ['1 Stick', '2 Sticks'] }
    ]
  },
  {
    id: 'DS05', name: 'Rasgulla', price: 50, category: 'desserts',
    description: 'Soft, spongy cottage cheese balls soaked in light sugar syrup.',
    image_url: '/public/images/Rasgulla.jpg',
    tags: ['indian', 'sweet', 'light', 'traditional'], calories: 120, display_order: 25,
    modifiers: [
      { name: 'Quantity', options: ['2 Pieces', '4 Pieces'] },
      { name: 'Temperature', options: ['Chilled', 'Room Temp'] }
    ]
  },
];

async function seed() {
  try {
    // Initialize tables first
    await initDB();
    console.log('Tables created/verified.');

    // Seed menu items
    for (const item of menuItems) {
      await pool.query(
        `INSERT INTO menu_items (id, name, description, price, category, image_url, tags, calories, modifiers, inventory_count, display_order)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
         ON CONFLICT (id) DO NOTHING`,
        [
          item.id,
          item.name,
          item.description,
          item.price,
          item.category,
          item.image_url,
          JSON.stringify(item.tags),
          item.calories,
          JSON.stringify(item.modifiers),
          100,
          item.display_order,
        ]
      );
    }
    console.log(`Seeded ${menuItems.length} menu items.`);

    // Seed default business owner
    const hashedPassword = await bcrypt.hash('Admin@123', 10);
    await pool.query(
      `INSERT INTO business_users (email, password, name, role)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (email) DO NOTHING`,
      ['admin@bitekaro.com', hashedPassword, 'BiteKaro Admin', 'owner']
    );
    console.log('Default admin user seeded.');

    console.log('Database seeded successfully');
  } catch (err) {
    console.error('Error seeding database:', err.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

seed();
