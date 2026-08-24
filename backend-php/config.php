<?php
/**
 * config.php
 * Loads settings for the PHP REST layer from the repo-root .env file
 * (the same .env the Python side uses) and exposes them as constants.
 *
 * No absolute paths: the .env location is always resolved relative to
 * this file (one directory up), so this works on any machine that
 * clones the repo.
 */

declare(strict_types=1);

/**
 * Minimal .env parser (KEY=VALUE per line, '#' comments, optional quotes).
 * Does not overwrite a variable that is already set in the real
 * environment, so a production deployment can just set real env vars
 * instead of shipping a .env file.
 */
function backend_load_env(string $path): void
{
    if (!is_readable($path)) {
        return;
    }

    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if ($lines === false) {
        return;
    }

    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) {
            continue;
        }

        [$key, $value] = explode('=', $line, 2);
        $key = trim($key);
        $value = trim($value);

        $len = strlen($value);
        if ($len >= 2 && ($value[0] === '"' || $value[0] === "'") && $value[$len - 1] === $value[0]) {
            $value = substr($value, 1, -1);
        }

        if (getenv($key) === false) {
            putenv("$key=$value");
        }
    }
}

backend_load_env(dirname(__DIR__) . '/.env');

// Base URL of the FastAPI service (ai-service/main.py). No trailing slash.
define('FASTAPI_BASE_URL', rtrim(getenv('FASTAPI_BASE_URL') ?: 'http://127.0.0.1:8000', '/'));

// Origin allowed to call this API via CORS (the React/Vite dev server).
define('CORS_ALLOWED_ORIGIN', getenv('PHP_CORS_ALLOWED_ORIGIN') ?: 'http://localhost:5173');

// Seconds to wait for FastAPI before giving up and returning 502.
define('FASTAPI_TIMEOUT_SECONDS', (int) (getenv('FASTAPI_TIMEOUT_SECONDS') ?: 30));
