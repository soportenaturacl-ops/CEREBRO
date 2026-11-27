CREATE TABLE campaigns (
    id TEXT PRIMARY KEY NOT NULL,
    currency TEXT NOT NULL CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
    spend_minor INTEGER NOT NULL CHECK (typeof(spend_minor) = 'integer' AND spend_minor >= 0),
    UNIQUE (id, currency)
);

CREATE TABLE transactions (
    id TEXT PRIMARY KEY NOT NULL,
    currency TEXT NOT NULL CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
    gross_minor INTEGER NOT NULL CHECK (typeof(gross_minor) = 'integer' AND gross_minor > 0),
    fee_minor INTEGER NOT NULL CHECK (typeof(fee_minor) = 'integer' AND fee_minor >= 0),
    campaign_id TEXT,
    UNIQUE (id, currency),
    FOREIGN KEY (campaign_id, currency) REFERENCES campaigns (id, currency)
);

CREATE TABLE refunds (
    id TEXT PRIMARY KEY NOT NULL,
    transaction_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (typeof(amount_minor) = 'integer' AND amount_minor > 0),
    FOREIGN KEY (transaction_id, currency) REFERENCES transactions (id, currency)
);

CREATE INDEX transactions_currency_campaign ON transactions (currency, campaign_id);
CREATE INDEX refunds_transaction_currency ON refunds (transaction_id, currency);

CREATE TRIGGER enforce_refund_limit
BEFORE INSERT ON refunds
WHEN NEW.amount_minor > (
    SELECT gross_minor FROM transactions WHERE id = NEW.transaction_id AND currency = NEW.currency
) - COALESCE((
    SELECT SUM(amount_minor) FROM refunds WHERE transaction_id = NEW.transaction_id AND currency = NEW.currency
), 0)
BEGIN
    SELECT RAISE(ABORT, 'refunds exceed the original transaction amount');
END;

CREATE VIEW unit_economics_metrics AS
SELECT t.id AS transaction_id, t.currency, t.campaign_id, t.gross_minor, t.fee_minor,
       COALESCE(SUM(r.amount_minor), 0) AS refund_minor
FROM transactions AS t
LEFT JOIN refunds AS r ON r.transaction_id = t.id AND r.currency = t.currency
GROUP BY t.id, t.currency, t.campaign_id, t.gross_minor, t.fee_minor;
