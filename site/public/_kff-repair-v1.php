<?php
declare(strict_types=1);

const SITE = 'kitchenfindsfavorites.com';
const ASSOCIATES_TAG = 'kitchenfi0fde-20';
const GA4 = 'G-G7WPSMPB7T';
const STATEMENT = 'As an Amazon Associate I earn from qualifying purchases.';
const DISCLOSURE = '#ad ' . STATEMENT;
const KEY_HASH = '3aa16cc2ee5ca1a689d0decdd0344e4e513a1565248071d0811fe5f326c0e726';
const MAX_HTML_BYTES = 900000;
const SLUG = '[a-z0-9][a-z0-9-]{0,94}';

function finish(int $code, array $body): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: private, no-store');
    header('X-Robots-Tag: noindex, nofollow');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($body, JSON_UNESCAPED_SLASHES);
    exit;
}

function target(string $input): ?array {
    if (!preg_match('~^https://([a-z0-9.-]+)(/[^?#]*)$~D', $input, $parts)) return null;
    [, $host, $path] = $parts;
    if ($host === SITE && preg_match('~^/(picks|microsites)/(' . SLUG . ')/$~D', $path, $names)) {
        return [substr($path, 1) . 'index.html', $names[1] === 'microsites' ? $names[2] : null];
    }
    if ($path === '/' && preg_match('~^(' . SLUG . ')\.' . preg_quote(SITE, '~') . '$~D', $host, $names)) {
        return [$names[1] . '/index.html', $names[1]];
    }
    return null;
}

function text_only(string $fragment): string {
    return trim((string)preg_replace('/\s+/u', ' ', html_entity_decode(strip_tags($fragment), ENT_QUOTES | ENT_HTML5, 'UTF-8')));
}

function html(string $text): string {
    return htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE | ENT_HTML5, 'UTF-8');
}

function link_parts(string $href): ?array {
    $data = parse_url($href);
    if (!is_array($data) || ($data['scheme'] ?? '') !== 'https' || empty($data['host'])
        || isset($data['user']) || isset($data['pass']) || isset($data['port'])) return null;
    return $data;
}

function fix_anchor(string $element, ?string $guide, array &$found, array &$changed): string {
    return preg_replace_callback('~(\shref\s*=\s*)(["\x27])(.*?)\2~is', function (array $attr) use ($guide, &$found, &$changed): string {
        $href = html_entity_decode($attr[3], ENT_QUOTES | ENT_HTML5, 'UTF-8');
        if ($guide !== null && substr($href, 0, 7) === '/picks/') $href = 'https://' . SITE . $href;
        $data = link_parts($href);
        if ($data === null) return $attr[0];
        $host = strtolower($data['host']);
        $path = $data['path'] ?? '/';
        $pairs = isset($data['query']) && $data['query'] !== '' ? explode('&', $data['query']) : [];
        $key = static function (string $pair): string { return urldecode(explode('=', $pair, 2)[0]); };
        $value = static function (string $pair): string { return urldecode(explode('=', $pair, 2)[1] ?? ''); };

        if (in_array($host, [SITE, 'www.' . SITE], true) && $guide !== null
            && preg_match('~^/picks/' . SLUG . '/?$~D', $path)) {
            $found['referral'] = true;
            $default = ['utm_source'=>'microsite', 'utm_medium'=>'referral', 'utm_campaign'=>'kff_microsite_pages', 'utm_content'=>$guide];
            foreach ($pairs as $pair) {
                if ($value($pair) !== '') unset($default[$key($pair)]);
            }
            if ($default === []) return $attr[0];
            $pairs = array_values(array_filter($pairs, static function (string $pair) use ($key, $default): bool {
                return !array_key_exists($key($pair), $default);
            }));
            foreach ($default as $field => $val) $pairs[] = rawurlencode($field) . '=' . rawurlencode($val);
            $changed['referrals'] = true;
        } elseif (in_array($host, ['amazon.com', 'www.amazon.com'], true)
            && (preg_match('~/(?:dp|gp/product)/[a-z0-9]{10}(?:/|$)~i', $path) || rtrim($path, '/') === '/deals')) {
            $found['amazon'] = true;
            $tags = array_values(array_filter($pairs, static function (string $pair) use ($key): bool { return $key($pair) === 'tag'; }));
            if (count($tags) === 1 && $value($tags[0]) === ASSOCIATES_TAG) return $attr[0];
            $pairs = array_values(array_filter($pairs, static function (string $pair) use ($key): bool { return $key($pair) !== 'tag'; }));
            $pairs[] = 'tag=' . ASSOCIATES_TAG;
            $changed['amazon_tags'] = true;
        } else {
            return $attr[0];
        }
        $next = 'https://' . $host . $path . '?' . implode('&', $pairs);
        if (isset($data['fragment'])) $next .= '#' . $data['fragment'];
        return $attr[1] . $attr[2] . html($next) . $attr[2];
    }, $element, 1) ?? $element;
}

function repair(string $source, string $url, ?string $guide): array {
    $opaque = '~<!--[\s\S]*?-->|<(script|style|template|noscript)\b[^>]*>[\s\S]*?</\1\s*>~i';
    $markup = preg_replace($opaque, ' ', $source);
    if (!is_string($markup) || !preg_match('~<html\b~i', $markup) || !preg_match('~<main\b~i', $markup)
        || !preg_match('~<h1\b[^>]*>(.*?)</h1>~is', $markup, $heading) || preg_match('~<\?~', $source)) return [$source, [], 'Unrecognized HTML layout.'];
    if (preg_match('~<meta\b[^>]*\bcontent\s*=\s*["\x27][^"\x27]*\bnoindex\b~i', $markup)) return [$source, [], 'The page is excluded from indexing.'];

    $found = ['amazon'=>false, 'referral'=>false];
    $changes = [];
    $chunks = preg_split('~(<!--[\s\S]*?-->|<(?:script|style|template|noscript)\b[^>]*>[\s\S]*?</(?:script|style|template|noscript)\s*>|<[^>]+>)~i', $source, -1, PREG_SPLIT_DELIM_CAPTURE);
    if ($chunks === false) return [$source, [], 'Could not read this HTML layout.'];
    foreach ($chunks as $i => $part) {
        if ($i % 2 === 0) {
            $count = 0;
            $chunks[$i] = preg_replace('~(?<!#ad )' . preg_quote(STATEMENT, '~') . '~', DISCLOSURE, $part, -1, $count) ?? $part;
            if ($count) $changes['disclosure'] = true;
        } elseif (preg_match('~^<a\s~i', $part)) {
            $chunks[$i] = fix_anchor($part, $guide, $found, $changes);
        } elseif (preg_match('~^<(span|p)\b[^>]*\bclass\s*=\s*["\x27](?:product-price|affiliate-price)["\x27][^>]*>$~i', $part, $price)
            && preg_match('~^\s*(?:US\s*)?\$\s*\d[\d,]*(?:\.\d{2})?\s*$~iD', $chunks[$i+1] ?? '')
            && strtolower($chunks[$i+2] ?? '') === '</' . strtolower($price[1]) . '>') {
            $chunks[$i+1] = 'Check price on Amazon';
            $changes['listed_price'] = true;
        }
    }
    $existingStatement = strpos(text_only($markup), STATEMENT) !== false;
    if (!$found['amazon'] && !$found['referral'] && !$existingStatement) return [$source, [], 'No supported affiliate route or existing disclosure.'];
    $next = implode('', $chunks);
    $visible = text_only((string)preg_replace($opaque, ' ', $next));
    if (strpos($visible, DISCLOSURE) === false && ($found['amazon'] || $found['referral'])) {
        $next = preg_replace('~(<main\b[^>]*>)~i', '$1<p class="disclosure">' . DISCLOSURE . '</p>', $next, 1);
        $changes['disclosure'] = true;
    }



    $head = '';
    if (($found['amazon'] || $found['referral']) && !preg_match('~googletagmanager\.com/(?:gtag|gtm)|\b(?:G|GTM)-[A-Z0-9]{6,}~i', $source)) {
        $head .= '<script async src="https://www.googletagmanager.com/gtag/js?id=' . GA4 . '"></script>'
            . '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag("js",new Date());gtag("config","' . GA4 . '");</script>';
        $changes['page_views'] = true;
    }
    $hasKnownStream = isset($changes['page_views']) || strpos($source, GA4) !== false;
    if ($found['amazon'] && $hasKnownStream && !preg_match('~amazon_link_click|amazon_click|affiliate_click~i', $source)) {
        $head .= <<<'JS'
<script>document.addEventListener('click',function(event){
const a=event.target?.closest?.('a[href]');
if(!a||typeof window.gtag!=='function')return;
const link=new URL(a.href);
if(!['amazon.com','www.amazon.com'].includes(link.hostname)||!link.searchParams.get('tag'))return;
window.gtag('event','amazon_click',{link_page:location.pathname,transport_type:'beacon'});
});</script>
JS;
        $changes['click_event'] = true;
    }

    $title = text_only($heading[1]);
    if ($guide === null && $title !== '' && strlen($title) <= 155) {
        if (!preg_match('~<title\b~i', $markup)) {
            $head .= '<title>' . html($title) . ' | Kitchen Finds &amp; Favorites</title>';
            $changes['title'] = true;
        }
        if (!preg_match('~<link\b[^>]*\brel\s*=\s*["\x27]canonical["\x27]~i', $markup)) {
            $head .= '<link rel="canonical" href="' . html($url) . '">';
            $changes['canonical'] = true;
        }
    }
    if ($head !== '') {
        $count = 0;
        $next = preg_replace_callback('~</head\s*>~i', static function (array $close) use ($head): string { return $head . $close[0]; }, $next, 1, $count) ?? $next;
        if (!$count) return [$source, [], 'The HTML has no usable closing head.'];
    }
    return [$next, array_keys($changes), null];
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') finish(405, ['error'=>'POST required.']);
$key = $_SERVER['HTTP_X_KFF_REPAIR_KEY'] ?? '';
if (!preg_match('/^[0-9a-f]{64}$/D', $key) || !hash_equals(KEY_HASH, hash('sha256', $key))) {
    finish(401, ['error'=>'Repair authorization required.']);
}
$input = file_get_contents('php://input', false, null, 0, 4097);
if ($input === false || strlen($input) > 4096) finish(400, ['error'=>'Invalid request size.']);
$body = json_decode($input, true);
$url = is_array($body) && is_string($body['url'] ?? null) ? $body['url'] : '';
$destination = target($url);
if ($destination === null) finish(422, ['error'=>'This URL has no eligible repair target.']);
[$relative, $guide] = $destination;
$path = __DIR__ . '/' . $relative;
if (realpath($path) !== $path || !is_file($path) || !is_readable($path)) finish(404, ['error'=>'An eligible Hostinger HTML file was not found.']);

$lockName = sys_get_temp_dir() . '/kff-repair-' . hash('sha256', $path) . '.lock';
$lock = @fopen($lockName, 'c');
if ($lock === false || !flock($lock, LOCK_EX | LOCK_NB)) finish(409, ['error'=>'This file is currently being saved.']);
$source = @file_get_contents($path, false, null, 0, MAX_HTML_BYTES + 1);
if ($source === false || strlen($source) > MAX_HTML_BYTES || !preg_match('//u', $source)) finish(422, ['error'=>'The HTML could not be read safely.']);
if ($guide !== null && substr($relative, 0, 11) !== 'microsites/'
    && !preg_match('~<title[^>]*>[^<]*Buying Guide\s*</title>~i', $source)) finish(422, ['error'=>'This subdomain is not a supported KFF guide.']);
[$repaired, $changes, $reason] = repair($source, $url, $guide);
if ($source === $repaired) finish(200, ['changes'=>[], 'reason'=>$reason, 'revision'=>hash('sha256', $source)]);
if (($body['check'] ?? false) === true) finish(200, ['changes'=>$changes, 'dryRun'=>true]);
$temp = tempnam(dirname($path), '.kff-repair-');
if ($temp === false || dirname($temp) !== dirname($path)) {
    if ($temp !== false) @unlink($temp);
    finish(500, ['error'=>'Could not stage the repair.']);
}
$mode = fileperms($path);
$written = @file_put_contents($temp, $repaired);
if ($written !== strlen($repaired) || $mode === false || !@chmod($temp, $mode & 0777)
    || @hash_file('sha256', $path) !== hash('sha256', $source) || !@rename($temp, $path)) {
    @unlink($temp);
    finish(409, ['error'=>'The file changed or the repair could not be saved.']);
}
$revision = hash('sha256', $repaired);
if (@hash_file('sha256', $path) !== $revision) finish(500, ['error'=>'Hostinger could not verify the saved repair.']);
if (parse_url($url, PHP_URL_HOST) === SITE) {
    header('X-LiteSpeed-Purge: url=' . parse_url($url, PHP_URL_PATH));
}
finish(200, ['changes'=>$changes, 'revision'=>$revision]);
