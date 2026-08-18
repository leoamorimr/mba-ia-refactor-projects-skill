require('dotenv').config();

// All secrets and environment-dependent values are read from process.env here,
// and nowhere else in the codebase.
//
// ADMIN_API_KEY is a live credential wired into a real authorization check
// (middlewares/auth.js) — unlike a merely inert placeholder, silently
// falling back to a fixed string here would mean any deployment that forgets
// to set this env var ships with a publicly-known admin key. So we fail fast
// at boot instead: set ADMIN_API_KEY in your environment, or in a local
// `.env` file (loaded above via dotenv) for local dev/testing.
if (!process.env.ADMIN_API_KEY) {
    throw new Error(
        'Missing required environment variable ADMIN_API_KEY. Set it in your environment ' +
            'or in a local .env file before starting the app (see .env.example).'
    );
}

const config = {
    port: parseInt(process.env.PORT, 10) || 3000,

    // Shared-secret admin guard for sensitive routes (financial report, user delete).
    // See README.md for how to authenticate as admin.
    adminApiKey: process.env.ADMIN_API_KEY,

    bcryptSaltRounds: parseInt(process.env.BCRYPT_SALT_ROUNDS, 10) || 10,
};

module.exports = config;
