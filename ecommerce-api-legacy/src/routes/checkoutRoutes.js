// Routing only: parses nothing beyond what validation already put on
// `req.validated`, calls the controller, and shapes the HTTP response.
const express = require('express');
const { validateCheckout } = require('../middlewares/validators');
const createCheckoutController = require('../controllers/checkoutController');

function createCheckoutRoutes({ cacheService }) {
    const router = express.Router();
    const checkoutController = createCheckoutController({ cacheService });

    router.post('/api/checkout', validateCheckout, async (req, res, next) => {
        try {
            const result = await checkoutController.checkout(req.validated);
            res.status(200).json({ msg: result.message, enrollment_id: result.enrollmentId });
        } catch (err) {
            next(err);
        }
    });

    return router;
}

module.exports = createCheckoutRoutes;
