"""Report queries shown on the SQL Queries page (Chapter 7.3 plus derived attributes)."""

QUERIES = [
    {
        "id": "routing",
        "title": "Which customer and ledger did each payment reach?",
        "concepts": "4-table JOIN, LEFT JOIN, ORDER BY",
        "explain": "Payments 4001 and 4002 reach the same master account (101), but their different "
                   "virtual IBANs identify different customers. LEFT JOIN keeps payments that have no ledger entry yet.",
        "sql": """SELECT p.paymentId, p.vIbanId, v.accountId, c.name AS customer, p.amount,
       m.currency, p.status, e.ledgerId
FROM Payment AS p
JOIN VirtualIBAN AS v ON v.vIbanId = p.vIbanId
JOIN MasterAccount AS m ON m.accountId = v.accountId
JOIN Customer AS c ON c.customerId = v.customerId
LEFT JOIN LedgerEntry AS e ON e.paymentId = p.paymentId
ORDER BY p.paymentId;""",
    },
    {
        "id": "returned",
        "title": "Why was payment 4003 returned?",
        "concepts": "WHERE filter, ORDER BY, weak entity",
        "explain": "The weak entity PaymentStatusHistory records the receipt at 09:00 and the return at 09:25.",
        "sql": """SELECT sequenceNo, status, changeTimestamp, reason
FROM PaymentStatusHistory
WHERE paymentId = 4003
ORDER BY sequenceNo;""",
    },
    {
        "id": "balances",
        "title": "What is each customer's balance? (derived totalBalance)",
        "concepts": "JOIN, SUM, GROUP BY, HAVING",
        "explain": "GROUP BY collects each customer's ledgers. HAVING keeps a customer only when all their "
                   "ledgers use the reporting currency, so USD and LBP are never added together.",
        "sql": """SELECT c.customerId, c.name, c.balanceCurrency, SUM(l.balance) AS totalBalance
FROM Customer AS c
JOIN LedgerAccount AS l ON l.customerId = c.customerId
GROUP BY c.customerId, c.name, c.balanceCurrency
HAVING MIN(l.currency) = c.balanceCurrency
   AND MAX(l.currency) = c.balanceCurrency
ORDER BY c.customerId;""",
    },
    {
        "id": "perviban",
        "title": "How many payments has each virtual IBAN received? (derived totalNumPayments)",
        "concepts": "LEFT JOIN, COUNT, GROUP BY, ORDER BY DESC",
        "explain": "totalNumPayments is not stored; it is counted from Payment. LEFT JOIN keeps IBANs with zero payments.",
        "sql": """SELECT v.vIbanId, v.IBAN, c.name AS customer, v.status,
       COUNT(p.paymentId) AS totalNumPayments
FROM VirtualIBAN AS v
JOIN Customer AS c ON c.customerId = v.customerId
LEFT JOIN Payment AS p ON p.vIbanId = v.vIbanId
GROUP BY v.vIbanId
ORDER BY totalNumPayments DESC, v.vIbanId;""",
    },
    {
        "id": "custbank",
        "title": "Bank-customer association summary (derived CustomerBank attributes)",
        "concepts": "Multi-table JOIN, COUNT DISTINCT, MIN, conditional SUM, GROUP BY",
        "explain": "Derives numVirtualIBANs, numMasterAccounts, firstAssociationDate and the amount posted "
                   "to the ledger for each bank-customer pair. Amounts are kept in the account currency.",
        "sql": """SELECT b.name AS bank, c.name AS customer,
       COUNT(DISTINCT v.vIbanId)   AS numVirtualIBANs,
       COUNT(DISTINCT v.accountId) AS numMasterAccounts,
       MIN(v.assignmentDate)       AS firstAssociationDate,
       m.currency,
       COALESCE(SUM(CASE WHEN p.status = 'Matched' THEN p.amount END), 0) AS totalReceived
FROM CustomerBank AS cb
JOIN Bank AS b          ON b.bankId = cb.bankId
JOIN Customer AS c      ON c.customerId = cb.customerId
JOIN VirtualIBAN AS v   ON v.customerId = cb.customerId
JOIN MasterAccount AS m ON m.accountId = v.accountId AND m.bankId = cb.bankId
LEFT JOIN Payment AS p  ON p.vIbanId = v.vIbanId
GROUP BY cb.bankId, cb.customerId, m.currency
ORDER BY b.name, c.name;""",
    },
    {
        "id": "multi",
        "title": "Which customers hold more than one virtual IBAN?",
        "concepts": "GROUP BY, HAVING COUNT > 1",
        "explain": "HAVING filters groups after aggregation, here customers with two or more virtual IBANs.",
        "sql": """SELECT c.customerId, c.name, COUNT(*) AS numVirtualIBANs
FROM Customer AS c
JOIN VirtualIBAN AS v ON v.customerId = c.customerId
GROUP BY c.customerId, c.name
HAVING COUNT(*) > 1;""",
    },
]
