-- FAKE demo data only. No real people, accounts or transactions.
-- Demo logins: demo.admin / DemoAdmin@2026, demo.branch / DemoBranch@2026 (BCrypt hashed).
INSERT OR IGNORE INTO tblaccountadmin (id, username, password, mobile, session, branch, updationdate) VALUES
  (1, 'demo.admin',  '$2a$10$MdqnJ4p.BGIL700niUaxnOuyLQkX6g.YKoTIq9p7ZK4Sx3RanHr0W', '9000000001', 'active', 'Head Office',  '2026-10-01'),
  (2, 'demo.branch', '$2a$10$7Ta1OVKQuWq3HMo3evOEJOcAWP9aAGQkcF3DpxuPX52WA1yUBzkwu', '9000000002', 'active', 'Demo Branch 1', '2026-10-01');

-- Wallet ledger. A withdrawal (txntypeid 2 = AEPS cash withdrawal, 3 = micro-ATM withdrawal)
-- has a companion settlement row (txntypeid 5) whose refid points back to it; the reports
-- join the two and take the date from the settlement row.
INSERT OR IGNORE INTO imagentwallettransactions (id, agentid, refid, txnamount, txndatetime, txntypeid) VALUES
  (1,  'AG1001', NULL, '1500', '2026-09-03 10:12:00', '2'),
  (2,  'AG1001', NULL, '2500', '2026-09-18 15:40:00', '3'),
  (3,  'AG1002', NULL, '800',  '2026-09-21 11:05:00', '2'),
  (4,  'AG1002', NULL, '4000', '2026-10-02 09:30:00', '2'),
  (5,  'AG1003', NULL, '1200', '2026-10-06 13:20:00', '3'),
  (6,  'AG1001', NULL, '3000', '2026-10-09 17:55:00', '2'),
  (101, 'AG1001', '1', '1425', '2026-09-03 10:12:05', '5'),
  (102, 'AG1001', '2', '2375', '2026-09-18 15:40:04', '5'),
  (103, 'AG1002', '3', '760',  '2026-09-21 11:05:06', '5'),
  (104, 'AG1002', '4', '3800', '2026-10-02 09:30:03', '5'),
  (105, 'AG1003', '5', '1140', '2026-10-06 13:20:02', '5'),
  (106, 'AG1001', '6', '2850', '2026-10-09 17:55:07', '5');

INSERT OR IGNORE INTO instant_pay_withdrawal_response_data (id, agentid, amount, created_at) VALUES
  (1, 'AG1001', '1500', '2026-09-03'), (2, 'AG1002', '800', '2026-09-21'),
  (3, 'AG1002', '4000', '2026-10-02'), (4, 'AG1001', '3000', '2026-10-09');
INSERT OR IGNORE INTO instant_pay_mini_statement_response_ministatement (id, agentid, created_at) VALUES
  (1, 'AG1001', '2026-09-05'), (2, 'AG1003', '2026-10-06');
INSERT OR IGNORE INTO instant_pay_balance_enquiry_response_data (id, agentid, created_at) VALUES
  (1, 'AG1001', '2026-09-03'), (2, 'AG1002', '2026-09-21'), (3, 'AG1003', '2026-10-06');
