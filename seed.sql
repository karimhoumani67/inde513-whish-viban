-- INDE 513 | Sample data (fictional - no real personal or confidential data)
-- Payments, update, delete and resulting balances match Chapter 7 of the report.
PRAGMA foreign_keys = ON;

-- Banks (bank 3 holds an account with no virtual IBANs -> optional participation)
INSERT INTO Bank (bankId, name, bic) VALUES
(1, 'Cedar Commercial Bank', 'CCBKLBBE'),
(2, 'Phoenicia Trust Bank', 'PHTBLBBE'),
(3, 'Mediterranean Union Bank', 'MDUBLBBEXXX');

-- Master (real) accounts: the pooled bank accounts
INSERT INTO MasterAccount (accountId, realIBAN, currency, bankId) VALUES
(101, 'LB62000100000000000010100001', 'USD', 1),
(102, 'LB71000200000000000010200002', 'USD', 2),
(103, 'LB15000100000000000010300003', 'LBP', 1),
(104, 'LB33000300000000000010400004', 'USD', 3);

-- Customers (kycStatus omitted for Rami -> DEFAULT 'Pending')
INSERT INTO Customer (customerId, name, kycStatus, balanceCurrency) VALUES
(1, 'Maya Haddad', 'Verified', 'USD'),
(2, 'Jad Nassar',  'Verified', 'USD'),
(3, 'Lina Saad',   'Verified', 'LBP');
INSERT INTO Customer (customerId, name, balanceCurrency) VALUES
(4, 'Rami Khoury', 'USD');

-- Multivalued attributes
INSERT INTO customerPhoneNumber (customerId, phoneNumber) VALUES
(1, '+961 70 100 001'), (1, '+961 01 100 002'),
(2, '+961 71 200 001'),
(3, '+961 76 300 001'),
(4, '+961 03 400 001');

INSERT INTO customerEmailAddress (customerId, emailAddress) VALUES
(1, 'maya@example.com'), (1, 'maya.old@example.com'),
(2, 'jad@example.com'),
(3, 'lina@example.com'), (3, 'lina.work@example.com'),
(4, 'rami@example.com');

-- M:N Bank-Customer association
INSERT INTO CustomerBank (bankId, customerId) VALUES
(1, 1), (2, 1), (1, 2), (1, 3);

-- Virtual IBANs (301 and 302 share master account 101; 305 is closed)
INSERT INTO VirtualIBAN (vIbanId, IBAN, status, closureDate, accountId, customerId, assignmentDate) VALUES
(301, 'LB62000100000000000030100301', 'Active', NULL, 101, 1, '2026-09-01'),
(302, 'LB62000100000000000030200302', 'Active', NULL, 101, 2, '2026-09-15'),
(303, 'LB71000200000000000030300303', 'Active', NULL, 102, 1, '2026-10-01'),
(304, 'LB15000100000000000030400304', 'Active', NULL, 103, 3, '2026-10-05'),
(305, 'LB62000100000000000030500305', 'Closed', '2026-10-20', 101, 2, '2026-09-20');

-- Ledger accounts (start at DEFAULT 0, credited below)
INSERT INTO LedgerAccount (ledgerId, currency, customerId) VALUES
(201, 'USD', 1), (202, 'USD', 2), (203, 'LBP', 3), (204, 'USD', 4);

-- The six incoming payments (status DEFAULT 'Received')
INSERT INTO Payment (paymentId, senderName, senderNote, amount, vIbanId) VALUES
(4001, 'Atlas Studio', 'Invoice 17', 250.00, 301),
(4002, 'North Books', NULL, 90.00, 302),
(4003, 'Olive Market', 'Invoice disputed', 125.00, 301),
(4004, 'Pine Design', NULL, 40.00, 302),
(4005, 'Atlas Studio', 'Invoice 24', 60.00, 303),
(4006, 'Coast Press', NULL, 450000.00, 304);

-- Status history: event 1 = Received for every payment
INSERT INTO PaymentStatusHistory (paymentId, sequenceNo, status, reason, changeTimestamp) VALUES
(4001, 1, 'Received', NULL, '2026-11-01 08:30:00'),
(4002, 1, 'Received', NULL, '2026-11-01 08:45:00'),
(4003, 1, 'Received', NULL, '2026-11-01 09:00:00'),
(4004, 1, 'Received', NULL, '2026-11-02 10:15:00'),
(4005, 1, 'Received', NULL, '2026-11-02 11:00:00'),
(4006, 1, 'Received', NULL, '2026-11-03 14:20:00');

-- Event 2: four matched, one returned (4004 stays Received)
INSERT INTO PaymentStatusHistory (paymentId, sequenceNo, status, reason, changeTimestamp) VALUES
(4001, 2, 'Matched',  'Matched to virtual IBAN 301', '2026-11-01 08:35:00'),
(4002, 2, 'Matched',  'Matched to virtual IBAN 302', '2026-11-01 08:50:00'),
(4003, 2, 'Returned', 'Sender requested return',     '2026-11-01 09:25:00'),
(4005, 2, 'Matched',  'Matched to virtual IBAN 303', '2026-11-02 11:05:00'),
(4006, 2, 'Matched',  'Matched to virtual IBAN 304', '2026-11-03 14:30:00');

UPDATE Payment SET status = 'Matched' WHERE paymentId IN (4001, 4002, 4005, 4006);
UPDATE Payment SET status = 'Returned' WHERE paymentId = 4003;

-- Ledger postings for matched payments
INSERT INTO LedgerEntry (entryId, amount, direction, paymentId, ledgerId) VALUES
(501, 250.00,    'Credit', 4001, 201),
(502, 90.00,     'Credit', 4002, 202),
(503, 60.00,     'Credit', 4005, 201),
(504, 450000.00, 'Credit', 4006, 203);

UPDATE LedgerAccount
SET balance = (SELECT COALESCE(SUM(CASE direction WHEN 'Credit' THEN amount ELSE -amount END), 0)
               FROM LedgerEntry e WHERE e.ledgerId = LedgerAccount.ledgerId);

-- Delete an outdated email address (Chapter 7.2)
DELETE FROM customerEmailAddress
WHERE customerId = 1 AND emailAddress = 'maya.old@example.com';
