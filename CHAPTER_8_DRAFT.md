# Chapter 8: Website

## 8.1 Overview
To demonstrate the database, we built a website connected to the SQLite database from Chapter 7. The site lets a user view and search customers and payments, record a new incoming payment, and match it to the customer's ledger or return it to the sender. Every page reads from and writes to the same eleven tables, so the relationships, constraints and queries from the earlier chapters can be shown working live.

Website link: `[insert Render link]`

## 8.2 Tools used
- **Python 3 and Flask**: web framework that handles the pages and forms.
- **SQLite** (Python `sqlite3` module): the database. On startup the website builds it from `schema.sql` (Chapter 7 tables) and `seed.sql` (sample data). `PRAGMA foreign_keys = ON;` runs on every connection.
- **HTML, CSS and Jinja templates**: page layout.
- **Render**: free hosting for the online version.
- **[AI tool used, e.g. Claude]**: helped write the code (see 8.5).

## 8.3 Main features
| Page | What it shows | Database concepts demonstrated |
|---|---|---|
| Dashboard (Figure 8.1) | Payment flow, record counts, payments by status, totals credited per currency | Aggregates (`COUNT`, `SUM`, `GROUP BY`) |
| Customers (Figures 8.2–8.3) | Search by name and KYC status; customer profile | Multivalued attributes (phones, emails), M:N `CustomerBank`, 1:M virtual IBANs and ledgers, derived `totalBalance` |
| Payments (Figures 8.4–8.5) | Search by sender, customer, IBAN or ID; filter by status; payment detail | Multi-table joins, weak entity `PaymentStatusHistory`, 1:1 posting to `LedgerEntry` |
| New payment (Figures 8.6, 8.9) | Form to record an incoming payment | `INSERT`, `DEFAULT 'Received'`, `CHECK` constraints, foreign key to `VirtualIBAN` |
| Match / Return | Processes a received payment | One transaction: `UPDATE` status, history record 2, credit `LedgerEntry`, balance update |
| SQL Queries (Figure 8.7) | The Chapter 7 queries and derived attributes, run live | Filtering, sorting, joins, aggregates, `GROUP BY`, `HAVING` |
| Tables (Figure 8.8) | All 11 tables with rows, columns, keys and DDL | Final normalized schema |

Because the website and the queries share one database, a change on one page shows up on the others. For example, matching a new 175.50 USD payment to virtual IBAN 301 raises Maya Haddad's balance from 310 to 485.50 USD on her profile and in the balance query. Clicking *Try double credit* on a matched payment re-runs the test from Section 7.4. SQLite rejects it with `UNIQUE constraint failed: LedgerEntry.paymentId`.

Input that breaks the data dictionary rules is rejected by the database itself rather than by the website. Examples are a negative amount, an amount with three decimals, or an empty sender name (Figure 8.9).

## 8.4 Screenshots
- Figure 8.1 Dashboard (`01_dashboard.png`)
- Figure 8.2 Customer search (`02_customers.png`)
- Figure 8.3 Customer profile, Maya Haddad (`03_customer_maya.png`)
- Figure 8.4 Payment search (`04_payments.png`)
- Figure 8.5 Payment 4003 with its status history (`05_payment_4003.png`)
- Figure 8.6 New payment form (`06_new_payment.png`)
- Figure 8.7 SQL queries page (`07_queries.png`)
- Figure 8.8 Table browser, VirtualIBAN (`08_tables.png`)
- Figure 8.9 CHECK constraint rejecting a negative amount (`09_check_rejected.png`)

## 8.5 Use of AI
We used [AI tool] to generate the first version of the Flask code, the HTML templates and the stylesheet. We gave it our Chapter 7 SQL and asked for pages to view, search and add records. The table definitions were not changed: the website loads our own `schema.sql`. We checked the output by running the website and confirming three things. First, the Chapter 7 queries returned the same results as in the report. Second, invalid inputs were rejected by our CHECK constraints. Third, matching a payment updated the history, ledger entry and balance correctly. [Add what your team changed or fixed yourselves.]

## 8.6 Running the website
Setup instructions are in `README.md` in the project ZIP. In short: run `pip install -r requirements.txt`, then `python app.py`, then open http://127.0.0.1:5000.
