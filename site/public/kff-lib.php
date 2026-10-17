<?php
// Shared helpers for the form handlers. Direct web requests to this file are refused by .htaccess.
declare(strict_types=1);

const KFF_SITE = 'https://kitchenfindsfavorites.com';
const KFF_MAILBOX = 'help@kitchenfindsfavorites.com';

function kff_redirect(string $path): never
{
    header('Location: ' . $path, true, 303);
    exit;
}

/** Private storage folder: next to public_html (not web-reachable), else a locked folder inside it. */
function kff_data_dir(): string
{
    $root = $_SERVER['DOCUMENT_ROOT'] ?? '';
    $outside = dirname($root !== '' ? $root : __DIR__) . '/kff-data';
    if ((is_dir($outside) || @mkdir($outside, 0750, true)) && is_writable($outside)) {
        return $outside;
    }
    $inside = __DIR__ . '/_private';
    if (!is_dir($inside)) {
        @mkdir($inside, 0750, true);
    }
    if (!is_file("$inside/.htaccess")) {
        @file_put_contents("$inside/.htaccess", "Require all denied\n");
    }
    return $inside;
}

/** Stop spreadsheet apps from treating a value as a formula when the CSV is opened. */
function kff_csv_safe(string $value): string
{
    return preg_match('/^[=+\-@\t\r]/', $value) ? "'" . $value : $value;
}
