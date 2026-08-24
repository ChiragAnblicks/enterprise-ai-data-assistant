<?php
/**
 * index.php
 * Front controller + router for the PHP REST layer.
 *
 * React -> PHP REST (this file) -> FastAPI (ai-service/main.py) -> MySQL + Chroma
 *
 * PHP does no NL->SQL, no SQL execution, no document retrieval, and no
 * MySQL connection of its own -- it forwards each request to FastAPI
 * and returns FastAPI's response as-is. FastAPI (db.py) is the only
 * security boundary for SQL.
 *
 * Run (from backend-php\):
 *     php -S localhost:8080 index.php
 *
 * Routes:
 *     GET  /health     -- PHP liveness + FastAPI reachability
 *     POST /ask         -- proxies to FastAPI POST /ask      (NL -> SQL -> rows -> explanation)
 *     POST /ask-docs     -- proxies to FastAPI POST /ask-docs (policy document Q&A)
 */

declare(strict_types=1);

require __DIR__ . '/config.php';
require __DIR__ . '/cors.php';          // handles OPTIONS preflight and exits if so
require __DIR__ . '/fastapi_client.php';

header('Content-Type: application/json');

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?? '/';
$path = rtrim($path, '/');
if ($path === '') {
    $path = '/';
}

// --- GET /health -----------------------------------------------------------
if ($method === 'GET' && $path === '/health') {
    [$upstreamStatus, $upstreamBody] = fastapi_request('GET', '/health');
    $upstreamOk = $upstreamStatus === 200;

    http_response_code($upstreamOk ? 200 : 502);
    echo json_encode([
        'php' => 'ok',
        'fastapi_reachable' => $upstreamOk,
        'fastapi_base_url' => FASTAPI_BASE_URL,
        'fastapi_response' => json_decode($upstreamBody, true) ?? $upstreamBody,
    ]);
    exit;
}

// --- POST /ask ---------------------------------------------------------
if ($method === 'POST' && $path === '/ask') {
    $body = file_get_contents('php://input');
    [$status, $responseBody] = fastapi_request('POST', '/ask', $body === false ? '' : $body);
    http_response_code($status);
    echo $responseBody;
    exit;
}

// --- POST /ask-docs ------------------------------------------------------
if ($method === 'POST' && $path === '/ask-docs') {
    $body = file_get_contents('php://input');
    [$status, $responseBody] = fastapi_request('POST', '/ask-docs', $body === false ? '' : $body);
    http_response_code($status);
    echo $responseBody;
    exit;
}

// --- Nothing matched -------------------------------------------------------
http_response_code(404);
echo json_encode(['detail' => "No route for $method $path"]);
