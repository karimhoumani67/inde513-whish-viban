"""
INDE 513 - Whish Money Virtual IBAN Payment Tracking System
Flask website connected to the SQLite database from Chapter 7.

Run locally:  pip install -r requirements.txt  ->  python app.py  ->  http://127.0.0.1:5000
"""
import os
import sqlite3
from datetime import datetime

from flask import Flask, flash, g, redirect, render_template, request, url_for

from queries import QUERIES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "whish_viban.db"))
TABLES = ["Bank", "MasterAccount", "Customer", "customerPhoneNumber", "customerEmailAddress",
          "CustomerBank", "VirtualIBAN", "LedgerAccount", "Payment", "LedgerEntry",
          "PaymentStatusHistory"]

app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="/static")
app.secret_key = os.environ.get("SECRET_KEY", "inde513-demo")


# ---------------------------------------------------------------- database
def build_database():
    """Create a fresh database from schema.sql + seed.sql."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    for f in ("schema.sql", "seed.sql"):
        with open(os.path.join(BASE_DIR, f), encoding="utf-8") as fh:
            con.executescript(fh.read())
    con.commit()
    con.close()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")   # required on every connection
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def q(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def money(value, currency=""):
    if value is None:
        return "-"
    v = float(value)
    s = f"{v:,.0f}" if currency == "LBP" else f"{v:,.2f}"
    return f"{s} {currency}".strip()


app.jinja_env.filters["money"] = money


# ---------------------------------------------------------------- pages
@app.route("/")
def dashboard():
    stats = {
        "customers": q("SELECT COUNT(*) n FROM Customer", one=True)["n"],
        "vibans": q("SELECT COUNT(*) n FROM VirtualIBAN WHERE status='Active'", one=True)["n"],
        "accounts": q("SELECT COUNT(*) n FROM MasterAccount", one=True)["n"],
        "payments": q("SELECT COUNT(*) n FROM Payment", one=True)["n"],
    }
    by_status = {r["status"]: r["n"] for r in
                 q("SELECT status, COUNT(*) n FROM Payment GROUP BY status")}
    received = q("""SELECT m.currency, SUM(p.amount) total
                    FROM Payment p JOIN VirtualIBAN v ON v.vIbanId=p.vIbanId
                    JOIN MasterAccount m ON m.accountId=v.accountId
                    WHERE p.status='Matched' GROUP BY m.currency ORDER BY m.currency""")
    recent = q("""SELECT p.paymentId, p.senderName, p.amount, p.status, m.currency, c.name customer,
                         (SELECT changeTimestamp FROM PaymentStatusHistory h
                          WHERE h.paymentId=p.paymentId ORDER BY sequenceNo DESC LIMIT 1) lastChange
                  FROM Payment p JOIN VirtualIBAN v ON v.vIbanId=p.vIbanId
                  JOIN MasterAccount m ON m.accountId=v.accountId
                  JOIN Customer c ON c.customerId=v.customerId
                  ORDER BY lastChange DESC LIMIT 5""")
    return render_template("dashboard.html", stats=stats, by_status=by_status,
                           received=received, recent=recent)


CUSTOMERS_SQL = """SELECT c.customerId, c.name, c.kycStatus, c.balanceCurrency,
       COALESCE(SUM(l.balance), 0) AS totalBalance,
       (SELECT COUNT(*) FROM VirtualIBAN v WHERE v.customerId = c.customerId) AS numVIbans
FROM Customer c
LEFT JOIN LedgerAccount l ON l.customerId = c.customerId
WHERE c.name LIKE ? AND (? = '' OR c.kycStatus = ?)
GROUP BY c.customerId
ORDER BY c.name;"""


@app.route("/customers")
def customers():
    search = request.args.get("q", "").strip()
    kyc = request.args.get("kyc", "")
    rows = q(CUSTOMERS_SQL, (f"%{search}%", kyc, kyc))
    return render_template("customers.html", rows=rows, search=search, kyc=kyc, sql=CUSTOMERS_SQL)


@app.route("/customers/<int:cid>")
def customer_detail(cid):
    c = q("SELECT * FROM Customer WHERE customerId=?", (cid,), one=True)
    if not c:
        flash("Customer not found.", "error")
        return redirect(url_for("customers"))
    phones = q("SELECT phoneNumber FROM customerPhoneNumber WHERE customerId=?", (cid,))
    emails = q("SELECT emailAddress FROM customerEmailAddress WHERE customerId=?", (cid,))
    banks = q("""SELECT b.bankId, b.name, b.bic FROM CustomerBank cb
                 JOIN Bank b ON b.bankId=cb.bankId WHERE cb.customerId=?""", (cid,))
    vibans = q("""SELECT v.*, m.realIBAN, m.currency, b.name bank,
                         (SELECT COUNT(*) FROM Payment p WHERE p.vIbanId=v.vIbanId) totalNumPayments
                  FROM VirtualIBAN v JOIN MasterAccount m ON m.accountId=v.accountId
                  JOIN Bank b ON b.bankId=m.bankId WHERE v.customerId=? ORDER BY v.vIbanId""", (cid,))
    ledgers = q("SELECT * FROM LedgerAccount WHERE customerId=?", (cid,))
    entries = q("""SELECT e.*, p.senderName, l.currency FROM LedgerEntry e
                   JOIN LedgerAccount l ON l.ledgerId=e.ledgerId
                   JOIN Payment p ON p.paymentId=e.paymentId
                   WHERE l.customerId=? ORDER BY e.entryId""", (cid,))
    payments = q("""SELECT p.*, m.currency FROM Payment p
                    JOIN VirtualIBAN v ON v.vIbanId=p.vIbanId
                    JOIN MasterAccount m ON m.accountId=v.accountId
                    WHERE v.customerId=? ORDER BY p.paymentId DESC""", (cid,))
    total = q("""SELECT SUM(balance) t, MIN(currency)=MAX(currency) AND MIN(currency)=? same
                 FROM LedgerAccount WHERE customerId=?""", (c["balanceCurrency"], cid), one=True)
    return render_template("customer_detail.html", c=c, phones=phones, emails=emails, banks=banks,
                           vibans=vibans, ledgers=ledgers, entries=entries, payments=payments,
                           total=total)


PAYMENTS_SQL = """SELECT p.paymentId, p.senderName, p.senderNote, p.amount, p.status,
       v.IBAN, v.vIbanId, c.customerId, c.name AS customer, m.currency
FROM Payment p
JOIN VirtualIBAN v   ON v.vIbanId = p.vIbanId
JOIN Customer c      ON c.customerId = v.customerId
JOIN MasterAccount m ON m.accountId = v.accountId
WHERE (? = '' OR p.status = ?)
  AND (p.senderName LIKE ? OR v.IBAN LIKE ? OR c.name LIKE ? OR CAST(p.paymentId AS TEXT) = ?)
ORDER BY p.paymentId DESC;"""


@app.route("/payments")
def payments():
    status = request.args.get("status", "")
    search = request.args.get("q", "").strip()
    like = f"%{search}%"
    rows = q(PAYMENTS_SQL, (status, status, like, like, like, search))
    return render_template("payments.html", rows=rows, status=status, search=search, sql=PAYMENTS_SQL)


@app.route("/payments/<int:pid>")
def payment_detail(pid):
    p = q("""SELECT p.*, v.IBAN, v.vIbanId, v.accountId, m.realIBAN, m.currency, b.name bank,
                    c.customerId, c.name customer
             FROM Payment p JOIN VirtualIBAN v ON v.vIbanId=p.vIbanId
             JOIN MasterAccount m ON m.accountId=v.accountId
             JOIN Bank b ON b.bankId=m.bankId
             JOIN Customer c ON c.customerId=v.customerId
             WHERE p.paymentId=?""", (pid,), one=True)
    if not p:
        flash("Payment not found.", "error")
        return redirect(url_for("payments"))
    history = q("SELECT * FROM PaymentStatusHistory WHERE paymentId=? ORDER BY sequenceNo", (pid,))
    entry = q("SELECT * FROM LedgerEntry WHERE paymentId=?", (pid,), one=True)
    return render_template("payment_detail.html", p=p, history=history, entry=entry)


@app.route("/payments/new", methods=["GET", "POST"])
def new_payment():
    vibans = q("""SELECT v.vIbanId, v.IBAN, c.name customer, m.currency
                  FROM VirtualIBAN v JOIN Customer c ON c.customerId=v.customerId
                  JOIN MasterAccount m ON m.accountId=v.accountId
                  WHERE v.status='Active' ORDER BY v.vIbanId""")
    if request.method == "POST":
        f = request.form
        db = get_db()
        try:
            amount = float(f.get("amount", ""))
        except ValueError:
            flash("Amount must be a number.", "error")
            return render_template("new_payment.html", vibans=vibans, form=f)
        try:
            with db:  # one transaction: Payment + first history record
                cur = db.execute(
                    "INSERT INTO Payment (senderName, senderNote, amount, vIbanId) VALUES (?, ?, ?, ?)",
                    (f.get("senderName", "").strip(), f.get("senderNote", "").strip() or None,
                     amount, int(f.get("vIbanId", 0))))
                pid = cur.lastrowid
                db.execute("""INSERT INTO PaymentStatusHistory (paymentId, sequenceNo, status, changeTimestamp)
                              VALUES (?, 1, 'Received', ?)""", (pid, now()))
        except sqlite3.IntegrityError as e:
            flash(f"Rejected by the database: {e}", "error")
            return render_template("new_payment.html", vibans=vibans, form=f)
        flash(f"Payment {pid} recorded with status Received.", "ok")
        return redirect(url_for("payment_detail", pid=pid))
    return render_template("new_payment.html", vibans=vibans, form={})


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.route("/payments/<int:pid>/match", methods=["POST"])
def match_payment(pid):
    db = get_db()
    p = q("""SELECT p.*, v.customerId, m.currency FROM Payment p
             JOIN VirtualIBAN v ON v.vIbanId=p.vIbanId
             JOIN MasterAccount m ON m.accountId=v.accountId WHERE p.paymentId=?""", (pid,), one=True)
    if not p or p["status"] != "Received":
        flash("Only a payment with status Received can be matched.", "error")
        return redirect(url_for("payment_detail", pid=pid))
    ledger = q("SELECT ledgerId FROM LedgerAccount WHERE customerId=? AND currency=? LIMIT 1",
               (p["customerId"], p["currency"]), one=True)
    if not ledger:
        flash(f"The customer has no {p['currency']} ledger account to credit.", "error")
        return redirect(url_for("payment_detail", pid=pid))
    try:
        with db:  # all-or-nothing: status, history, ledger entry, balance
            db.execute("UPDATE Payment SET status='Matched' WHERE paymentId=?", (pid,))
            db.execute("""INSERT INTO PaymentStatusHistory (paymentId, sequenceNo, status, reason, changeTimestamp)
                          VALUES (?, 2, 'Matched', ?, ?)""", (pid, f"Matched to virtual IBAN {p['vIbanId']}", now()))
            db.execute("INSERT INTO LedgerEntry (amount, direction, paymentId, ledgerId) VALUES (?, 'Credit', ?, ?)",
                       (p["amount"], pid, ledger["ledgerId"]))
            db.execute("UPDATE LedgerAccount SET balance = ROUND(balance + ?, 2) WHERE ledgerId=?",
                       (p["amount"], ledger["ledgerId"]))
    except sqlite3.IntegrityError as e:
        flash(f"Rejected by the database: {e}", "error")
        return redirect(url_for("payment_detail", pid=pid))
    flash(f"Payment {pid} matched and credited to ledger {ledger['ledgerId']}.", "ok")
    return redirect(url_for("payment_detail", pid=pid))


@app.route("/payments/<int:pid>/return", methods=["POST"])
def return_payment(pid):
    db = get_db()
    p = q("SELECT status FROM Payment WHERE paymentId=?", (pid,), one=True)
    if not p or p["status"] != "Received":
        flash("Only a payment with status Received can be returned.", "error")
        return redirect(url_for("payment_detail", pid=pid))
    reason = request.form.get("reason", "").strip() or "Returned to sender"
    try:
        with db:
            db.execute("UPDATE Payment SET status='Returned' WHERE paymentId=?", (pid,))
            db.execute("""INSERT INTO PaymentStatusHistory (paymentId, sequenceNo, status, reason, changeTimestamp)
                          VALUES (?, 2, 'Returned', ?, ?)""", (pid, reason, now()))
    except sqlite3.IntegrityError as e:
        flash(f"Rejected by the database: {e}", "error")
        return redirect(url_for("payment_detail", pid=pid))
    flash(f"Payment {pid} returned. No ledger entry was created.", "ok")
    return redirect(url_for("payment_detail", pid=pid))


@app.route("/payments/<int:pid>/double-credit", methods=["POST"])
def double_credit(pid):
    """Constraint demo (Chapter 7.4): try to credit an already-credited payment again."""
    db = get_db()
    e = q("SELECT * FROM LedgerEntry WHERE paymentId=?", (pid,), one=True)
    try:
        with db:
            db.execute("INSERT INTO LedgerEntry (amount, direction, paymentId, ledgerId) VALUES (?, 'Credit', ?, ?)",
                       (e["amount"], pid, e["ledgerId"]))
        flash("Unexpected: the second credit was accepted.", "error")
    except sqlite3.IntegrityError as err:
        flash(f"SQLite blocked the second credit: {err}", "ok")
    return redirect(url_for("payment_detail", pid=pid))


@app.route("/queries", methods=["GET", "POST"])
def queries():
    results = []
    for item in QUERIES:
        cur = get_db().execute(item["sql"])
        results.append({**item, "cols": [d[0] for d in cur.description], "rows": cur.fetchall()})
    custom = {"sql": "", "cols": [], "rows": [], "error": None}
    if request.method == "POST":
        custom["sql"] = request.form.get("sql", "").strip()
        first = custom["sql"].lstrip("(").split(None, 1)[0].upper() if custom["sql"] else ""
        if first not in ("SELECT", "WITH"):
            custom["error"] = "Only SELECT queries can be run here (the page opens the database read-only)."
        else:
            try:
                ro = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                cur = ro.execute(custom["sql"])
                custom["cols"] = [d[0] for d in cur.description]
                custom["rows"] = cur.fetchmany(200)
                ro.close()
            except sqlite3.Error as e:
                custom["error"] = str(e)
    return render_template("queries.html", results=results, custom=custom)


@app.route("/tables")
@app.route("/tables/<name>")
def tables(name="Bank"):
    if name not in TABLES:
        name = "Bank"
    counts = {t: q(f"SELECT COUNT(*) n FROM {t}", one=True)["n"] for t in TABLES}
    cur = get_db().execute(f"SELECT * FROM {name}")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    info = q(f"PRAGMA table_info({name})")
    fks = q(f"PRAGMA foreign_key_list({name})")
    ddl = q("SELECT sql FROM sqlite_master WHERE name=?", (name,), one=True)["sql"]
    return render_template("tables.html", tables=TABLES, counts=counts, name=name,
                           cols=cols, rows=rows, info=info, fks=fks, ddl=ddl)


@app.route("/reset", methods=["POST"])
def reset():
    close_db(None)
    build_database()
    flash("Demo data reset to the original sample records.", "ok")
    return redirect(url_for("dashboard"))


# Build the database when the app starts (Render's disk is temporary, so we always start clean).
if not os.path.exists(DB_PATH) or os.environ.get("RESET_DB_ON_START", "1") == "1":
    build_database()

if __name__ == "__main__":
    app.run(debug=True)
