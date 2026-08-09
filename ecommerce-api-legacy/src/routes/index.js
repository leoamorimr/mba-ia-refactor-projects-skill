// Aggregates all domain route modules behind a single router the
// composition root mounts once. Grouped by domain instead of one giant
// route file, per the architecture guidelines.
const express = require('express');
const createCheckoutRoutes = require('./checkoutRoutes');
const adminRoutes = require('./adminRoutes');
const userRoutes = require('./userRoutes');

function createRouter({ cacheService }) {
    const router = express.Router();
    router.use(createCheckoutRoutes({ cacheService }));
    router.use(adminRoutes);
    router.use(userRoutes);
    return router;
}

module.exports = createRouter;
