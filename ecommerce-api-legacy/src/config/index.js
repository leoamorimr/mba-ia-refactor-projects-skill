require('dotenv').config();

// All secrets and environment-dependent values are read from process.env here,
// and nowhere else in the codebase. The fallback values below are clearly
// labeled dev-only placeholders for local development convenience — they are
// NOT real secrets and must be overridden via a real .env / secrets manager
// in any deployed environment.
const config = {
    port: parseInt(process.env.PORT, 10) || 3000,

    dbUser: process.env.DB_USER || 'dev-only-db-user',
    dbPass: process.env.DB_PASS || 'dev-only-insecure-db-pass',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || 'dev-only-insecure-payment-key',
    smtpUser: process.env.SMTP_USER || 'dev-only-smtp-user@example.com',

    // Shared-secret admin guard for sensitive routes (financial report, user delete).
    // See README.md for how to authenticate as admin.
    adminApiKey: process.env.ADMIN_API_KEY || 'dev-only-insecure-admin-key',

    bcryptSaltRounds: parseInt(process.env.BCRYPT_SALT_ROUNDS, 10) || 10,
};

module.exports = config;
