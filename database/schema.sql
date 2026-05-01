-- Support articles searched by the agent via FULLTEXT Boolean Mode
CREATE TABLE IF NOT EXISTS knowledge_base (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(255)  NOT NULL,
    content     LONGTEXT      NOT NULL,
    category    VARCHAR(100)  NOT NULL DEFAULT 'general',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    FULLTEXT idx_kb_search (title, content),
    INDEX idx_kb_category   (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Persistent key-value facts per user; UNIQUE enables upsert
CREATE TABLE IF NOT EXISTS user_memory (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id       VARCHAR(128)  NOT NULL,
    memory_key    VARCHAR(255)  NOT NULL,
    memory_value  TEXT          NOT NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_memory (user_id, memory_key),
    INDEX idx_um_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Short-term conversation history; one row per TResponseInputItem (JSON)
CREATE TABLE IF NOT EXISTS conversations (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id  VARCHAR(255)  NOT NULL,
    user_id     VARCHAR(128)  NOT NULL,
    role        VARCHAR(32)   NOT NULL,
    content     LONGTEXT      NOT NULL,
    created_at  DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_conv_session  (session_id, id),
    INDEX idx_conv_user     (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample knowledge base articles for testing
INSERT IGNORE INTO knowledge_base (title, content, category) VALUES
(
    'Order Tracking and Delivery Status',
    'You can track your order by logging into your account and visiting the "My Orders" section. Each order shows a real-time tracking link once it has been dispatched. Standard delivery takes 3-5 business days. Express delivery takes 1-2 business days. If your tracking shows "delivered" but you have not received the package, please wait 24 hours as sometimes carriers mark packages early. After 24 hours, contact our support team with your order number.',
    'shipping'
),
(
    'Return and Refund Policy',
    'We accept returns within 30 days of delivery for unused items in original packaging. To initiate a return, log into your account, go to "My Orders", select the item, and click "Return Item". You will receive a prepaid shipping label by email within 24 hours. Refunds are processed within 5-7 business days after we receive the returned item. Sale items and digital downloads are non-refundable. Premium members receive free returns with no questions asked.',
    'returns'
),
(
    'Account Tiers and Benefits',
    'We offer three account tiers: Standard, Plus, and Premium. Standard accounts have free shipping on orders over $50. Plus accounts ($9.99/month) get free shipping on all orders and priority customer support. Premium accounts ($19.99/month) get free shipping, priority support, free returns, early access to sales, and a dedicated account manager. You can upgrade your plan at any time from your Account Settings page.',
    'billing'
),
(
    'Password Reset and Account Security',
    'To reset your password, click "Forgot Password" on the login page and enter your email address. You will receive a reset link valid for 1 hour. If you do not receive the email, check your spam folder or try again in 5 minutes. For account security, we recommend enabling two-factor authentication (2FA) in Account Settings > Security. If you suspect unauthorised access, change your password immediately and contact support.',
    'account'
),
(
    'Payment Methods and Billing Issues',
    'We accept Visa, Mastercard, American Express, PayPal, and Apple Pay. All payments are processed securely via Stripe. If your payment fails, check that your billing address matches your card on file, your card has not expired, and you have sufficient funds. For subscription billing issues, go to Account Settings > Billing to update your payment method. Invoices are emailed on the 1st of each month for subscription accounts.',
    'billing'
);
