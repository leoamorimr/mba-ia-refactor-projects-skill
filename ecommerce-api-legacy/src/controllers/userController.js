// Orchestration for user management. `deleteUser` fixes the
// referential-integrity finding: dependent payments and enrollments are
// removed in the same transaction as the user, instead of leaving orphaned
// rows behind (the original response literally admitted to this: "mas as
// matrículas e pagamentos ficaram sujos no banco").
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const database = require('../config/database');
const { NotFoundError } = require('../utils/errors');

async function deleteUser(id) {
    const user = await userModel.findById(id);
    if (!user) {
        throw new NotFoundError('Usuário não encontrado');
    }

    await database.transaction(async () => {
        await paymentModel.deleteByEnrollmentUserId(id);
        await enrollmentModel.deleteByUserId(id);
        await userModel.deleteById(id);
    });

    return { message: 'Usuário deletado com sucesso, incluindo matrículas e pagamentos associados.' };
}

module.exports = { deleteUser };
