<?php
// Email sign-up handler (Hostinger, PHP 8). Copied into public/ by build.py.
// Stores addresses in kff-data/subscribers.csv OUTSIDE public_html, so deploys never touch it
// and it can't be downloaded from the web. Download it from hPanel > File Manager.
declare(strict_types=1);
require __DIR__ . '/kff-lib.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    kff_redirect('/newsletter/');
}
if (trim((string)($_POST['website'] ?? '')) !== '') {
    kff_redirect('/thanks/'); // honeypot filled in: a bot. Pretend it worked.
}
$email = strtolower(trim((string)($_POST['email'] ?? '')));
if (strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    kff_redirect('/newsletter/?error=email#updates');
}
$source = substr((string)preg_replace('~[^a-z0-9/_-]~i', '', (string)($_POST['source'] ?? '')), 0, 120);

$file = kff_data_dir() . '/subscribers.csv';
$fh = fopen($file, 'c+');
if ($fh === false || !flock($fh, LOCK_EX)) {
    kff_redirect('/newsletter/?error=server#updates');
}
$known = false;
while (($row = fgetcsv($fh, null, ',', '"', '')) !== false) {
    if (isset($row[1]) && $row[1] === kff_csv_safe($email)) {
        $known = true;
        break;
    }
}
if (!$known) {
    if (ftell($fh) === 0) {
        fputcsv($fh, ['subscribed_at', 'email', 'signup_page'], ',', '"', '');
    }
    fseek($fh, 0, SEEK_END);
    fputcsv($fh, [date('c'), kff_csv_safe($email), $source], ',', '"', '');
}
fflush($fh);
flock($fh, LOCK_UN);
fclose($fh);
kff_redirect('/thanks/');
