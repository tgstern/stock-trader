import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup

# Configure application
app = Flask(__name__)

# export API_KEY=pk_8aca4a2dc2d9498dbf069d57d93421d1

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom usd format filter
@app.template_filter('usd')
def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


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

    # Select all user data from database to pass to template
    cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])
    cash = cash[0]["cash"]
    portfolio = db.execute(
        "SELECT symbol, name, value, SUM(shares), total, totalval FROM portfolio WHERE id = :id GROUP BY symbol", id=session['user_id'])
    net = 0

    # lookup current stock information and update database
    for i in range(len(portfolio)):
        symbol = portfolio[i]["symbol"]
        total = portfolio[i]["SUM(shares)"]
        pricecheck = lookup(symbol)
        totalval = pricecheck["price"] * total
        net += totalval
        db.execute("UPDATE portfolio SET total = :total, totalval = :totalval WHERE symbol = :symbol",
                   total=total, totalval=totalval, symbol=symbol)

    # refresh porfolio with new data to push to html page
    portfolio = db.execute(
        "SELECT symbol, name, total, totalval FROM portfolio WHERE id = :id GROUP BY symbol HAVING total > 0", id=session['user_id'])

    # sum of accounts
    net += cash

    # Generate user stock portfolio
    return render_template("index.html", cash=cash, portfolio=portfolio, net=net)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # Generate buy form
    if request.method == "GET":
        return render_template("buy.html")

    # Generate results
    if request.method == "POST":

        # Lookup stock information
        cost = lookup(request.form.get("symbol"))

        # Check for valid stock symbol and amount
        if not cost:
            return apology("Stock symbol not found")
        try:
            if int(request.form.get("shares")) <= 0:
                return apology("Numbers of shares must be positive")
        except:
            return apology("Please enter a valid number of shares")

        # Store stock variables
        name = cost["name"]
        price = cost["price"]
        value = cost["price"]
        symbol = cost["symbol"]
        shares = int(request.form.get("shares"))
        cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])
        time = datetime.now()

        # Check that user can afford the stock purchase
        if price * shares > cash[0]["cash"]:
            return apology("Insufficient funds for this purchase")

        # Purchase stock by updating portfolio database and users cash amount
        else:
            db.execute("INSERT INTO portfolio (id, symbol, name, shares, price, value, time) VALUES(:id, :symbol, :name, :shares, :price, :value, :time);",
                       id=session['user_id'], symbol=symbol, name=name, shares=shares, price=price, value=value, time=time)
            db.execute("UPDATE users SET cash = cash - :cost WHERE id = :id", cost=price * shares, id=session['user_id'])
            return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Select all user data from database to pass to template
    portfolio = db.execute("SELECT * FROM portfolio WHERE id = :id", id=session['user_id'])

    # Generate user transaction history
    return render_template("history.html", portfolio=portfolio)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password")

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


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():

    # generate account options page
    if request.method == "GET":
        return render_template("account.html")

    # execute account options
    if request.method == "POST":

        # reset users stock history and cash amount
        if request.form.get("account") == "reset":
            db.execute("DELETE FROM portfolio WHERE id = :id", id=session["user_id"])
            db.execute("UPDATE users SET cash = 10000 WHERE id = :id", id=session["user_id"])
            return redirect("/")

        # remove user from the database and clear session
        if request.form.get("account") == "delete":
            db.execute("DELETE FROM portfolio WHERE id = :id", id=session["user_id"])
            db.execute("DELETE FROM users WHERE id = :id", id=session["user_id"])
            session.clear()
            return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # generate template for form submission
    if request.method == "GET":
        return render_template("quote.html")

    # generate results of the quote
    if request.method == "POST":

        # Lookup stock information
        quote = lookup(request.form.get("symbol"))

        # Check for valid stock symbol
        if not quote:
            return apology("Stock symbol not found")

        # Pass prices to quoted.html
        return render_template("quoted.html", name=quote["name"], price=quote["price"], symbol=quote["symbol"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # On form submission
    if request.method == "POST":

        # Ensure username provided
        if not request.form.get("username"):
            return apology("Missing username!")

        # Ensure password and password confirmation provided
        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Please enter your password")

        # Check that passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Password do not match")

        else:
            # Hash password
            hash = generate_password_hash(request.form.get("password"))

            # Store user in database
            result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                                username=request.form.get("username"), hash=hash)
            if not result:
                return apology("Account name taken")

            # Remember user login
            session["user_id"] = result

            # Redirect user to home page
            return redirect("/")

    else:
        # Generate webpage
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Generate sell form
    if request.method == "GET":
        portfolio = db.execute(
            "SELECT symbol FROM portfolio WHERE id = :id GROUP BY symbol HAVING SUM(shares) > 0", id=session['user_id'])
        return render_template("sell.html", portfolio=portfolio)

    # Generate results
    if request.method == "POST":

        # Lookup stock information
        cost = lookup(request.form.get("symbol"))

        # Check for valid stock symbol and amount
        if not cost:
            return apology("Stock symbol not found")
        try:
            if int(request.form.get("shares")) <= 0:
                return apology("Numbers of shares must be positive")
        except:
            return apology("Please enter a valid number of shares")

        # Store stock variables
        name = cost["name"]
        price = cost["price"]
        value = cost["price"]
        symbol = cost["symbol"]
        shares = int(request.form.get("shares"))
        total = shares
        totalval = price * shares
        cash = db.execute("SELECT * FROM portfolio WHERE id = :id AND symbol = :symbol", id=session['user_id'], symbol=symbol)
        time = datetime.now()

        # Check that user has the available stock to sell
        owned = 0
        for i in range(len(cash)):
            owned += cash[i]["shares"]
        if shares > owned:
            return apology("Insufficient stock for this purchase")

        # Sell stock by updating portfolio database and users cash amount
        else:
            db.execute("INSERT INTO portfolio (id, symbol, name, shares, price, value, time, total, totalval) VALUES(:id, :symbol, :name, :shares, :price, :value, :time, :total, :totalval);",
                       id=session['user_id'], symbol=symbol, name=name, shares=(-shares), price=price, value=value, time=time, total=total, totalval=totalval)
            db.execute("UPDATE users SET cash = cash + :cost WHERE id = :id", cost=(price * shares), id=session['user_id'])
            return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
