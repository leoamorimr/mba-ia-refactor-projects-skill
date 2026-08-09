// Orchestration for the checkout flow: applies the payment-approval rule,
// creates/authenticates the user, and coordinates the enrollment/payment/
// audit-log models. Extracted out of the route handler per the fat-controller
// finding — the route now only parses the request and shapes the response.
const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const database = require('../config/database');
const paymentService = require('../services/paymentService');
const passwordService = require('../services/passwordService');
const logger = require('../utils/logger');
const { NotFoundError, UnauthorizedError, PaymentDeniedError } = require('../utils/errors');

// The DB connection dependency is injected via the shared `database` module
// (composition root owns creating it) and the cache dependency is injected
// explicitly through this factory rather than pulled from a mutable global
// export, so this controller can be unit-tested with a fake cache.
function createCheckoutController({ cacheService }) {
    // Fixes the broken-authentication finding: an existing user's submitted
    // password is now actually verified against the stored hash before any
    // enrollment/payment happens. A brand-new user's password is now
    // required (no more silent "123456" default) and hashed with a real
    // algorithm instead of the reversible `badCrypto` transform.
    async function resolveUserId({ username, email, password }) {
        const existingUser = await userModel.findByEmail(email);

        if (existingUser) {
            const passwordMatches = await passwordService.verifyPassword(password, existingUser.pass);
            if (!passwordMatches) {
                throw new UnauthorizedError('Credenciais inválidas');
            }
            return existingUser.id;
        }

        const passwordHash = await passwordService.hashPassword(password);
        return userModel.create({ name: username, email, passwordHash });
    }

    async function checkout({ username, email, password, courseId, cardNumber }) {
        const course = await courseModel.findActiveById(courseId);
        if (!course) {
            throw new NotFoundError('Curso não encontrado');
        }

        const userId = await resolveUserId({ username, email, password });

        // Never log the raw card number or the payment-gateway secret key —
        // only a masked representation, through the structured logger.
        logger.info('Processing checkout payment', { maskedCard: paymentService.maskCard(cardNumber) });

        if (!paymentService.isApprovedCard(cardNumber)) {
            throw new PaymentDeniedError('Pagamento recusado');
        }

        const { enrollmentId } = await database.transaction(async () => {
            const newEnrollmentId = await enrollmentModel.create({ userId, courseId });
            await paymentModel.create({
                enrollmentId: newEnrollmentId,
                amount: course.price,
                status: paymentModel.PAYMENT_STATUS.PAID,
            });
            await auditLogModel.record(`Checkout curso ${courseId} por ${userId}`);
            return { enrollmentId: newEnrollmentId };
        });

        if (cacheService) {
            cacheService.set(`last_checkout_${userId}`, course.title);
        }

        return { message: 'Sucesso', enrollmentId };
    }

    return { checkout };
}

module.exports = createCheckoutController;
