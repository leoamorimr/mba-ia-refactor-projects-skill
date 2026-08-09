// Routing only. `requireAdmin` fixes the unauthenticated-admin-endpoint
// finding: this route now rejects any request without a valid admin key.
const express = require('express');
const { requireAdmin } = require('../middlewares/auth');
const { validateReportQuery } = require('../middlewares/validators');
const financialReportController = require('../controllers/financialReportController');

const router = express.Router();

router.get('/api/admin/financial-report', requireAdmin, validateReportQuery, async (req, res, next) => {
    try {
        const report = await financialReportController.getReport(req.validated);
        res.status(200).json(report);
    } catch (err) {
        next(err);
    }
});

module.exports = router;
