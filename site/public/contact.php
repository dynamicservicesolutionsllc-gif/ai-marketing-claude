<?php
// Contact form handler (Hostinger, PHP 8). Copied into public/ by build.py.
// Emails the message to the site mailbox and keeps a backup copy in kff-data/contact-messages.csv.
declare(strict_types=1);
require __DIR__ . '/kff-lib.php';

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    kff_redirect('/contact/');
}
if (trim((string)($_POST['website'] ?? '')) !== '') {
    kff_redirect('/contact/sent/'); // honeypot: bot
}
// Strip line breaks from anything that goes into a mail header (header injection).
$name = substr(trim((string)preg_replace('/[\r\n\t]+/', ' ', (string)($_POST['name'] ?? ''))), 0, 100);
$email = strtolower(trim((string)($_POST['email'] ?? '')));
$message = trim(str_replace("\r\n", "\n", (string)($_POST['message'] ?? '')));

if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 254
    || strlen($message) < 10 || strlen($message) > 5000) {
    kff_redirect('/contact/?error=fields#form');
}

$fh = fopen(kff_data_dir() . '/contact-messages.csv', 'a');
if ($fh !== false) {
    flock($fh, LOCK_EX);
    fputcsv($fh, [date('c'), kff_csv_safe($name), kff_csv_safe($email), kff_csv_safe($message)], ',', '"', '');
    flock($fh, LOCK_UN);
    fclose($fh);
}

$subject = '=?UTF-8?B?' . base64_encode('Website message from ' . $name) . '?=';
$body = "Name: $name\nEmail: $email\n\n$message\n\n-- Sent from the contact form on " . KFF_SITE . "\n";
$headers = implode("\r\n", [
    'From: Kitchen Finds & Favorites <' . KFF_MAILBOX . '>',
    'Reply-To: ' . $email,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
]);
$sent = mail(KFF_MAILBOX, $subject, $body, $headers, '-f' . KFF_MAILBOX);
kff_redirect($sent ? '/contact/sent/' : '/contact/?error=send#form');
