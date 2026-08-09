// Data access only for the `courses` table.
const db = require('../config/database');

async function findActiveById(id) {
    return db.get('SELECT id, title, price, active FROM courses WHERE id = ? AND active = 1', [id]);
}

async function listPage({ limit, offset }) {
    return db.all('SELECT id, title, price, active FROM courses ORDER BY id LIMIT ? OFFSET ?', [
        limit,
        offset,
    ]);
}

module.exports = { findActiveById, listPage };
