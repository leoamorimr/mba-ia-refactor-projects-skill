// Data access only for the `payments` table.
const db = require('../config/database');
const { findByIdsIn } = require('../utils/query');

const PAYMENT_STATUS = { PAID: 'PAID' };

async function create({ enrollmentId, amount, status }) {
    const result = await db.run(
        'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
        [enrollmentId, amount, status]
    );
    return result.lastID;
}

// Fetches every payment for a batch of enrollment ids in a single query,
// instead of the original one-query-per-enrollment N+1 pattern.
async function findByEnrollmentIds(enrollmentIds) {
    return findByIdsIn('payments', 'enrollment_id', enrollmentIds, [
        'id',
        'enrollment_id',
        'amount',
        'status',
    ]);
}

async function deleteByEnrollmentUserId(userId) {
    return db.run(
        'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)',
        [userId]
    );
}

module.exports = { create, findByEnrollmentIds, deleteByEnrollmentUserId, PAYMENT_STATUS };
