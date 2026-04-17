/* ═══════════════════════════════════════════════════════════════
   BiteKaro Kiosk — Payment Logic
   ═══════════════════════════════════════════════════════════════ */

let pendingOrder = null;
let selectedMethod = null;
let razorpayKeyId = null;

document.addEventListener('DOMContentLoaded', async () => {
  const stored = sessionStorage.getItem('bk_pending_order');
  if (!stored) { window.location.href = 'cart.html'; return; }
  pendingOrder = JSON.parse(stored);

  // Display
  const count = pendingOrder.items.reduce((s, i) => s + i.quantity, 0);
  document.getElementById('orderSummaryLabel').textContent = `${count} item${count > 1 ? 's' : ''}`;
  document.getElementById('paymentTotal').textContent = BiteKaroApp.formatPrice(pendingOrder.total);
  document.getElementById('razorpayAmount').textContent = BiteKaroApp.formatPrice(pendingOrder.total);

  // Order details
  document.getElementById('orderDetails').innerHTML = pendingOrder.items.map(i =>
    `<div class="flex justify-between mb-1" style="font-size:13px;">
      <span>${i.item_name} x${i.quantity}</span>
      <span class="fw-600">${BiteKaroApp.formatPrice(i.item_total)}</span>
    </div>`
  ).join('');

  // Fetch Razorpay key
  try {
    const config = await BiteKaroApp.fetchAPI('/config/razorpay-key');
    razorpayKeyId = config.key_id;
  } catch(e) { console.warn('Could not fetch Razorpay key'); }
});

function toggleOrderDetails() {
  const d = document.getElementById('orderDetails');
  const a = document.getElementById('expandArrow');
  d.classList.toggle('hidden');
  a.style.transform = d.classList.contains('hidden') ? '' : 'rotate(180deg)';
}

function selectPayment(method) {
  selectedMethod = method;
  document.querySelectorAll('.payment-card').forEach(c => c.classList.remove('selected'));
  document.getElementById('razorpayBtn').style.display = 'none';
  document.getElementById('cashBtn').style.display = 'none';

  if (method === 'razorpay') {
    document.getElementById('razorpayCard').classList.add('selected');
    document.getElementById('razorpayBtn').style.display = 'flex';
  } else if (method === 'cash') {
    document.getElementById('cashCard').classList.add('selected');
    document.getElementById('cashBtn').style.display = 'flex';
  }
}

// ═══ RAZORPAY ═══
async function handleRazorpayPayment() {
  if (!pendingOrder) return;
  showProcessing(true);

  try {
    // Step 1: Create order
    const rzpOrder = await BiteKaroApp.fetchAPI('/orders/create-payment', {
      method: 'POST',
      body: { amount: pendingOrder.total, order_description: 'BiteKaro Cafe Order' }
    });
    showProcessing(false);

    // Step 2: Load Razorpay script if needed
    await loadRazorpayScript();

    // Step 3: Open checkout
    const options = {
      key: rzpOrder.key_id || razorpayKeyId,
      amount: Math.round(pendingOrder.total * 100),
      currency: 'INR',
      name: 'BiteKaro',
      description: 'Cafe Order',
      image: '/public/images/logo.png',
      order_id: rzpOrder.razorpay_order_id,
      prefill: {
        name: BiteKaroApp.customer?.name || '',
        contact: BiteKaroApp.customer?.phone || ''
      },
      theme: { color: '#1565C0' },
      handler: function(response) { verifyAndPlaceOrder(response, rzpOrder.razorpay_order_id); },
      modal: { ondismiss: function() { BiteKaroApp.showToast('Payment cancelled', 'info'); } }
    };
    const rzp = new Razorpay(options);
    rzp.open();
  } catch (err) {
    showProcessing(false);
    BiteKaroApp.showToast('Failed to start payment. Try again.', 'error');
    console.error('Razorpay error:', err);
  }
}

function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) { resolve(); return; }
    const s = document.createElement('script');
    s.src = 'https://checkout.razorpay.com/v1/checkout.js';
    s.onload = resolve;
    s.onerror = resolve;
    document.head.appendChild(s);
  });
}

async function verifyAndPlaceOrder(response, orderId) {
  showProcessing(true);
  try {
    const verification = await BiteKaroApp.fetchAPI('/orders/verify-payment', {
      method: 'POST',
      body: {
        razorpay_order_id: orderId,
        razorpay_payment_id: response.razorpay_payment_id,
        razorpay_signature: response.razorpay_signature
      }
    });
    if (verification.valid) {
      await placeOrder('razorpay', 'paid', response.razorpay_payment_id);
    } else {
      showProcessing(false);
      BiteKaroApp.showToast('Payment verification failed. Please try again.', 'error');
    }
  } catch(err) {
    showProcessing(false);
    BiteKaroApp.showToast('Verification error. Contact support.', 'error');
  }
}

// ═══ CASH ═══
async function handleCashPayment() {
  if (!pendingOrder) return;
  showProcessing(true);
  await placeOrder('cash', 'pending', null);
}

// ═══ PLACE ORDER ═══
async function placeOrder(paymentMethod, paymentStatus, paymentId) {
  try {
    // Redeem loyalty if needed
    if (pendingOrder.loyalty_points_used > 0 && BiteKaroApp.customer?.id) {
      try {
        await BiteKaroApp.fetchAPI('/loyalty/redeem', {
          method: 'POST',
          body: { customer_id: BiteKaroApp.customer.id, points_to_redeem: pendingOrder.loyalty_points_used }
        });
      } catch(e) { console.warn('Redeem error:', e.message); }
    }

    const order = await BiteKaroApp.fetchAPI('/orders', {
      method: 'POST',
      body: {
        customer_id: pendingOrder.customer_id,
        items: pendingOrder.items,
        subtotal: pendingOrder.subtotal,
        discount: pendingOrder.discount,
        total: pendingOrder.total,
        payment_method: paymentMethod,
        payment_status: paymentStatus,
        payment_id: paymentId,
        mood: pendingOrder.mood,
        special_instructions: pendingOrder.special_instructions
      }
    });

    sessionStorage.setItem('bk_placed_order', JSON.stringify(order.order || order));
    BiteKaroApp.clearCart();
    window.location.href = 'confirmation.html';
  } catch(err) {
    showProcessing(false);
    BiteKaroApp.showToast('Failed to place order. Please try again.', 'error');
    console.error('Order error:', err);
  }
}

function showProcessing(show) {
  document.getElementById('paymentProcessing').classList.toggle('hidden', !show);
  document.getElementById('paymentOptions').classList.toggle('hidden', show);
}
