<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function out(int $status, array $body): never { http_response_code($status); echo json_encode($body, JSON_UNESCAPED_SLASHES) . PHP_EOL; exit; }
function val(string $name): string { $v = getenv($name); return is_string($v) ? trim($v) : ''; }
function syncToken(): string {
    $v = val('SYNC_ENDPOINT_TOKEN');
    if ($v !== '') return $v;
    $home = val('HOME');
    $file = $home !== '' ? $home . '/private/sync-endpoint-token.txt' : '';
    return $file !== '' && is_file($file) ? trim((string) file_get_contents($file)) : '';
}
function bearer(): string {
    $h = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    return preg_match('/^Bearer\\s+(.+)$/i', $h, $m) ? trim($m[1]) : '';
}
function required(array $names): void { foreach ($names as $n) if (val($n) === '') out(503, ['ok'=>false,'error'=>'Amazon configuration incomplete']); }
function amazonToken(): string {
    $ch = curl_init('https://creatorsapi.amazon.com/auth/O2/token');
    curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_POSTFIELDS=>http_build_query([
        'grant_type'=>'client_credentials','client_id'=>val('AMAZON_CLIENT_ID'),
        'client_secret'=>val('AMAZON_CLIENT_SECRET'),'version'=>val('AMAZON_CREDENTIAL_VERSION')
    ]), CURLOPT_RETURNTRANSFER=>true, CURLOPT_TIMEOUT=>20,
    CURLOPT_HTTPHEADER=>['Content-Type: application/x-www-form-urlencoded']]);
    $body = curl_exec($ch); $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); $err = curl_error($ch); curl_close($ch);
    $json = json_decode((string)$body, true);
    if ($body === false || $code < 200 || $code >= 300 || !is_array($json) || empty($json['access_token'])) throw new RuntimeException('Amazon token request failed: '.$code.' '.$err);
    return (string)$json['access_token'];
}
function searchAmazon(string $token, array $search): array {
    $payload = ['keywords'=>trim((string)$search['keywords']), 'searchIndex'=>trim((string)($search['searchIndex'] ?? 'All')) ?: 'All', 'itemCount'=>min(max((int)($search['itemCount'] ?? 10),1),10), 'partnerTag'=>val('AMAZON_PARTNER_TAG'), 'marketplace'=>val('AMAZON_MARKETPLACE'), 'resources'=>['Images.Primary.Large','ItemInfo.Title','Offers.Listings.Price','Offers.Listings.Availability.Message']];
    $ch = curl_init('https://creatorsapi.amazon.com/catalog/v1/searchItems');
    curl_setopt_array($ch, [CURLOPT_POST=>true, CURLOPT_POSTFIELDS=>json_encode($payload), CURLOPT_RETURNTRANSFER=>true, CURLOPT_TIMEOUT=>30, CURLOPT_HTTPHEADER=>['Authorization: Bearer '.$token,'Content-Type: application/json','Accept: application/json','x-marketplace: '.val('AMAZON_MARKETPLACE')]]);
    $body = curl_exec($ch); $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); $err = curl_error($ch); curl_close($ch);
    $json = json_decode((string)$body, true);
    if ($body === false || $code < 200 || $code >= 300 || !is_array($json)) throw new RuntimeException('Amazon catalog request failed: '.$code.' '.$err);
    return $json['searchResult']['items'] ?? [];
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') out(405, ['ok'=>false,'error'=>'POST required']);
$expected = syncToken();
if ($expected === '' || bearer() === '' || !hash_equals($expected, bearer())) out(401, ['ok'=>false,'error'=>'Unauthorized']);
required(['AMAZON_CLIENT_ID','AMAZON_CLIENT_SECRET','AMAZON_CREDENTIAL_VERSION','AMAZON_PARTNER_TAG','AMAZON_MARKETPLACE']);
$searches = json_decode(val('AMAZON_SEARCHES'), true);
if (!is_array($searches) || !$searches) out(503, ['ok'=>false,'error'=>'AMAZON_SEARCHES is not configured']);

$path = __DIR__.'/data/products.json'; $dir = dirname($path); if (!is_dir($dir) && !mkdir($dir,0750,true)) out(500,['ok'=>false,'error'=>'Catalog directory unavailable']);
$lock = fopen($path.'.lock','c'); if (!$lock || !flock($lock, LOCK_EX|LOCK_NB)) out(503,['ok'=>false,'error'=>'Sync already running']);
try {
    $old = is_file($path) ? json_decode((string)file_get_contents($path), true) : []; $byAsin=[];
    foreach (is_array($old)?$old:[] as $p) if (is_array($p) && !empty($p['asin'])) $byAsin[(string)$p['asin']]=$p;
    $seen=[]; $fetched=0; $updated=0; $errors=[]; $token=amazonToken();
    foreach ($searches as $s) {
        if (!is_array($s) || trim((string)($s['keywords']??''))==='') continue;
        try { $items=searchAmazon($token,$s); } catch (Throwable $e) { $errors[]='One Amazon search failed'; continue; }
        foreach ($items as $i) {
            if (!is_array($i)) continue; $asin=trim((string)($i['asin']??'')); if ($asin==='' || isset($seen[$asin])) continue; $seen[$asin]=1; $fetched++;
            $p=['asin'=>$asin,'title'=>trim((string)($i['itemInfo']['title']['displayValue']??'')),'category'=>(string)($s['searchIndex']??'All'),'affiliate_url'=>(string)($i['detailPageURL']??''),'image_url'=>(string)($i['images']['primary']['large']['url']??''),'price'=>(string)($i['offers']['listings'][0]['price']['displayAmount']??''),'availability'=>(string)($i['offers']['listings'][0]['availability']['message']??''),'updated_at'=>gmdate('c')];
            if ($p['title']==='') continue; if (!isset($byAsin[$asin]) || json_encode($byAsin[$asin])!==json_encode($p)) {$byAsin[$asin]=$p; $updated++;}
        }
    }
    $tmp=tempnam($dir,'products-'); if ($tmp===false || file_put_contents($tmp,json_encode(array_values($byAsin),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES).PHP_EOL,LOCK_EX)===false) throw new RuntimeException('Catalog write failed'); chmod($tmp,0640); if (!rename($tmp,$path)) throw new RuntimeException('Catalog replace failed');
    out(200,['ok'=>true,'fetched'=>$fetched,'updated'=>$updated,'total'=>count($byAsin),'errors'=>$errors,'completed_at'=>gmdate('c')]);
} catch (Throwable $e) { error_log('Amazon sync failed: '.$e->getMessage()); out(500,['ok'=>false,'error'=>'Catalog sync failed']); } finally { flock($lock,LOCK_UN); fclose($lock); }
