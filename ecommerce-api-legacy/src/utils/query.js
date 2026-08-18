// Shared helper for the "batch fetch rows whose column is one of a list of
// ids" pattern that was previously duplicated (bail out on an empty array,
// build a `?,?,?` placeholder string, run a `SELECT ... WHERE col IN (...)`)
// across enrollmentModel, paymentModel, and userModel.
const db = require('../config/database');

// table/column/selectColumns are trusted, hardcoded call-site literals
// (never user input) — only `ids` are request-derived, and those are
// still passed as parameterized values, never string-interpolated.
async function findByIdsIn(table, column, ids, selectColumns) {
    if (!ids.length) return [];
    const placeholders = ids.map(() => '?').join(',');
    const columns = selectColumns.join(', ');
    return db.all(`SELECT ${columns} FROM ${table} WHERE ${column} IN (${placeholders})`, ids);
}

module.exports = { findByIdsIn };
