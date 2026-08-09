// Data access only for the `audit_logs` table.
const db = require('../config/database');

async function record(action) {
    return db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [action]);
}

module.exports = { record };
