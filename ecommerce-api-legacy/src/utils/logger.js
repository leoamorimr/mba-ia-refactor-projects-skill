// Minimal structured logger replacing scattered console.log calls.
// Emits one JSON object per line so log lines are queryable/aggregable by
// any log shipper, instead of ad-hoc human-readable strings.
// IMPORTANT: never pass raw sensitive values (card numbers, secrets,
// passwords) in `meta` — callers must mask/redact before logging.

function write(level, message, meta = {}) {
    const entry = {
        level,
        message,
        timestamp: new Date().toISOString(),
        ...meta,
    };
    const line = JSON.stringify(entry);
    if (level === 'error') {
        console.error(line);
    } else {
        console.log(line);
    }
}

module.exports = {
    info: (message, meta) => write('info', message, meta),
    warn: (message, meta) => write('warn', message, meta),
    error: (message, meta) => write('error', message, meta),
};
