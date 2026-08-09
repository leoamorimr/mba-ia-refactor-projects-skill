// Replaces the module-level mutable `globalCache` export with an explicit,
// injectable cache instance. Any consumer that needs caching gets one
// passed into it via the composition root instead of reaching into shared
// module state from anywhere in the codebase.
const logger = require('../utils/logger');

class CacheService {
    constructor() {
        this.store = new Map();
    }

    set(key, value) {
        logger.info('Cache set', { key });
        this.store.set(key, value);
    }

    get(key) {
        return this.store.get(key);
    }
}

module.exports = CacheService;
