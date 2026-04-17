/* ═══════════════════════════════════════════════════════════════
   BiteKaro Kiosk — Menu Logic
   ═══════════════════════════════════════════════════════════════ */

let allItems = [];
let currentCategory = 'all';

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  setupNavScroll();
  setupMoodStrip();
  setupCustomerChip();
  fetchAndRenderMenu();
  try {
    fetchRecommendations();
  } catch(e) {
    console.error('Error starting recommendations:', e);
  }
  document.addEventListener('cartUpdated', renderCartSidebar);
});

// ── Navbar scroll shadow ──
function setupNavScroll() {
  const nav = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 10);
  });
}

// ── Mood strip ──
function setupMoodStrip() {
  const mood = BiteKaroApp.mood;
  if (mood) {
    const strip = document.getElementById('moodStrip');
    strip.style.display = 'flex';
    strip.style.position = 'relative';
    const emojis = { happy: '😊', tired: '😴', thirsty: '🥵', hungry: '🍽️' };
    document.getElementById('moodPill').innerHTML =
      `${emojis[mood] || '😊'} ${mood.charAt(0).toUpperCase() + mood.slice(1)} mode <span class="mood-x" onclick="changeMood()">✕</span>`;
  }
}
function changeMood() {
  sessionStorage.removeItem('bk_mood');
  BiteKaroApp.mood = null;
  window.location.href = 'index.html';
}

// ── Customer chip ──
function setupCustomerChip() {
  if (BiteKaroApp.customer) {
    const chip = document.getElementById('customerChip');
    chip.style.display = 'inline-block';
    chip.textContent = `Hi ${BiteKaroApp.customer.name || 'there'}! 🌟 ${BiteKaroApp.customer.loyalty_points || 0} pts`;
  }
}

// ═══ FETCH & RENDER MENU ═══
async function fetchAndRenderMenu() {
  console.log('Fetching menu...');
  try {
    const data = await BiteKaroApp.fetchAPI('/menu');
    console.log('Menu response:', data);
    console.log('Items count:', data.all?.length);
    console.log('Rendering items...');
    allItems = data.all || [];
    window.menuItemsMap = {};
    allItems.forEach(item => {
      window.menuItemsMap[item.id] = item;
    });
    document.getElementById('menuLoading').style.display = 'none';
    const grid = document.getElementById('menuGrid');
    if (grid) { grid.style.display = 'grid'; }
    else { console.error('menuGrid container not found!'); }
    renderItems(allItems);
  } catch (err) {
    document.getElementById('menuLoading').innerHTML = '<p style="color:var(--error);">Failed to load menu. Please refresh.</p>';
    console.error('Menu fetch error:', err);
  }
}

function renderItems(items) {
  const grid = document.getElementById('menuGrid');
  const noResults = document.getElementById('noResults');

  if (!grid) {
    console.error("renderItems: menuGrid not found!");
    return;
  }

  if (items.length === 0) {
    grid.style.display = 'none';
    if(noResults) noResults.classList.remove('hidden');
    return;
  }
  grid.style.display = 'grid';
  if(noResults) noResults.classList.add('hidden');

  grid.innerHTML = items.map(item => {
    const tags = Array.isArray(item.tags) ? item.tags : [];
    const isPopular = tags.includes('popular');
    const isSpicy = tags.includes('spicy');
    const lowStock = item.inventory_count < 5 && item.inventory_count > 0;
    const unavailable = !item.is_available;
    const imgSrc = item.image_url ? encodeURI(item.image_url) : '';

    return `
      <div class="h-[280px] rounded-xl overflow-hidden relative group shadow-lg hover:-translate-y-2 transition-all duration-300 cursor-pointer" onclick="openCustomizationModal('${item.id}')">
        ${imgSrc ? `<img class="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" src="${imgSrc}" alt="${item.name}" loading="lazy" onerror="this.style.display='none'">` : '<div class="absolute inset-0 w-full h-full bg-slate-200"></div>'}
        <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent"></div>
        ${unavailable ? '<div class="absolute inset-0 bg-white/50 backdrop-blur-sm z-10 flex items-center justify-center"><span class="bg-slate-800 text-white px-3 py-1 rounded-full font-bold shadow-lg">Not Available</span></div>' : ''}
        <div class="absolute top-4 left-4 flex gap-2 z-20 flex-wrap">
          <span class="px-2 py-1 bg-green-500 text-white text-[10px] font-bold rounded">VEG</span>
          ${isPopular ? '<span class="px-2 py-1 bg-[#FFB300] text-slate-900 text-[10px] font-bold rounded">POPULAR</span>' : ''}
          ${isSpicy ? '<span class="px-2 py-1 bg-red-500 text-white text-[10px] font-bold rounded">SPICY</span>' : ''}
          ${lowStock ? `<span class="px-2 py-1 bg-slate-800/90 text-white text-[10px] font-bold rounded">Only ${item.inventory_count} left!</span>` : ''}
        </div>
        <button class="absolute top-4 right-4 bg-white size-10 rounded-full flex items-center justify-center text-primary shadow-lg hover:bg-primary hover:text-white transition-colors z-20 disabled:opacity-50" onclick="event.stopPropagation(); quickAdd('${item.id}')" ${unavailable ? 'disabled' : ''}>
          <span class="material-symbols-outlined font-bold">add</span>
        </button>
        <div class="absolute bottom-5 left-5 right-5 z-20">
          <h3 class="text-white text-lg font-bold font-poppins">${item.name}</h3>
          <div class="flex items-center justify-between mt-1">
             <p class="text-blue-300 font-bold">${BiteKaroApp.formatPrice(item.price)}</p>
             ${item.calories ? `<p class="text-white/60 text-xs">${item.calories} kcal</p>` : ''}
          </div>
        </div>
      </div>`;
  }).join('');
}

// ── Quick Add (no customization) ──
function quickAdd(itemId) {
  const item = allItems.find(i => i.id === itemId);
  if (!item || !item.is_available) return;
  const mods = item.modifiers || [];
  const defaults = {};
  mods.forEach(m => { if (m.options && m.options.length) defaults[m.name] = m.options[0]; });
  BiteKaroApp.addToCart({
    item_id: item.id, item_name: item.name, price: item.price,
    image_url: item.image_url, category: item.category
  }, defaults, 1);
  BiteKaroApp.showToast(`${item.name} added to cart!`, 'success');
}

// ═══ CATEGORY FILTER ═══
function filterByCategory(cat, btn) {
  currentCategory = cat;
  document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const filtered = cat === 'all' ? allItems : allItems.filter(i => i.category === cat);
  renderItems(filtered);
}

// ═══ SEARCH ═══
function searchItems(q) {
  const query = q.toLowerCase().trim();
  if (!query) { renderItems(currentCategory === 'all' ? allItems : allItems.filter(i => i.category === currentCategory)); return; }
  const filtered = allItems.filter(item => {
    const tags = Array.isArray(item.tags) ? item.tags : [];
    return item.name.toLowerCase().includes(query) ||
           (item.description || '').toLowerCase().includes(query) ||
           tags.some(t => t.toLowerCase().includes(query));
  });
  renderItems(filtered);
}

// ═══ AI RECOMMENDATIONS ═══
async function fetchRecommendations() {
  console.log('Fetching recommendations...');
  const section = document.getElementById('recommendations-section');
  const scroll = document.getElementById('recommendations-container');
  const sub = document.getElementById('recoSub');

  if (!section || !scroll) return;
  if (!BiteKaroApp.mood) {
    section.style.display = 'none';
    return;
  }

  section.style.display = 'block';
  if (sub) sub.textContent = `Based on your ${BiteKaroApp.mood} mood`;

  showRecSkeletons();

  try {
    let orderHistory = [];
    try { orderHistory = JSON.parse(sessionStorage.getItem('bk_order_history') || '[]'); } catch(e) {}

    const body = {
      customer_id: BiteKaroApp.customer?.id || null,
      cart_items: BiteKaroApp.cart.map(i => i.item_id),
      mood: BiteKaroApp.mood || 'happy',
      hour: BiteKaroApp.getCurrentHour(),
      month: BiteKaroApp.getCurrentMonth(),
      top_k: 5,
      order_history: orderHistory
    };
    
    console.log('Request body:', JSON.stringify(body));

    const data = await BiteKaroApp.fetchAPI('/recommend', {
      method: 'POST',
      body: body
    });
    
    console.log('Response:', data);
    console.log('Recs count:', data.recommendations?.length);

    renderRecommendations(data.recommendations);
  } catch (err) {
    section.style.display = 'none';
    console.warn('Reco fetch error:', err);
  }
}

function showRecSkeletons() {
  const container = document.getElementById('recommendations-container')
  if (!container) return
  container.innerHTML = Array(5).fill(`
    <div class="rec-card skeleton-card">
      <div class="skeleton-img"></div>
    </div>
  `).join('')
}

function getRecImageUrl(rec) {
  const menuItem = window.menuItemsMap
                   ? window.menuItemsMap[rec.item_id]
                   : null
  if (menuItem && menuItem.image_url) {
    return encodeURI(menuItem.image_url)
  }
  if (rec.image_url) {
    return encodeURI(rec.image_url)
  }
  const extensionMap = {
    'CB01': 'jpeg',
    'CB05': 'jpeg',
    'ML04': 'jpeg',
  }
  const ext = extensionMap[rec.item_id] || 'jpg'
  const name = rec.item_name || ''
  return encodeURI('/public/images/' + name + '.' + ext)
}

function renderRecommendations(recs) {
  const container = document.getElementById('recommendations-container')
  if (!container) return
  
  if (!recs || recs.length === 0) {
    document.getElementById('recommendations-section').style.display = 'none'
    return
  }
  
  document.getElementById('recommendations-section').style.display = 'block'
  
  container.innerHTML = recs.map(rec => {
    const imageUrl = getRecImageUrl(rec);
    return `
      <div class="rec-card" onclick="openCustomizationModal('${rec.item_id}')">
        <div class="rec-card-img" style="background-image: url('${imageUrl}')">
          <div class="rec-card-overlay">
            <p class="rec-item-name">${rec.item_name}</p>
            <p class="rec-item-price">Rs.${rec.price}</p>
            <p class="rec-item-reason">${rec.reason}</p>
          </div>
          <button class="rec-add-btn" 
            onclick="event.stopPropagation(); quickAddRecommendation('${rec.item_id}')">
            +
          </button>
        </div>
      </div>
    `
  }).join('')
}

function quickAddRecommendation(itemId) {
  const item = window.menuItemsMap ? window.menuItemsMap[itemId] : null;
  if (!item) return
  BiteKaroApp.addToCart(
    {
      item_id: item.id,
      item_name: item.name,
      price: item.price,
      image_url: item.image_url,
      category: item.category
    },
    {},
    1
  )
  BiteKaroApp.showToast(item.name + ' added to cart!', 'success')
  fetchRecommendations()
}

// ═══ CUSTOMIZATION MODAL ═══
let modalItem = null;
let modalQty = 1;
let modalSelections = {};

function openCustomizationModal(itemId) {
  const item = allItems.find(i => i.id === itemId);
  if (!item || !item.is_available) return;
  modalItem = item;
  modalQty = 1;
  modalSelections = {};

  const mods = Array.isArray(item.modifiers) ? item.modifiers : [];
  mods.forEach(m => { if (m.options && m.options.length) modalSelections[m.name] = m.options[0]; });

  const imgSrc = item.image_url ? encodeURI(item.image_url) : '';

  const modHTML = mods.map(m => `
    <div class="modifier-group">
      <label>${m.name}</label>
      <div class="modifier-options">
        ${m.options.map((opt, i) => `
          <button class="modifier-pill ${i === 0 ? 'selected' : ''}"
            onclick="selectModifier('${m.name}', '${opt}', this)">${opt}</button>
        `).join('')}
      </div>
    </div>
  `).join('');

  document.getElementById('modalContent').innerHTML = `
    <div style="position:relative;">
      ${imgSrc ? `<img class="modal-img" src="${imgSrc}" alt="${item.name}" onerror="this.style.display='none'">` : '<div class="modal-img" style="background:var(--gradient-hero);"></div>'}
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <h3>${item.name}</h3>
      <p class="modal-desc">${item.description || ''}</p>
      ${item.calories ? `<span class="modal-cal">🔥 ${item.calories} cal</span>` : ''}
      <div class="modal-base-price">${BiteKaroApp.formatPrice(item.price)}</div>
      ${modHTML}
      <div class="qty-row">
        <span>Quantity</span>
        <div class="qty-controls">
          <button class="qty-btn" onclick="changeModalQty(-1)">−</button>
          <span class="qty-value" id="modalQtyVal">${modalQty}</span>
          <button class="qty-btn" onclick="changeModalQty(1)">+</button>
        </div>
      </div>
      <textarea class="special-note-input" id="modalNote" placeholder="Any special requests..."></textarea>
    </div>
    <div class="modal-footer">
      <button class="modal-add-btn" id="modalAddBtn" onclick="addFromModal()">
        Add ${modalQty} ${item.name} — ${BiteKaroApp.formatPrice(item.price * modalQty)}
      </button>
    </div>
  `;

  document.getElementById('modalOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function selectModifier(group, option, btn) {
  modalSelections[group] = option;
  btn.parentElement.querySelectorAll('.modifier-pill').forEach(p => p.classList.remove('selected'));
  btn.classList.add('selected');
}

function changeModalQty(delta) {
  modalQty = Math.max(1, Math.min(10, modalQty + delta));
  document.getElementById('modalQtyVal').textContent = modalQty;
  updateModalBtn();
}

function updateModalBtn() {
  if (!modalItem) return;
  document.getElementById('modalAddBtn').textContent =
    `Add ${modalQty} ${modalItem.name} — ${BiteKaroApp.formatPrice(modalItem.price * modalQty)}`;
}

function addFromModal() {
  if (!modalItem) return;
  BiteKaroApp.addToCart({
    item_id: modalItem.id, item_name: modalItem.name, price: modalItem.price,
    image_url: modalItem.image_url, category: modalItem.category
  }, { ...modalSelections }, modalQty);
  BiteKaroApp.showToast(`${modalItem.name} added to cart!`, 'success');
  closeModal();
  fetchRecommendations(); // Refresh recs since cart changed
}

function closeModal() {
  document.getElementById('modalOverlay').classList.remove('open');
  document.body.style.overflow = '';
  modalItem = null;
}

// ═══ CART SIDEBAR ═══
function toggleCartSidebar(open) {
  document.getElementById('sidebarOverlay').classList.toggle('open', open);
  document.getElementById('cartSidebar').classList.toggle('open', open);
  if (open) renderCartSidebar();
}

function renderCartSidebar() {
  const items = BiteKaroApp.cart;
  const container = document.getElementById('sidebarItems');
  const footer = document.getElementById('sidebarFooter');
  const count = document.getElementById('sidebarCount');
  const total = document.getElementById('sidebarTotal');

  count.textContent = `(${BiteKaroApp.getCartCount()} items)`;

  if (items.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🥣</div>
        <p class="empty-state-title">Your cart is empty</p>
        <p class="empty-state-desc">Add items from the menu to get started</p>
        <button class="btn-primary btn-sm" onclick="toggleCartSidebar(false)">Start Ordering</button>
      </div>`;
    footer.style.display = 'none';
    return;
  }

  footer.style.display = 'block';
  total.textContent = BiteKaroApp.formatPrice(BiteKaroApp.getCartTotal());

  container.innerHTML = items.map(item => {
    const custStr = Object.values(item.customizations || {}).filter(Boolean).join(', ');
    const imgSrc = item.image_url ? encodeURI(item.image_url) : '';
    return `
      <div class="sidebar-item border-${item.category}">
        ${imgSrc ? `<img class="sidebar-item-img" src="${imgSrc}" alt="${item.item_name}" onerror="this.style.display='none'">` : '<div class="sidebar-item-img" style="background:var(--blue-pale);border-radius:12px;"></div>'}
        <div class="sidebar-item-info">
          <div class="sidebar-item-name">${item.item_name}</div>
          ${custStr ? `<div class="sidebar-item-custom">${custStr}</div>` : ''}
        </div>
        <div class="sidebar-item-actions">
          <button class="sidebar-qty-btn" onclick="sidebarQty('${item.cartItemId}', -1)">−</button>
          <span class="sidebar-qty-val">${item.quantity}</span>
          <button class="sidebar-qty-btn" onclick="sidebarQty('${item.cartItemId}', 1)">+</button>
        </div>
        <span class="sidebar-item-price">${BiteKaroApp.formatPrice(item.item_total)}</span>
        <button class="sidebar-trash" onclick="sidebarRemove('${item.cartItemId}')">🗑</button>
      </div>`;
  }).join('');
}

function sidebarQty(cartItemId, delta) {
  const item = BiteKaroApp.cart.find(c => c.cartItemId === cartItemId);
  if (item) BiteKaroApp.updateCartQuantity(cartItemId, item.quantity + delta);
  renderCartSidebar();
}

function sidebarRemove(cartItemId) {
  BiteKaroApp.removeFromCart(cartItemId);
  renderCartSidebar();
  fetchRecommendations();
}
