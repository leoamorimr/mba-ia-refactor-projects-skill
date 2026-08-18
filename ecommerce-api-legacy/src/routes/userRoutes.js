// Routing only. `requireAdmin` fixes the unauthenticated-destructive-endpoint
// finding: this route now rejects any request without a valid admin key.
const express = require('express');
const { requireAdmin } = require('../middlewares/auth');
const { validateUserIdParam } = require('../middlewares/validators');
const userController = require('../controllers/userController');

const router = express.Router();

router.delete('/api/users/:id', requireAdmin, validateUserIdParam, async (req, res, next) => {
    try {
        const result = await userController.deleteUser(req.validated.id);
        res.status(200).json({ message: result.message });
    } catch (err) {
        next(err);
    }
});

module.exports = router;
