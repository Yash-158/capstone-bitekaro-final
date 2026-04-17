require('dotenv').config();

const express = require('express');
const cors = require('cors');
const path = require('path');
const http = require('http');
const { Server } = require('socket.io');

// Import route files
const menuRoutes = require('./routes/menu');
const orderRoutes = require('./routes/orders');
const loyaltyRoutes = require('./routes/loyalty');
const analyticsRoutes = require('./routes/analytics');
const authRoutes = require('./routes/auth');
const recommendRoutes = require('./routes/recommend');

// Import middleware
const errorHandler = require('./middleware/errorHandler');

// Import database
const { initDB } = require('./config/db');

const app = express();
const server = http.createServer(app);

// Initialize Socket.io for real-time order updates
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

// Make io accessible globally so routes can use it
global.io = io;
app.set('io', io);

// --- Middleware ---
app.use(cors({ origin: '*' }));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// --- Serve static files ---
app.use('/kiosk', express.static(path.join(__dirname, '..', 'kiosk')));
app.use('/dashboard', express.static(path.join(__dirname, '..', 'dashboard')));
app.use('/public', express.static(path.join(__dirname, '..', 'public')));

// --- Health check ---
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'BiteKaro API running', timestamp: new Date() });
});

// --- Razorpay key endpoint ---
app.get('/api/config/razorpay-key', (req, res) => {
  res.json({ key_id: process.env.RAZORPAY_KEY_ID });
});

// --- API Routes ---
app.use('/api/menu', menuRoutes);
app.use('/api/orders', orderRoutes);
app.use('/api/loyalty', loyaltyRoutes);
app.use('/api/analytics', analyticsRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/recommend', recommendRoutes);

// --- Global error handler ---
app.use(errorHandler);

// --- Socket.io connection ---
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// --- Start server ---
const PORT = process.env.PORT || 3000;

async function startServer() {
  try {
    await initDB();
    server.listen(PORT, () => {
      console.log(`BiteKaro server running on port ${PORT}`);
      console.log(`Kiosk: http://localhost:${PORT}/kiosk`);
      console.log(`Dashboard: http://localhost:${PORT}/dashboard/login.html`);
    });
  } catch (err) {
    console.error('Failed to start server:', err.message);
    process.exit(1);
  }
}

startServer();

module.exports = { app, server, io };
