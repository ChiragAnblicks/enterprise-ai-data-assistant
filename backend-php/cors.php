<?php
/**
 * cors.php
 * CORS headers so the React/Vite dev server (a different origin) can
 * call this API from the browser. Requires config.php to have run
 * first (uses CORS_ALLOWED_ORIGIN).
 */

declare(strict_types=1);

header('Access-Control-Allow-Origin: ' . CORS_ALLOWED_ORIGIN);
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Access-Control-Max-Age: 3600');

// Browsers send an OPTIONS preflight before the real POST; answer it
// here with no body so index.php's router never has to see it.
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
    http_response_code(204);
    exit;
}
