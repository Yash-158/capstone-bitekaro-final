/* ═══════════════════════════════════════════════════════════════
   BiteKaro Kiosk — Cart Logic
   ═══════════════════════════════════════════════════════════════ */

let loyaltyDiscount = 0;
let redeemPoints = 0;

document.addEventListener('DOMContentLoaded', () => {
  renderCart();
  calculateTotals();
  loadCrossSell();
  prefillCustomerFromSession();
  if (BiteKaroApp.customer) showLoggedInLoyalty(BiteKaroApp.customer);
  else if (BiteKaroApp.customer?.phone) document.getElementById('loyaltyPhoneInput').value = BiteKaroApp.customer.phone;
});

// ═══ MANDATORY CHECKOUT CUSTOMER LOGIC ═══
function prefillCustomerFromSession() {
  const savedPhone = sessionStorage.getItem('bk_phone')
  const savedCustomer = sessionStorage.getItem('bk_customer')
  
  if (savedCustomer) {
    const customer = JSON.parse(savedCustomer)
    showCustomerFound(customer)
    return
  }
  if (savedPhone) {
    document.getElementById('cart-phone').value = savedPhone
    lookupCustomer()
  }
}

async function lookupCustomer() {
  const phone = document.getElementById('cart-phone').value.trim()
  if (phone.length !== 10) return
  
  try {
    const res = await fetch('/api/orders/history/' + phone)
    const data = await res.json()
    
    if (data.exists && data.customer) {
      // Existing customer — show their details, no name input needed
      BiteKaroApp.customer = data.customer
      sessionStorage.setItem('bk_customer', JSON.stringify(data.customer))
      sessionStorage.setItem('bk_phone', phone)
      sessionStorage.setItem('bk_order_history', 
        JSON.stringify(data.order_history || []))
      showCustomerFound(data.customer)
    } else {
      // New customer — show name input
      sessionStorage.setItem('bk_phone', phone)
      document.getElementById('customer-name-area').style.display = 'block'
      document.getElementById('name-label').textContent = 
        'Your Name * (New customer — welcome!)'
      document.getElementById('verify-customer-btn').style.display = 'block'
      document.getElementById('customer-found-card').style.display = 'none'
    }
  } catch(e) {
    console.error('Customer lookup failed:', e)
  }
}

function showCustomerFound(customer) {
  document.getElementById('customer-name-area').style.display = 'none'
  document.getElementById('verify-customer-btn').style.display = 'none'
  document.getElementById('customer-found-card').style.display = 'block'
  document.getElementById('found-customer-name').textContent = 
    customer.name || 'Valued Customer'
  const pts = customer.loyalty_points || 0
  document.getElementById('found-customer-points').textContent = 
    pts + ' points available'
  document.getElementById('cart-phone').value = customer.phone || sessionStorage.getItem('bk_phone') || ''
  BiteKaroApp.customer = customer
}

async function verifyAndSetCustomer() {
  const phone = document.getElementById('cart-phone').value.trim()
  const name = document.getElementById('cart-name').value.trim()
  
  if (!name) {
    document.getElementById('cart-name').style.borderColor = '#FF6B35'
    document.getElementById('cart-name').placeholder = 'Name is required'
    return
  }
  document.getElementById('cart-name').style.borderColor = ''
  
  // Register new customer
  try {
    const res = await fetch('/api/loyalty/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, name })
    })
    const data = await res.json()
    if (data.customer) {
      BiteKaroApp.customer = data.customer
      sessionStorage.setItem('bk_customer', JSON.stringify(data.customer))
      showCustomerFound(data.customer)
    }
  } catch(e) {
    // Still allow checkout with name+phone even if register fails
    BiteKaroApp.customer = { phone, name, loyalty_points: 0 }
    showCustomerFound(BiteKaroApp.customer)
  }
}

function resetCustomerForm() {
  BiteKaroApp.customer = null
  sessionStorage.removeItem('bk_customer')
  sessionStorage.removeItem('bk_phone')
  document.getElementById('cart-phone').value = ''
  document.getElementById('customer-name-area').style.display = 'none'
  document.getElementById('customer-found-card').style.display = 'none'
  document.getElementById('verify-customer-btn').style.display = 'none'
}

function isCustomerReady() {
  return BiteKaroApp.customer !== null && BiteKaroApp.customer !== undefined
}


// ═══ RENDER CART ═══
function renderCart() {
  const cart = BiteKaroApp.cart;
  const list = document.getElementById('cartItemsList');
  const empty = document.getElementById('emptyCart');
  const badge = document.getElementById('itemCountBadge');
  const btn = document.getElementById('proceedBtn');

  badge.textContent = `(${BiteKaroApp.getCartCount()} items)`;

  if (cart.length === 0) {
    list.innerHTML = '';
    empty.classList.remove('hidden');
    btn.disabled = true;
    return;
  }
  empty.classList.add('hidden');
  btn.disabled = false;

  list.innerHTML = cart.map(item => {
    const custStr = Object.values(item.customizations || {}).filter(Boolean).join(', ');
    const imgSrc = item.image_url ? encodeURI(item.image_url) : '';

    return `
      <div class="cart-item-row" data-category="${item.category}" data-cart-id="${item.cartItemId}">
        <img class="cart-item-thumb" 
             src="${imgSrc}" 
             alt="${item.item_name}" onerror="this.style.display='none'">
        <div class="cart-item-info">
          <p class="cart-item-name">${item.item_name}</p>
          <p class="cart-item-customizations">${custStr}</p>
          <p class="cart-item-price-each">${BiteKaroApp.formatPrice(item.price)} each</p>
        </div>
        <div class="cart-item-controls">
          <button class="qty-btn minus-btn" 
                  onclick="updateQty('${item.cartItemId}', -1)">−</button>
          <span class="qty-display">${item.quantity}</span>
          <button class="qty-btn plus-btn" 
                  onclick="updateQty('${item.cartItemId}', 1)">+</button>
        </div>
        <div class="cart-item-total">
          <p class="cart-item-total-price">${BiteKaroApp.formatPrice(item.item_total)}</p>
          <button class="cart-delete-btn" 
                  onclick="removeItem('${item.cartItemId}')">🗑</button>
        </div>
      </div>
    `;
  }).join('');
}

function updateQty(cartItemId, delta) {
  const item = BiteKaroApp.cart.find(c => c.cartItemId === cartItemId);
  if (item) BiteKaroApp.updateCartQuantity(cartItemId, item.quantity + delta);
  renderCart();
  calculateTotals();
}

function removeItem(cartItemId) {
  BiteKaroApp.removeFromCart(cartItemId);
  renderCart();
  calculateTotals();
  loadCrossSell();
}

// ═══ LOYALTY ═══
async function checkCartLoyalty() {
  const phone = document.getElementById('loyaltyPhoneInput').value.trim();
  const msg = document.getElementById('loyaltyMsg');
  if (!phone || phone.length < 10) { msg.innerHTML = '<span style="color:var(--error)">Enter a valid 10-digit number</span>'; return; }

  try {
    const data = await BiteKaroApp.fetchAPI('/loyalty/' + phone);
    if (data.exists) {
      BiteKaroApp.customer = data.customer;
      BiteKaroApp.saveToStorage();
      showLoggedInLoyalty(data.customer);
    } else {
      msg.innerHTML = '';
      document.getElementById('loyaltyNotLoggedIn').classList.add('hidden');
      document.getElementById('loyaltyRegisterForm').classList.remove('hidden');
      document.getElementById('customer-phone-display').value = phone;
    }
  } catch (err) {
    msg.innerHTML = '<span style="color:var(--error)">Could not check. Try again.</span>';
  }
}

async function registerCustomer() {
  const phone = document.getElementById('customer-phone-display').value;
  const name = document.getElementById('customer-name-input').value.trim();
  if (!name) { BiteKaroApp.showToast('Please enter your name', 'error'); return; }

  try {
    const data = await BiteKaroApp.fetchAPI('/loyalty/register', { method: 'POST', body: JSON.stringify({ phone, name }) });
    if (data.customer) {
      BiteKaroApp.customer = data.customer;
      BiteKaroApp.saveToStorage();
      document.getElementById('loyaltyRegisterForm').classList.add('hidden');
      showLoggedInLoyalty(data.customer);
      BiteKaroApp.showToast(`Welcome, ${name}! Account created 🎉`, 'success');
    }
  } catch(e) { BiteKaroApp.showToast('Registration failed.', 'error'); }
}

function showLoggedInLoyalty(customer) {
  document.getElementById('loyaltyNotLoggedIn').classList.add('hidden');
  document.getElementById('loyaltyLoggedIn').classList.remove('hidden');
  document.getElementById('welcomeCustomer').innerHTML = `
    <div style="font-size:15px;font-weight:600;color:var(--success);">Welcome ${customer.name || 'friend'}! 🎉</div>
    <div class="points-display">${customer.loyalty_points || 0} points</div>
    <div style="font-size:12px;color:var(--text-light);">${customer.total_orders || 0} orders placed</div>
  `;

  const points = customer.loyalty_points || 0;
  if (points >= 10) {
    const maxDiscount = Math.min(points, Math.floor(BiteKaroApp.getCartTotal() * 0.5));
    redeemPoints = maxDiscount;
    document.getElementById('redeemSection').classList.remove('hidden');
    document.getElementById('redeemLabel').textContent = `Use ${maxDiscount} points for Rs.${maxDiscount} off`;
  }
}

function toggleRedeem() {
  const btn = document.getElementById('redeemToggle');
  const isActive = btn.classList.toggle('active');
  loyaltyDiscount = isActive ? redeemPoints : 0;
  calculateTotals();
}

// ═══ TOTALS ═══
function calculateTotals() {
  const sub = BiteKaroApp.getCartTotal();
  const total = Math.max(sub - loyaltyDiscount, 0);
  document.getElementById('summarySubtotal').textContent = BiteKaroApp.formatPrice(sub);
  document.getElementById('summaryTotal').textContent = BiteKaroApp.formatPrice(total);
  const dr = document.getElementById('discountRow');
  if (loyaltyDiscount > 0) { dr.style.display = 'flex'; document.getElementById('summaryDiscount').textContent = `-Rs.${loyaltyDiscount}`; }
  else { dr.style.display = 'none'; }
}

// ═══ CROSS-SELL ═══
async function loadCrossSell() {
  const cart = BiteKaroApp.cart;
  const banner = document.getElementById('crossSellBanner');
  const container = document.getElementById('crossSellItems');
  if (cart.length === 0) { banner.classList.add('hidden'); return; }
  const hasBev = cart.some(i => i.category === 'hot_beverages' || i.category === 'cold_beverages');
  if (hasBev) { banner.classList.add('hidden'); return; }

  try {
    const data = await BiteKaroApp.fetchAPI('/recommend', {
      method: 'POST',
      body: { cart_items: cart.map(i => i.item_id), mood: BiteKaroApp.mood || 'happy', hour: BiteKaroApp.getCurrentHour(), month: BiteKaroApp.getCurrentMonth(), top_k: 4 }
    });
    const bevs = (data.recommendations || []).filter(r => r.category === 'hot_beverages' || r.category === 'cold_beverages').slice(0, 2);
    if (bevs.length > 0) {
      banner.classList.remove('hidden');
      container.innerHTML = bevs.map(b => `
        <button class="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg font-bold text-sm transition-colors tracking-wide shadow-sm flex-shrink-0 font-display" onclick="crossSellAdd('${b.item_id}', '${b.item_name}', ${b.price}, '${b.category}')">
          Add ${b.item_name} · ${BiteKaroApp.formatPrice(b.price)}
        </button>`).join('');
    } else { banner.classList.add('hidden'); }
  } catch(e) { banner.classList.add('hidden'); }
}

function crossSellAdd(id, name, price, category) {
  BiteKaroApp.addToCart({ item_id: id, item_name: name, price, category }, {}, 1);
  renderCart(); calculateTotals(); loadCrossSell();
}

// ═══ PROCEED ═══
function proceedToPayment() {
  if (BiteKaroApp.cart.length === 0) return;
  
  if (!isCustomerReady()) {
    // Shake the customer section to draw attention
    const section = document.getElementById('customer-section')
    if (section) {
      section.style.animation = 'shake 0.4s ease'
      setTimeout(() => section.style.animation = '', 500)
      section.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
    // Show error message
    BiteKaroApp.showToast('Please enter your phone number to continue', 'error')
    return
  }
  
  const orderData = {
    customer_id: BiteKaroApp.customer?.id || null,
    items: BiteKaroApp.cart,
    subtotal: BiteKaroApp.getCartTotal(),
    discount: loyaltyDiscount,
    total: Math.max(BiteKaroApp.getCartTotal() - loyaltyDiscount, 0),
    payment_method: null,
    mood: BiteKaroApp.mood || null,
    special_instructions: document.getElementById('specialInstructions').value.trim(),
    loyalty_points_used: loyaltyDiscount > 0 ? redeemPoints : 0
  };
  sessionStorage.setItem('bk_pending_order', JSON.stringify(orderData));
  window.location.href = 'payment.html';
}
