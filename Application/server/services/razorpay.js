const Razorpay = require('razorpay');
const crypto = require('crypto');

const razorpay = new Razorpay({
  key_id: process.env.RAZORPAY_KEY_ID,
  key_secret: process.env.RAZORPAY_KEY_SECRET,
});

async function createOrder(amount, receipt) {
  const options = {
    amount: Math.round(amount * 100), // rupees to paise
    currency: 'INR',
    receipt: receipt || `receipt_${Date.now()}`,
  };
  return razorpay.orders.create(options);
}

function verifyPayment(order_id, payment_id, signature) {
  const body = order_id + '|' + payment_id;
  const expectedSignature = crypto
    .createHmac('sha256', process.env.RAZORPAY_KEY_SECRET)
    .update(body)
    .digest('hex');
  return expectedSignature === signature;
}

module.exports = { createOrder, verifyPayment };
