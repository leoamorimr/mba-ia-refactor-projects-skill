// Single composition point for the raw DB connection, schema, and seed data.
// This is the ONLY place that instantiates the sqlite3 driver — models
// depend on the promisified `run`/`get`/`all` helpers exported here instead
// of each creating (or being welded to) their own connection, which is what
// fixes the "AppManager instantiates its own DB dependency inline with its
// business logic" tight-coupling finding.
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcryptjs');
const config = require('./index');
const logger = require('../utils/logger');

const SEED_ADMIN_USER_PASSWORD = '123';

let db;

function getDb() {
    if (!db) {
        db = new sqlite3.Database(':memory:');
    }
    return db;
}

function run(sql, params = []) {
    return new Promise((resolve, reject) => {
        getDb().run(sql, params, function callback(err) {
            if (err) return reject(err);
            resolve({ lastID: this.lastID, changes: this.changes });
        });
    });
}

function get(sql, params = []) {
    return new Promise((resolve, reject) => {
        getDb().get(sql, params, (err, row) => {
            if (err) return reject(err);
            resolve(row);
        });
    });
}

function all(sql, params = []) {
    return new Promise((resolve, reject) => {
        getDb().all(sql, params, (err, rows) => {
            if (err) return reject(err);
            resolve(rows);
        });
    });
}

// Minimal transaction helper so multi-statement writes (checkout's
// enrollment+payment+audit-log insert, and delete's cascade across
// payments/enrollments/users) either all succeed or all roll back.
async function transaction(work) {
    await run('BEGIN TRANSACTION');
    try {
        const result = await work();
        await run('COMMIT');
        return result;
    } catch (err) {
        await run('ROLLBACK');
        throw err;
    }
}

async function initSchema() {
    await run('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, pass TEXT)');
    await run('CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)');
    await run('CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)');
    await run('CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)');
    await run('CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)');
}

async function seedData() {
    // Seed password is hashed through the same real hashing mechanism used
    // for newly-created users, so the seeded account behaves like any other
    // account with respect to the (now enforced) login check on checkout.
    const passwordHash = await bcrypt.hash(SEED_ADMIN_USER_PASSWORD, config.bcryptSaltRounds);
    await run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
        'Leonan',
        'leonan@fullcycle.com.br',
        passwordHash,
    ]);
    await run(
        'INSERT INTO courses (title, price, active) VALUES (?, ?, ?), (?, ?, ?)',
        ['Clean Architecture', 997.0, 1, 'Docker', 497.0, 1]
    );
    await run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
    await run("INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, 'PAID')");
    logger.info('Database seeded with initial data');
}

module.exports = { run, get, all, transaction, initSchema, seedData };
