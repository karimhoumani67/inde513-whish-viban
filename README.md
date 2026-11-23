# Whish Money – Virtual IBAN Payment Tracking System
INDE 513 Information Systems · Project Phase II website

A Flask website connected to the SQLite database from Chapter 7 of the report. Users can view, search and add records, and process payments (match or return them).

## Files
| File | Purpose |
|---|---|
| `schema.sql` | The 11 `CREATE TABLE` statements from Chapter 7, plus foreign-key indexes |
| `seed.sql` | Fictional sample data. It reproduces the Chapter 7 results (6 payments, the return of 4003, deletion of the old email) |
| `app.py` | Flask application (routes and database logic) |
| `queries.py` | The SQL queries shown on the *SQL Queries* page |
| `templates/`, `static/` | HTML pages and stylesheet |
| `requirements.txt`, `render.yaml` | Dependencies and Render deployment settings |
| `screenshots/` | Screenshots of each page for the report |

The database file `whish_viban.db` is created automatically from `schema.sql` + `seed.sql` each time the app starts. Every connection runs `PRAGMA foreign_keys = ON;`.

## Run locally
Requires Python 3.9+.
```bash
cd whish-viban
python -m venv venv
# Windows: venv\Scripts\activate     macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Put it online with Render (free)
1. Create a GitHub repository and upload the contents of this folder (keep `app.py` at the top level).
2. On https://render.com sign in with GitHub, then choose **New → Web Service** and select the repository.
3. Settings (Render reads them from `render.yaml`. If asked, enter them manually):
   - Runtime: **Python 3**
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --workers 1 --bind 0.0.0.0:$PORT`
   - Instance type: **Free**
4. Click **Create Web Service**. After about 2 minutes you get a link like `https://whish-viban-tracker.onrender.com`.

**Note:** The free tier sleeps after 15 minutes without visits, and the first visit then takes about 50 seconds. Open the site a few minutes before presenting. The disk is temporary, so data added online resets to the sample data on restart. This is intended for the demo.

## Pages
- **Dashboard**: payment flow, counts, payments by status, totals credited per currency, latest activity, and a *Reset demo data* button.
- **Customers**: search by name and filter by KYC status. The detail page shows phones and emails (multivalued), banks (M:N), virtual IBANs, ledgers, entries and payments.
- **Payments**: search by sender, customer, IBAN or ID, and filter by status. The detail page shows routing, the status-history timeline (weak entity), and the ledger posting.
- **+ New payment**: inserts a Payment and history record 1. The database CHECK constraints reject invalid input.
- **Match / Return**: one transaction that updates the status, adds history record 2, and (for a match) creates the credit LedgerEntry and updates the balance.
- **Try double credit**: re-runs the Chapter 7.4 test. The UNIQUE constraint on `LedgerEntry.paymentId` blocks it.
- **SQL Queries**: the report queries run live, plus a read-only box for any `SELECT` query.
- **Tables**: all 11 tables with their rows, columns, keys and `CREATE TABLE` statement.

## Suggested 3-minute demo
1. Dashboard: explain the flow.
2. Customers → Maya Haddad: two virtual IBANs on two banks, balance 310 USD.
3. Payments → #4003: the Returned timeline.
4. + New payment: enter **-50** to show the rejection, then enter **175.50** to vIBAN 301.
5. Match it. Maya's balance becomes 485.50 USD. Then click *Try double credit* to show the block.
6. SQL Queries: the balances query now shows 485.50.
7. Reset demo data.
