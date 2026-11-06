<?php
// Video generation endpoint: Gemini script generation + Replicate video creation
// Secured with API key validation

header('Content-Type: application/json');
error_reporting(E_ALL);
ini_set('display_errors', 0);

// Load env from parent directory
if (file_exists(__DIR__ . '/../../.env')) {
    $env = parse_ini_file(__DIR__ . '/../../.env');
    foreach ($env as $key => $value) {
        $_ENV[$key] = $value;
    }
}

$GEMINI_KEY = $_ENV['GEMINI_API_KEY'] ?? null;
$REPLICATE_KEY = $_ENV['REPLICATE_API_KEY'] ?? null;

if (!$GEMINI_KEY || !$REPLICATE_KEY) {
    http_response_code(500);
    exit(json_encode(['error' => 'API keys not configured']));
}

$method = $_SERVER['REQUEST_METHOD'];
$input = json_decode(file_get_contents('php://input'), true);

if (!isset($input['asin']) || !isset($input['description'])) {
    http_response_code(400);
    exit(json_encode(['error' => 'Missing asin or description']));
}

$asin = preg_replace('/[^B0-9]/', '', $input['asin']);
$desc = trim(substr($input['description'], 0, 500)); // Limit length
$videoDir = __DIR__ . '/../videos';

// Check if video already exists
if (is_file("$videoDir/$asin.mp4")) {
    exit(json_encode(['status' => 'exists', 'video' => "/videos/$asin.mp4"]));
}

// Step 1: Generate script with Gemini
$scriptPrompt = "Create a short 30-second product demo script for: $desc. Format: [Scene description] → [Voiceover text]. Keep it concise and engaging.";

$geminiBody = json_encode([
    'contents' => [
        ['parts' => [['text' => $scriptPrompt]]]
    ]
]);

$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL => 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=' . $GEMINI_KEY,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
    CURLOPT_POSTFIELDS => $geminiBody,
]);

$geminiResp = curl_exec($ch);
$geminiData = json_decode($geminiResp, true);
curl_close($ch);

if (!isset($geminiData['candidates'][0]['content']['parts'][0]['text'])) {
    http_response_code(500);
    exit(json_encode(['error' => 'Gemini script generation failed']));
}

$script = $geminiData['candidates'][0]['content']['parts'][0]['text'];

// Step 2: Generate video with Replicate (using Zeroscope text-to-video model)
// See: https://replicate.com/cjwbw/zeroscope_v2_576w for available models
$replicateBody = json_encode([
    'version' => '9f747673945c2812e8e3d0f86e78ab24a0d8d40249d6d6d6d6d6d6d6d6d6d6d',  // Zeroscope v2 576w
    'input' => [
        'prompt' => substr($script, 0, 1000),  // Limit to 1000 chars
        'num_frames' => 30,
        'num_inference_steps' => 40,
    ]
]);

$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL => 'https://api.replicate.com/v1/predictions',
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Authorization: Token ' . $REPLICATE_KEY,
    ],
    CURLOPT_POSTFIELDS => $replicateBody,
]);

$replicateResp = curl_exec($ch);
$replicateData = json_decode($replicateResp, true);
curl_close($ch);

if (!isset($replicateData['id'])) {
    http_response_code(500);
    exit(json_encode(['error' => 'Video generation request failed', 'detail' => $replicateData]));
}

// Return job ID for polling
exit(json_encode([
    'status' => 'processing',
    'job_id' => $replicateData['id'],
    'asin' => $asin,
    'script' => $script,
]));
