// Real, salted password hashing replacing the homegrown, reversible
// `badCrypto` transform. Uses bcrypt's algorithm via the pure-JS bcryptjs
// implementation (same hashing scheme/API as `bcrypt`, no native build step).
const bcrypt = require('bcryptjs');
const config = require('../config');

async function hashPassword(plainTextPassword) {
    return bcrypt.hash(plainTextPassword, config.bcryptSaltRounds);
}

async function verifyPassword(plainTextPassword, passwordHash) {
    if (!passwordHash) return false;
    return bcrypt.compare(plainTextPassword, passwordHash);
}

module.exports = { hashPassword, verifyPassword };
