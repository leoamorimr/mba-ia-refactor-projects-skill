// Typed application errors so the centralized error-handling middleware can
// map them to the right HTTP status code instead of every controller/route
// repeating its own `res.status(x).send(...)` logic.

class AppError extends Error {
    constructor(message, statusCode) {
        super(message);
        this.name = this.constructor.name;
        this.statusCode = statusCode;
    }
}

class ValidationError extends AppError {
    constructor(message) {
        super(message, 400);
    }
}

class BadRequestError extends AppError {
    constructor(message) {
        super(message, 400);
    }
}

class UnauthorizedError extends AppError {
    constructor(message) {
        super(message, 401);
    }
}

class NotFoundError extends AppError {
    constructor(message) {
        super(message, 404);
    }
}

class PaymentDeniedError extends AppError {
    constructor(message) {
        super(message, 400);
    }
}

module.exports = {
    AppError,
    ValidationError,
    BadRequestError,
    UnauthorizedError,
    NotFoundError,
    PaymentDeniedError,
};
