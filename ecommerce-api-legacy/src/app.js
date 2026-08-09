// Composition root: the only file that reads config, initializes the DB,
// wires the routes/middlewares together, and starts the server. It
// contains wiring, not business logic — that all lives in
// controllers/models/services now.
const express = require('express');
const config = require('./config');
const database = require('./config/database');
const CacheService = require('./services/cacheService');
const createRouter = require('./routes');
const errorHandler = require('./middlewares/errorHandler');
const logger = require('./utils/logger');

async function bootstrap() {
    const app = express();
    app.use(express.json());

    await database.initSchema();
    await database.seedData();

    const cacheService = new CacheService();
    app.use(createRouter({ cacheService }));

    // Registered last, after all routes, so any error passed to next(err)
    // (or thrown from an async handler) funnels into one shared handler.
    app.use(errorHandler);

    app.listen(config.port, () => {
        logger.info(`Frankenstein LMS rodando na porta ${config.port}...`);
    });

    return app;
}

const bootstrapPromise = bootstrap().catch((err) => {
    logger.error('Failed to start application', { message: err.message, stack: err.stack });
    process.exit(1);
});

module.exports = bootstrapPromise;
