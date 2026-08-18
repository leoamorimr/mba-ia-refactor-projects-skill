// Schema validation at the route boundary — types, formats, and
// required-ness are checked here before any DB call runs, instead of the
// original bare presence checks (`if (!u || !e || !cid || !cc)`).
const { z } = require('zod');
const { ValidationError } = require('../utils/errors');

const DEFAULT_REPORT_PAGE = 1;
const DEFAULT_REPORT_LIMIT = 50;
const MAX_REPORT_LIMIT = 100;

function formatZodError(error) {
    return error.issues.map((issue) => issue.message).join('; ');
}

// Wire format (`usr`, `eml`, `pwd`, `c_id`, `card`) is preserved for API
// compatibility; validated values are mapped to descriptive names for
// everything downstream (fixes the single-letter-variable naming finding
// without touching the public request shape).
const checkoutSchema = z.object({
    usr: z.string().trim().min(1, 'usr é obrigatório'),
    eml: z.string().trim().email('eml deve ser um email válido'),
    pwd: z.string().min(1, 'pwd é obrigatório'),
    c_id: z.coerce.number().int('c_id deve ser um inteiro').positive('c_id deve ser positivo'),
    card: z.string().regex(/^\d{13,19}$/, 'card deve conter entre 13 e 19 dígitos numéricos'),
});

function validateCheckout(req, res, next) {
    const result = checkoutSchema.safeParse(req.body);
    if (!result.success) {
        return next(new ValidationError(formatZodError(result.error)));
    }
    req.validated = {
        username: result.data.usr,
        email: result.data.eml,
        password: result.data.pwd,
        courseId: result.data.c_id,
        cardNumber: result.data.card,
    };
    return next();
}

const userIdParamSchema = z.object({
    id: z.coerce.number().int('id deve ser um inteiro').positive('id deve ser positivo'),
});

function validateUserIdParam(req, res, next) {
    const result = userIdParamSchema.safeParse(req.params);
    if (!result.success) {
        return next(new ValidationError(formatZodError(result.error)));
    }
    req.validated = { id: result.data.id };
    return next();
}

const reportQuerySchema = z.object({
    page: z.coerce.number().int().positive().optional().default(DEFAULT_REPORT_PAGE),
    limit: z.coerce
        .number()
        .int()
        .positive()
        .max(MAX_REPORT_LIMIT)
        .optional()
        .default(DEFAULT_REPORT_LIMIT),
});

function validateReportQuery(req, res, next) {
    const result = reportQuerySchema.safeParse(req.query);
    if (!result.success) {
        return next(new ValidationError(formatZodError(result.error)));
    }
    req.validated = result.data;
    return next();
}

module.exports = { validateCheckout, validateUserIdParam, validateReportQuery };
