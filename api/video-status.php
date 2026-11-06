<?php
// Check video generation status and download when ready
header('Content-Type: application/json');

if (file_exists(__DIR__ . '/../../.env')) {
    $env = parse_ini_file(__DIR__ . '/../../.env');
    foreach ($env as $key => $value) {
        $_ENV[$key] = $value;
    }
}

$REPLICATE_KEY = $_ENV['REPLICATE_API_KEY'] ?? null;
if (!$REPLICATE_KEY) {
    http_response_code(500);
    exit(json_encode(['error' => 'API key not configured']));
}

$input = json_decode(file_get_contents('php://input'), true);
if (!isset($input['job_id']) || !isset($input['asin'])) {
    http_response_code(400);
    exit(json_encode(['error' => 'Missing job_id or asin']));
}

$jobId = $input['job_id'];
$asin = preg_replace('/[^B0-9]/', '', $input['asin']);
$videoDir = __DIR__ . '/../videos';

// Check job status
$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL => "https://api.replicate.com/v1/predictions/$jobId",
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'Authorization: Token ' . $REPLICATE_KEY,
    ],
]);

$resp = curl_exec($ch);
$data = json_decode($resp, true);
curl_close($ch);

if ($data['status'] === 'succeeded' && isset($data['output'])) {
    // Download and save video
    if (!is_dir($videoDir)) {
        mkdir($videoDir, 0755, true);
    }

    $videoUrl = is_array($data['output']) ? $data['output'][0] : $data['output'];
    $videoFile = "$videoDir/$asin.mp4";

    // Download video
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => $videoUrl,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_BINARYTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
    ]);
    $videoContent = curl_exec($ch);
    curl_close($ch);

    if ($videoContent && strlen($videoContent) > 1000) {
        file_put_contents($videoFile, $videoContent);
        exit(json_encode([
            'status' => 'completed',
            'video' => "/videos/$asin.mp4",
        ]));
    }
}

if ($data['status'] === 'failed') {
    exit(json_encode([
        'status' => 'failed',
        'error' => $data['error'] ?? 'Video generation failed',
    ]));
}

exit(json_encode([
    'status' => $data['status'] ?? 'unknown',
    'job_id' => $jobId,
]));
