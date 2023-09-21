import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    """ getting user id and username """
    user_id = session.get("user_id")

    if user_id is None:
        return render_template("register.html")

    username = db.execute("SELECT username FROM users WHERE id = ?", user_id)
    username = username[0]["username"].capitalize()

    consolidated = db.execute(
        "SELECT * FROM consolidated WHERE users_id = ? ORDER BY stock", user_id
    )

    consolidated_wallet = []
    total_stocks_value = 0

    for row in consolidated:
        stock_info = lookup(row["stock"])

        price = float(stock_info["price"])

        total = int(row["shares"]) * price

        total_stocks_value += total

        consolidated_wallet.append(
            {
                "stock": row["stock"],
                "shares": row["shares"],
                "price": price,
                "total": total,
            }
        )

    """ Cash Balance """
    cash = db.execute("Select cash FROM users WHERE id = ?", user_id)
    user_cash = cash[0]["cash"]

    cash_balance = user_cash + total_stocks_value

    """ Wallet profit/loss """
    profit_loss = cash_balance - 10000

    return render_template(
        "index.html",
        name=username,
        purchases=consolidated_wallet,
        total_stocks_value=total_stocks_value,
        cash=user_cash,
        cash_balance=cash_balance,
        profit_loss=profit_loss,
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    else:
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        """ stock symbol validations """
        if not symbol:
            return apology("Must provide symbol.")

        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("Must provide a positive integer number of shares.")

        quote = lookup(symbol)
        if quote is None:
            return apology("Symbol not found.")

        """ searching stock infos """
        price = quote["price"]
        total_cost = int(shares) * price

        date = datetime.date.today()

        """ get user cash """
        user_id = session.get("user_id")

        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        user_cash = user_cash[0]["cash"]

        """ purchase validations """
        if user_cash < total_cost:
            return apology("Insufficient fund")

        """ update user cash """
        cash_net = user_cash - total_cost

        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_net, user_id)

        """ update purchase """
        db.execute(
            "INSERT INTO purchase (users_id, stock, shares, price, total_purchase, date) VALUES (?, ?, ?, ?, ?, ?)",
            user_id,
            symbol,
            shares,
            price,
            total_cost,
            date,
        )

        """ update consolidated """

        consolidated = db.execute(
            "SELECT * FROM consolidated WHERE users_id = ? AND stock = ?",
            user_id,
            symbol,
        )

        if consolidated:
            if consolidated[0]["shares"] is None:
                db.execute(
                    "INSERT INTO consolidated (users_id, stock, shares) VALUES (?, ?, ?)",
                    user_id,
                    symbol,
                    shares,
                )
            new_shares = consolidated[0]["shares"] + int(shares)
            db.execute(
                "UPDATE consolidated SET shares = ? WHERE users_id = ? AND stock = ?",
                new_shares,
                user_id,
                symbol,
            )

        else:
            db.execute(
                "INSERT INTO consolidated (users_id, stock, shares) VALUES (?, ?, ?)",
                user_id,
                symbol,
                shares,
            )

        flash(f"Bought {shares} shares of {symbol} for {usd(total_cost)}!")
        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session.get("user_id")

    purchases = db.execute(
        "SELECT stock, shares, price, total_purchase, date FROM purchase WHERE users_id = ? ORDER BY date;",
        user_id,
    )
    sales = db.execute(
        "SELECT stock, shares, price, total_sell, date FROM sell WHERE users_id = ? ORDER BY date;",
        user_id,
    )

    history = []
    total_history = 0

    for row in purchases:
        total_history += row["total_purchase"]
        price_formatted = usd(row["price"])
        total_formatted = usd(row["total_purchase"])
        history.append(
            {
                "date": row["date"],
                "stock": row["stock"],
                "shares": row["shares"],
                "price": price_formatted,
                "total": total_formatted,
            }
        )

    for row in sales:
        total_history += row["total_sell"]
        price_formatted = usd(row["price"])
        total_formatted = usd(row["total_sell"])
        history.append(
            {
                "date": row["date"],
                "stock": row["stock"],
                "shares": row["shares"],
                "price": row["price"],
                "total": total_formatted,
            }
        )

    total_history_formatted = usd(total_history)

    return render_template("history.html", history=history)


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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
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
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("Must Give Symbol.")

        result = lookup(symbol.upper())

        if result == None:
            return apology("Symbol Does Not Exist in NASDAQ.")

        name = result["name"]
        price = result["price"]
        symbol = result["symbol"]

        return render_template("quoted.html", name=name, price=price, symbol=symbol)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("Must Give Username")

        if not password:
            return apology("Must Give Password")

        number = 0
        symbol = 0
        capitalized = 0

        for char in password:
            if char.isnumeric():
                number += 1
            if char.isupper():
                capitalized += 1
            elif not char.isalnum():
                symbol += 1

        if number <= 0 or symbol <= 0 or capitalized <= 0:
            return apology(
                "Password must have at least one capitalized letter, symbol and number."
            )

        if not confirmation:
            return apology("Must Give Confirmation")

        if password != confirmation:
            return apology("Passwords Do Not Match")

        hash = generate_password_hash(password)

        try:
            new_user = db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?);", username, hash
            )
        except:
            return apology("Username alredy exists")

        session["user_id"] = new_user

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    """ users current stocks owned """
    user_id = session.get("user_id")
    stocks_owned = db.execute(
        "SELECT stock, shares FROM consolidated WHERE users_id = ?", user_id
    )

    if request.method == "GET":
        return render_template("sell.html", stocks_owned=stocks_owned)

    else:
        """get inputs"""
        sell_stock = request.form.get("symbol")
        sell_shares = request.form.get("shares")

        """ stock owned validations """
        if sell_stock == "default":
            return apology("Please provide a valid stock symbol.")

        stock_available = 0

        for row in stocks_owned:
            if sell_stock == row["stock"]:
                stock_available += 1
        if stock_available != 1:
            return apology("Please provide a valid stock symbol.")

        """ shares owned validations """
        if not sell_shares:
            return apology("Please provide a valid share amount.")

        elif sell_shares.isnumeric() == False:
            return apology("Please provide a valid NUMBER amount.")

        sell_shares_int = int(sell_shares)

        if sell_shares_int <= 0:
            return apology("Please provide a valid share amount.")

        stock_found = False
        for row in stocks_owned:
            if row["stock"] == sell_stock:
                stock_found = True
                shares_owned = row["shares"]
                break

        if not stock_found:
            return apology("Stock not found in your wallet.")

        if sell_shares_int > shares_owned:
            return apology("You don't have enough shares to sell that amount.")

        """ get user cash """
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        user_cash = cash[0]["cash"]

        """ stock info """
        date = datetime.date.today()

        if lookup(sell_stock) is None:
            return apology("Please provide a valid stock symbol.")

        stock_info = lookup(sell_stock)

        name = stock_info["name"]
        price = float(stock_info["price"])

        """ consolidated update """
        consolidated = db.execute(
            "SELECT shares FROM consolidated WHERE users_id = ? AND stock = ?",
            user_id,
            sell_stock,
        )

        if consolidated:
            new_shares = consolidated[0]["shares"] - sell_shares_int
            if new_shares == 0:
                db.execute(
                    "DELETE FROM consolidated WHERE stock = ? AND users_id = ?;",
                    name,
                    user_id,
                )
            else:
                db.execute(
                    "UPDATE consolidated SET shares = ? WHERE users_id = ? AND stock = ?",
                    new_shares,
                    user_id,
                    sell_stock,
                )
        else:
            db.execute(
                "INSERT INTO consolidated (users_id, stock, shares) VALUES (?, ?, ?)",
                user_id,
                sell_stock,
                sell_shares,
            )

        """ cash update """

        sale = sell_shares_int * price
        sale_adjust = -sale
        cash_net = user_cash + sale

        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_net, user_id)

        """ sell update """
        db.execute(
            "INSERT INTO sell (users_id, stock, shares, price, total_sell, date) VALUES (?, ?, ?, ?, ?, ?)",
            user_id,
            sell_stock,
            sell_shares,
            price,
            sale_adjust,
            date,
        )

        flash(f"Sold {sell_shares} shares of {sell_stock} for {usd(sale)}!")

        return redirect("/")
