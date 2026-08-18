// Data access only for the `users` table — no HTTP concepts, no business
// rules, just parameterized queries.
const db = require('../config/database');
const { findByIdsIn } = require('../utils/query');

async function findByEmail(email) {
    return db.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]);
}

async function findById(id) {
    return db.get('SELECT id, name, email, pass FROM users WHERE id = ?', [id]);
}

async function findByIds(ids) {
    return findByIdsIn('users', 'id', ids, ['id', 'name', 'email']);
}

async function create({ name, email, passwordHash }) {
    const result = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
        name,
        email,
        passwordHash,
    ]);
    return result.lastID;
}

async function deleteById(id) {
    return db.run('DELETE FROM users WHERE id = ?', [id]);
}

module.exports = { findByEmail, findById, findByIds, create, deleteById };
