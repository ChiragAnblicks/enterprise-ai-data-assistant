<?php
/**
 * fastapi_client.php
 * One function: forward a request to the FastAPI service (ai-service/main.py)
 * over HTTP and hand back its status code + raw JSON body untouched.
 *
 * This file has no MySQL code and never will -- FastAPI's db.py is the
 * only thing that talks to MySQL (as capstone_ro, SELECT-only). PHP is
 * a pure proxy: React -> PHP REST -> FastAPI -> MySQL + Chroma.
 */

declare(strict_types=1);

/**
 * @return array{0:int,1:string} [http status code, raw response body]
 */
function fastapi_request(string $method, string $path, ?string $jsonBody = null): array
{
    $url = FASTAPI_BASE_URL . $path;

    $ch = curl_init($url);
    if ($ch === false) {
        return [502, json_encode(['detail' => 'Could not initialize request to AI service.'])];
    }

    $headers = ['Accept: application/json'];
    if ($jsonBody !== null) {
        $headers[] = 'Content-Type: application/json';
    }

    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_TIMEOUT => FASTAPI_TIMEOUT_SECONDS,
        CURLOPT_CONNECTTIMEOUT => 5,
    ]);

    if ($jsonBody !== null) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonBody);
    }

    $responseBody = curl_exec($ch);

    if ($responseBody === false) {
        $error = curl_error($ch);
        curl_close($ch);
        return [
            502,
            json_encode([
                'detail' => "Could not reach the AI service at $url: $error. "
                    . "Is it running? (uvicorn main:app --reload --port 8000 in ai-service\\)",
            ]),
        ];
    }

    $statusCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    // FastAPI always returns JSON (success or {"detail": "..."} on error) --
    // pass it through as-is so PHP's error shape matches FastAPI's exactly.
    return [$statusCode, $responseBody];
}
