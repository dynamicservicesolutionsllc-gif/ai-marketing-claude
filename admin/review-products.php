<?php
/**
 * Admin: Review & approve staged products
 * Access: https://kitchenfindsfavorites.com/admin/review-products.php
 */

// Auth password - change to your own if desired
define('ADMIN_PASSWORD', 'N7_bwzBK3a1mv99fBTar5Gg2rpKvxJEQDlIvByjMwKs');
$authenticated = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password'])) {
    if ($_POST['password'] === ADMIN_PASSWORD) {
        $authenticated = true;
        setcookie('admin_auth', bin2hex(random_bytes(32)), time() + 3600);
    }
}

if (isset($_COOKIE['admin_auth']) && strlen($_COOKIE['admin_auth']) === 64) {
    $authenticated = true;
}

if (!$authenticated) {
    ?>
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login</title>
        <style>
            body { font-family: system-ui; max-width: 400px; margin: 50px auto; }
            input { padding: 8px; width: 100%; }
            button { padding: 8px 16px; background: #06a; color: white; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <h2>Admin Login</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="Enter admin password" required>
            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    <?php
    exit;
}

// Load products.json
$products_file = __DIR__ . '/../products.json';
$data = json_decode(file_get_contents($products_file), true);
$staging = $data['staging']['products'] ?? [];

// Handle approvals
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    $asin = $_POST['asin'] ?? null;

    if ($_POST['action'] === 'approve' && $asin) {
        // Find and move product from staging to main
        $product = null;
        foreach ($staging as $key => $p) {
            if ($p['asin'] === $asin) {
                $product = $p;
                unset($staging[$key]);
                break;
            }
        }

        if ($product) {
            unset($product['status']);
            unset($product['source_keyword']);
            unset($product['score']);

            $data['products'][] = $product;
            $data['staging']['products'] = array_values($staging);

            file_put_contents($products_file, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n");
            $message = "✓ Product {$asin} approved!";
        }
    } elseif ($_POST['action'] === 'reject' && $asin) {
        // Remove from staging
        foreach ($staging as $key => $p) {
            if ($p['asin'] === $asin) {
                unset($staging[$key]);
                break;
            }
        }

        $data['staging']['products'] = array_values($staging);
        file_put_contents($products_file, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n");
        $message = "✗ Product {$asin} rejected";
    } elseif ($_POST['action'] === 'edit' && $asin) {
        // Update product details
        foreach ($staging as $key => $p) {
            if ($p['asin'] === $asin) {
                $staging[$key]['name'] = $_POST['name'] ?? $p['name'];
                $staging[$key]['blurb'] = $_POST['blurb'] ?? $p['blurb'];
                $staging[$key]['category'] = $_POST['category'] ?? $p['category'];
                $staging[$key]['award'] = $_POST['award'] ?? '';
                $staging[$key]['suits'] = $_POST['suits'] ?? '';
                $staging[$key]['check'] = $_POST['check'] ?? '';
                break;
            }
        }

        $data['staging']['products'] = $staging;
        file_put_contents($products_file, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . "\n");
        $message = "✓ Product details updated";
    }

    // Reload
    $staging = $data['staging']['products'] ?? [];
}

?>
<!DOCTYPE html>
<html>
<head>
    <title>Review Staged Products</title>
    <style>
        body { font-family: system-ui; max-width: 900px; margin: 20px auto; padding: 20px; }
        h1 { color: #333; }
        .product { border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 8px; }
        .product h3 { margin-top: 0; }
        .meta { color: #666; font-size: 0.9em; }
        input, textarea, select { padding: 6px; margin: 5px 0; width: 100%; box-sizing: border-box; }
        button { padding: 8px 16px; margin: 5px 5px 5px 0; cursor: pointer; }
        .approve { background: #0a0; color: white; border: none; }
        .reject { background: #a00; color: white; border: none; }
        .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .success { background: #efe; color: #060; }
        .error { background: #fee; color: #600; }
    </style>
</head>
<body>
    <h1>Review Staged Products</h1>

    <?php if (isset($message)): ?>
        <div class="message success"><?php echo htmlspecialchars($message); ?></div>
    <?php endif; ?>

    <p>Pending review: <strong><?php echo count($staging); ?></strong> products</p>

    <?php if (empty($staging)): ?>
        <p>No staged products waiting for review.</p>
    <?php else: ?>
        <?php foreach ($staging as $product): ?>
            <div class="product">
                <h3><?php echo htmlspecialchars($product['title'] ?? $product['name']); ?></h3>
                <div class="meta">
                    ASIN: <?php echo htmlspecialchars($product['asin']); ?> |
                    Category: <?php echo htmlspecialchars($product['category']); ?> |
                    Source: <?php echo htmlspecialchars($product['source_keyword'] ?? 'auto'); ?> |
                    Score: <?php echo number_format($product['score'] ?? 0, 1); ?>
                </div>

                <form method="POST" style="margin-top: 10px;">
                    <input type="hidden" name="asin" value="<?php echo htmlspecialchars($product['asin']); ?>">

                    <label>Product Name:</label>
                    <input type="text" name="name" value="<?php echo htmlspecialchars($product['name']); ?>">

                    <label>Blurb (short description):</label>
                    <textarea name="blurb" rows="2"><?php echo htmlspecialchars($product['blurb']); ?></textarea>

                    <label>Award/Label:</label>
                    <input type="text" name="award" value="<?php echo htmlspecialchars($product['award'] ?? ''); ?>" placeholder="e.g. Best budget option">

                    <label>Who it suits:</label>
                    <textarea name="suits" rows="2"><?php echo htmlspecialchars($product['suits'] ?? ''); ?></textarea>

                    <label>Before you buy:</label>
                    <textarea name="check" rows="2"><?php echo htmlspecialchars($product['check'] ?? ''); ?></textarea>

                    <div>
                        <button type="submit" name="action" value="edit">💾 Save Changes</button>
                        <button type="submit" name="action" value="approve" class="approve">✓ Approve</button>
                        <button type="submit" name="action" value="reject" class="reject">✗ Reject</button>
                    </div>
                </form>
            </div>
        <?php endforeach; ?>
    <?php endif; ?>

    <hr>
    <p><a href="/">← Back to site</a></p>
</body>
</html>
