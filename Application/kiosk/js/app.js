/* ═══════════════════════════════════════════════════════════════
   BiteKaro Kiosk — Global State & Utilities
   ═══════════════════════════════════════════════════════════════ */

const BiteKaroApp = {
  cart: [],
  customer: null,
  mood: null,
  API_BASE: 'http://localhost:3000/api',

  // ── Init ──
  init() {
    this.loadFromStorage();
    this.updateCartUI();
  },

  // ── Cart Methods ──
  addToCart(item, customizations = {}, quantity = 1) {
    const custKey = JSON.stringify(customizations);
    const existing = this.cart.find(
      c => c.item_id === item.item_id && JSON.stringify(c.customizations) === custKey
    );
    if (existing) {
      existing.quantity += quantity;
      existing.item_total = existing.price * existing.quantity;
    } else {
      this.cart.push({
        cartItemId: Date.now() + Math.random().toString(36).slice(2, 6),
        item_id: item.item_id || item.id,
        item_name: item.item_name || item.name,
        price: parseFloat(item.price),
        image_url: item.image_url || '',
        category: item.category || '',
        customizations,
        quantity,
        item_total: parseFloat(item.price) * quantity
      });
    }
    this.saveToStorage();
    this.updateCartUI();
  },

  removeFromCart(cartItemId) {
    this.cart = this.cart.filter(c => c.cartItemId !== cartItemId);
    this.saveToStorage();
    this.updateCartUI();
  },

  updateCartQuantity(cartItemId, newQuantity) {
    if (newQuantity <= 0) {
      this.removeFromCart(cartItemId);
      return;
    }
    const item = this.cart.find(c => c.cartItemId === cartItemId);
    if (item) {
      item.quantity = newQuantity;
      item.item_total = item.price * newQuantity;
      this.saveToStorage();
      this.updateCartUI();
    }
  },

  getCartTotal() {
    return this.cart.reduce((sum, i) => sum + i.item_total, 0);
  },

  getCartCount() {
    return this.cart.reduce((sum, i) => sum + i.quantity, 0);
  },

  clearCart() {
    this.cart = [];
    this.saveToStorage();
    this.updateCartUI();
  },

  // ── Storage ──
  saveToStorage() {
    try {
      sessionStorage.setItem('bk_cart', JSON.stringify(this.cart));
      if (this.customer) sessionStorage.setItem('bk_customer', JSON.stringify(this.customer));
      if (this.mood) sessionStorage.setItem('bk_mood', this.mood);
    } catch (e) { /* storage full fallback */ }
  },

  loadFromStorage() {
    try {
      const cart = sessionStorage.getItem('bk_cart');
      if (cart) this.cart = JSON.parse(cart);
    } catch (e) { this.cart = []; }
    try {
      const cust = sessionStorage.getItem('bk_customer');
      if (cust) this.customer = JSON.parse(cust);
    } catch (e) { this.customer = null; }
    try {
      this.mood = sessionStorage.getItem('bk_mood') || null;
    } catch (e) { this.mood = null; }
  },

  // ── Format ──
  formatPrice(amount) {
    return 'Rs.' + parseFloat(amount).toFixed(0);
  },

  // ── Toast ──
  showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span> ${message}`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('out');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  },

  // ── Time Helpers ──
  getCurrentHour() { return new Date().getHours(); },
  getCurrentMonth() { return new Date().getMonth() + 1; },

  // ── Cart UI ──
  updateCartUI() {
    document.querySelectorAll('.cart-badge').forEach(badge => {
      const count = this.getCartCount();
      badge.textContent = count;
      badge.style.display = count > 0 ? 'flex' : 'none';
      badge.classList.remove('pulse');
      void badge.offsetWidth;
      if (count > 0) badge.classList.add('pulse');
    });
    document.dispatchEvent(new CustomEvent('cartUpdated'));
  },

  // ── API ──
  async fetchAPI(endpoint, options = {}) {
    const { body, ...rest } = options;
    const config = {
      headers: { 'Content-Type': 'application/json' },
      ...rest
    };
    if (body) config.body = JSON.stringify(body);
    const res = await fetch(this.API_BASE + endpoint, config);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || data.message || 'API error');
    return data;
  }
};

window.BiteKaroApp = BiteKaroApp;
document.addEventListener('DOMContentLoaded', () => BiteKaroApp.init());
