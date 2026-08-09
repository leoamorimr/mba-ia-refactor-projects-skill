// Reporting aggregation extracted out of the route handler. Fixes the N+1
// query pattern (one query for courses, one batched query for enrollments,
// two batched queries for users/payments — 4 total regardless of data
// volume, instead of 1 + N + 2N) and adds pagination on the outer course
// list instead of always loading every course unbounded.
const courseModel = require('../models/courseModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const userModel = require('../models/userModel');

async function getReport({ page, limit }) {
    const offset = (page - 1) * limit;
    const courses = await courseModel.listPage({ limit, offset });
    if (courses.length === 0) {
        return [];
    }

    const courseIds = courses.map((course) => course.id);
    const enrollments = await enrollmentModel.findByCourseIds(courseIds);

    const enrollmentIds = enrollments.map((enrollment) => enrollment.id);
    const userIds = [...new Set(enrollments.map((enrollment) => enrollment.user_id))];

    const [payments, users] = await Promise.all([
        paymentModel.findByEnrollmentIds(enrollmentIds),
        userModel.findByIds(userIds),
    ]);

    const usersById = new Map(users.map((user) => [user.id, user]));
    const paymentByEnrollmentId = new Map(payments.map((payment) => [payment.enrollment_id, payment]));
    const enrollmentsByCourseId = new Map();
    for (const enrollment of enrollments) {
        const bucket = enrollmentsByCourseId.get(enrollment.course_id) || [];
        bucket.push(enrollment);
        enrollmentsByCourseId.set(enrollment.course_id, bucket);
    }

    return courses.map((course) => {
        const courseEnrollments = enrollmentsByCourseId.get(course.id) || [];
        let revenue = 0;

        const students = courseEnrollments.map((enrollment) => {
            const payment = paymentByEnrollmentId.get(enrollment.id);
            const user = usersById.get(enrollment.user_id);

            if (payment && payment.status === 'PAID') {
                revenue += payment.amount;
            }

            return {
                student: user ? user.name : 'Unknown',
                paid: payment ? payment.amount : 0,
            };
        });

        return { course: course.title, revenue, students };
    });
}

module.exports = { getReport };
