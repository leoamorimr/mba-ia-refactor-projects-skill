// Data access only for the `enrollments` table.
const db = require('../config/database');

async function create({ userId, courseId }) {
    const result = await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [
        userId,
        courseId,
    ]);
    return result.lastID;
}

// Fetches every enrollment for a batch of course ids in a single query,
// instead of the original one-query-per-course N+1 pattern.
async function findByCourseIds(courseIds) {
    if (!courseIds.length) return [];
    const placeholders = courseIds.map(() => '?').join(',');
    return db.all(
        `SELECT id, user_id, course_id FROM enrollments WHERE course_id IN (${placeholders})`,
        courseIds
    );
}

async function deleteByUserId(userId) {
    return db.run('DELETE FROM enrollments WHERE user_id = ?', [userId]);
}

module.exports = { create, findByCourseIds, deleteByUserId };
