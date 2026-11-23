-- INDE 513 | Whish Money Virtual IBAN Payment Tracking System
-- Schema taken verbatim from Chapter 7 of the final report

PRAGMA foreign_keys = ON;
CREATE TABLE Bank (
bankId INTEGER PRIMARY KEY CHECK (bankId > 0),
name VARCHAR(100) NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
bic VARCHAR(11) NOT NULL UNIQUE
CHECK (length(bic) IN (8, 11) AND bic NOT GLOB '*[^A-Z0-9]*')
);
CREATE TABLE MasterAccount (
accountId INTEGER PRIMARY KEY CHECK (accountId > 0),
realIBAN VARCHAR(34) NOT NULL UNIQUE
CHECK (length(realIBAN) BETWEEN 15 AND 34 AND realIBAN NOT GLOB '*[^A-Z0-9]*'),
currency CHAR(3) NOT NULL CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
bankId INTEGER NOT NULL,
FOREIGN KEY (bankId) REFERENCES Bank(bankId)
);
CREATE TABLE Customer (
customerId INTEGER PRIMARY KEY CHECK (customerId > 0),
name VARCHAR(100) NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
kycStatus VARCHAR(8) NOT NULL DEFAULT 'Pending'
CHECK (kycStatus IN ('Pending', 'Verified', 'Rejected')),
balanceCurrency CHAR(3) NOT NULL CHECK (balanceCurrency GLOB '[A-Z][A-Z][A-Z]')
);
CREATE TABLE customerPhoneNumber (
customerId INTEGER NOT NULL,
phoneNumber VARCHAR(20) NOT NULL CHECK (length(phoneNumber) BETWEEN 1 AND 20),
PRIMARY KEY (customerId, phoneNumber),
FOREIGN KEY (customerId) REFERENCES Customer(customerId)
);
CREATE TABLE customerEmailAddress (
customerId INTEGER NOT NULL,
emailAddress VARCHAR(254) NOT NULL
CHECK (length(emailAddress) BETWEEN 1 AND 254 AND emailAddress LIKE '_%@_%._%'
AND emailAddress NOT LIKE '%@%@%' AND emailAddress NOT LIKE '% %'),
PRIMARY KEY (customerId, emailAddress),
FOREIGN KEY (customerId) REFERENCES Customer(customerId)
);
CREATE TABLE CustomerBank (
bankId INTEGER NOT NULL,
customerId INTEGER NOT NULL,
PRIMARY KEY (bankId, customerId),
FOREIGN KEY (bankId) REFERENCES Bank(bankId),
FOREIGN KEY (customerId) REFERENCES Customer(customerId)
);
CREATE TABLE VirtualIBAN (
vIbanId INTEGER PRIMARY KEY CHECK (vIbanId > 0),
IBAN VARCHAR(34) NOT NULL UNIQUE
CHECK (length(IBAN) BETWEEN 15 AND 34 AND IBAN NOT GLOB '*[^A-Z0-9]*'),
status VARCHAR(6) NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Closed')),
closureDate TEXT CHECK (closureDate IS NULL OR (length(closureDate) = 10 AND date(closureDate, '+0 days') IS closureDate)),
accountId INTEGER NOT NULL,
customerId INTEGER NOT NULL,
assignmentDate TEXT NOT NULL CHECK (length(assignmentDate) = 10 AND date(assignmentDate, '+0 days') IS assignmentDate),
FOREIGN KEY (accountId) REFERENCES MasterAccount(accountId),
FOREIGN KEY (customerId) REFERENCES Customer(customerId),
CHECK (status <> 'Active' OR closureDate IS NULL),
CHECK (closureDate IS NULL OR closureDate >= assignmentDate)
);
CREATE TABLE LedgerAccount (
ledgerId INTEGER PRIMARY KEY CHECK (ledgerId > 0),
balance NUMERIC(12,2) NOT NULL DEFAULT 0
CHECK (balance >= -9999999999.99 AND balance <= 9999999999.99
AND balance = ROUND(balance, 2)),
currency CHAR(3) NOT NULL CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
customerId INTEGER NOT NULL,
FOREIGN KEY (customerId) REFERENCES Customer(customerId)
);
CREATE TABLE Payment (
paymentId INTEGER PRIMARY KEY CHECK (paymentId > 0),
senderName VARCHAR(100) NOT NULL CHECK (length(senderName) BETWEEN 1 AND 100),
senderNote VARCHAR(255) CHECK (length(senderNote) <= 255),
amount NUMERIC(12,2) NOT NULL
CHECK (amount > 0 AND amount <= 9999999999.99
AND amount = ROUND(amount, 2)),
status VARCHAR(8) NOT NULL DEFAULT 'Received'
CHECK (status IN ('Received', 'Matched', 'Returned')),
vIbanId INTEGER NOT NULL,
FOREIGN KEY (vIbanId) REFERENCES VirtualIBAN(vIbanId)
);
CREATE TABLE LedgerEntry (
entryId INTEGER PRIMARY KEY CHECK (entryId > 0),
amount NUMERIC(12,2) NOT NULL
CHECK (amount > 0 AND amount <= 9999999999.99
AND amount = ROUND(amount, 2)),
direction VARCHAR(6) NOT NULL CHECK (direction IN ('Credit', 'Debit')),
paymentId INTEGER NOT NULL UNIQUE,
ledgerId INTEGER NOT NULL,
FOREIGN KEY (paymentId) REFERENCES Payment(paymentId),
FOREIGN KEY (ledgerId) REFERENCES LedgerAccount(ledgerId)
);
CREATE TABLE PaymentStatusHistory (
paymentId INTEGER NOT NULL,
sequenceNo INTEGER NOT NULL,
status VARCHAR(8) NOT NULL,
reason VARCHAR(255) CHECK (length(reason) <= 255),
changeTimestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
CHECK (length(changeTimestamp) = 19
AND datetime(changeTimestamp, '+0 seconds') IS changeTimestamp),
PRIMARY KEY (paymentId, sequenceNo),
FOREIGN KEY (paymentId) REFERENCES Payment(paymentId),
CHECK ((sequenceNo = 1 AND status = 'Received')
OR (sequenceNo = 2 AND status IN ('Matched', 'Returned')))
);

-- Lookup indexes on foreign keys
CREATE INDEX idx_master_bank      ON MasterAccount(bankId);
CREATE INDEX idx_viban_account    ON VirtualIBAN(accountId);
CREATE INDEX idx_viban_customer   ON VirtualIBAN(customerId);
CREATE INDEX idx_ledger_customer  ON LedgerAccount(customerId);
CREATE INDEX idx_payment_viban    ON Payment(vIbanId);
CREATE INDEX idx_entry_ledger     ON LedgerEntry(ledgerId);
