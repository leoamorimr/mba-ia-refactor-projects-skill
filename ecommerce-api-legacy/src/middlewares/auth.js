// Minimal but real admin authorization gate: a shared-secret API key
// checked via an `x-admin-key` header. The project had no auth system at
// all, so this is the minimum viable mechanism that actually enforces
// authorization on the two previously wide-open sensitive routes (the
// financial report and the destructive user delete). See README.md for
// how to authenticate as admin.
const config = require('../config');
const { UnauthorizedError } = require('../utils/errors');

function requireAdmin(req, res, next) {
    const providedKey = req.header('x-admin-key');
    if (!providedKey || providedKey !== config.adminApiKey) {
        return next(new UnauthorizedError('Unauthorized: valid x-admin-key header required'));
    }
    return next();
}

module.exports = { requireAdmin };
