import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id = session["user_id"]
    x = db.execute("SELECT cash FROM users WHERE id=?", id)
    cash = x[0]['cash']
    username = db.execute("SELECT username FROM users WHERE id=?", id)[0]["username"]
    symbols = db.execute("SELECT DISTINCT symbol FROM purchases WHERE buyer=?", username)
    print(symbols)
    share = db.execute("SELECT SUM(shares) FROM purchases GROUP BY symbol HAVING buyer=?", username)
    print(share)
    shares = []
    for item in share:
        shares.append(item["SUM(shares)"])
    print(shares)
    price = db.execute("SELECT price FROM purchases GROUP BY symbol HAVING buyer=?", username)
    print(price)
    prices = []
    total = db.execute("SELECT SUM(price) FROM purchases WHERE buyer=?", username)
    print(total)
    totals = 0;
    if not total[0]['SUM(price)'] == None:
        totals = total[0]["SUM(price)"]
    print(totals)
    for item in price:
        prices.append(item["price"])
    symbol = []
    print(prices)
    for item in symbols:
        symbol.append(lookup(item["symbol"]))
    print(symbol)
    return render_template("index.html", symbol=symbol, shares=shares, prices=prices, totals=totals, cash=cash)
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        if not lookup(symbol):
            return apology("Symbol does not exist")
        quote = lookup(symbol)
        #shares =
        shares = 0
        if float(request.form.get("shares")) % 1 != 0:
            return apology("Must be integer")
        else:
            shares = float(request.form.get("shares"))
        if not shares > 0:
            return apology("Enter a positive number")
        cost = quote["price"] * shares
        id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id=?", id)
        if cost > cash[0]["cash"]:
            return apology("Not enough cash")
        date = datetime.now()
        current_time = date.strftime("%d/%m/%y %H:%M:%S")
        print("Current Time =", current_time)
        username = db.execute("SELECT username FROM users WHERE id=?", id)[0]["username"]
        db.execute("INSERT INTO purchases (buyer, symbol, shares, price, time) VALUES(?, ?, ?, ?, ?)", username, symbol, shares, cost, current_time)
        db.execute("UPDATE users SET cash=? WHERE username=?", cash[0]["cash"] - cost, username)
        db.execute("INSERT INTO history (symbol, shares, price, type, transacted) VALUES(?,?,?,'buy',?)", symbol, shares, cost, current_time)
        return redirect("/")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT * FROM history")
    return render_template("history.html", history=history)
    print(history)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        quote = lookup(request.form.get("symbol"))
        if not quote:
            return apology("Quote not found")

        return render_template("quoted.html", quote=quote)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        name = db.execute("SELECT username FROM users")
        names = []
        for n in name:
            names.append(n["username"])
        if not request.form.get("username"):
            return apology("Must enter username")
        elif request.form.get("username") in names:
            return apology("Username not available")
        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Must enter password")
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords not identical")
        elif len(request.form.get("password")) < 8:
            return apology("Passowrd must be atleast 8 characters")
        name = request.form.get("username")
        hashp = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", name, hashp)
        return render_template("login.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    id = session["user_id"]
    username = db.execute("SELECT username FROM users WHERE id=?", id)[0]["username"]
    if request.method == "GET":

        symbols = db.execute("SELECT DISTINCT symbol FROM purchases WHERE buyer=?", username)
        symbol = []
        for item in symbols:
            symbol.append(item["symbol"])
        return render_template("sell.html", symbol=symbol)
    else:
        item = request.form.get("symbol")
        if not item:
            return apology("Choose Stock")
        num = int(request.form.get("shares"))
        available = db.execute("SELECT SUM(shares) FROM purchases GROUP BY symbol HAVING buyer=? AND symbol=?", username, item)[0]['SUM(shares)']
        if num == 0:
            return apology("Enter positive number")
        elif num > available:
            return apology("Not enough stock")
        info = lookup(item);
        profit = info["price"] * num
        now = datetime.now()
        current_time = now.strftime("%d/%m/%y %H:%M:%S")
        db.execute("UPDATE purchases SET price=price - (?) WHERE buyer =? AND symbol=? LIMIT 1", profit, username, item)
        db.execute("UPDATE purchases SET shares=shares - (?) WHERE buyer=? AND symbol=? LIMIT 1", num, username, item)
        db.execute("UPDATE users SET cash=cash+(?) WHERE username=?", profit, username)
        db.execute("INSERT INTO history (symbol, shares, price, type, transacted) VALUES(?,?,?,'sell',?)", item, num, profit, current_time)
        return redirect("/")



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
