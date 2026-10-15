-- AEPS response tables. They have no JPA entity (the API only counts their rows),
-- so Hibernate does not create them; this does, for the SQLite demo database.
CREATE TABLE IF NOT EXISTS instant_pay_withdrawal_response_data (id INTEGER PRIMARY KEY, agentid TEXT, amount TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS instant_pay_mini_statement_response_ministatement (id INTEGER PRIMARY KEY, agentid TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS instant_pay_balance_enquiry_response_data (id INTEGER PRIMARY KEY, agentid TEXT, created_at TEXT);
