// One centralized Express error handler registered once at the app level,
// replacing every route/callback re-implementing its own
// `if (err) return res.status(500).send(...)` logic.
const logger = require('../utils/logger');
const { AppError } = require('../utils/errors');

// eslint-disable-next-line no-unused-vars
module.exports = function errorHandler(err, req, res, next) {
    if (err instanceof AppError) {
        logger.warn(err.message, { statusCode: err.statusCode, path: req.originalUrl });
        return res.status(err.statusCode).json({ error: err.message });
    }

    logger.error('Unhandled error', { message: err.message, stack: err.stack, path: req.originalUrl });
    return res.status(500).json({ error: 'Internal server error' });
};
