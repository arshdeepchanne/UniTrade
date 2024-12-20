import mysql.connector
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required


# Connect database
db = mysql.connector.connect(
  host="localhost",
  user="root",
  password="rootpassword",
  database="ezymarket",
  buffered=True
)

# Create cursor
cursor = db.cursor(dictionary=True)
db.commit()

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


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
@login_required
def index():
    """Show all products"""

    # Query the database for products
    cursor.execute("SELECT * from products where category='clothing'")

    clothing = cursor.fetchmany(4)

    cursor.execute("SELECT * from products where category='electronics'")

    electronics = cursor.fetchmany(4)
    
    cursor.execute("SELECT * from products where category='accessories'")

    accessories = cursor.fetchmany(4)

    cursor.execute("SELECT * from products where category='stationary'")

    stationary = cursor.fetchmany(4)

    return render_template("index.html", clothing=clothing, electronics=electronics, accessories=accessories, stationary=stationary)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("uid"):
            return apology("must provide uid", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        cursor.execute("SELECT * FROM users WHERE uid = (%s)", (request.form.get("uid"), ))
        rows = cursor.fetchall()
        cursor.execute("SELECT * FROM users")

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Register if you haven't already!", category="error")
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        db.commit()

        flash("Login Successful!")
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        # Get the username, password and confirmation password from the HTML form.
        name = request.form.get("name")
        uid = request.form.get("uid")
        password = request.form.get("password")
        confirm_pass = request.form.get("confirm_password")

        # Query the database to get the list of all users.
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        # Check if name was submitted.
        if not name or name == ' ':
            return apology("Please enter your name")
        # Check if the uid was submitted.
        if not uid or uid == ' ':
            return apology("Username cannot be blank")

        # Check if the username already exists.
        for user in users:
            if uid == user["uid"]:
                return apology("User already exists")

        # Ensure that passwords were submitted.
        if not password or not confirm_pass:
            return apology("Password cannot be blank")

        # Ensure that the password and confirmation password match.
        elif password != confirm_pass:
            return apology("Passwords do not match")

        # Register the user.
        cursor.execute("INSERT INTO users (uid, name, hash) VALUES(%s, %s, %s)", (uid, name, generate_password_hash(password)))

        # Query the database to get the id of the user.
        cursor.execute("SELECT id FROM users WHERE uid=(%s)", (uid, ))
        user = cursor.fetchone()
        # Remember the id of the logged in user.
        session["user_id"] = user["id"]

        db.commit()
        
        flash("Registration Successful!")
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/electronics")
@login_required
def electronics():
    # Query the database for products
    cursor.execute("SELECT * from products where category='electronics'")

    electronics = cursor.fetchall()

    return render_template("electronics.html", electronics=electronics)


@app.route("/clothing")
@login_required
def clothing():

    cursor.execute("SELECT * from products where category='clothing'")

    clothing = cursor.fetchall()

    return render_template("clothing.html", clothing=clothing)


@app.route("/accessories")
@login_required
def accessories():

    cursor.execute("SELECT * from products where category='accessories'")

    accessories = cursor.fetchall()

    return render_template("accessories.html", accessories=accessories)


@app.route("/stationary")
@login_required
def stationary():

    cursor.execute("SELECT * from products where category='stationary'")

    stationary = cursor.fetchall()

    return render_template("stationary.html", stationary=stationary)


@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():

    if request.method == "POST":
        product_id = request.form.get("form_id")

        cursor.execute("SELECT * FROM cart WHERE user_id=(%s) and product_id=(%s)", (session["user_id"], product_id))
        prod_exist = cursor.fetchall()

        if prod_exist:
            return apology("Item already in cart")

        cursor.execute("INSERT INTO cart (user_id, product_id) VALUES(%s, %s)", (session["user_id"], product_id))
        db.commit()
        return redirect("/")

    else:
        cursor.execute("SELECT product_id FROM cart WHERE user_id=(%s)", (session["user_id"],))
        products = cursor.fetchall()
        product_ids = []
        for product in products:
            product_ids.append(product["product_id"])

        if not product_ids:
            return apology("Cart empty!")
        
        if len(product_ids) == 1:
            cursor.execute("SELECT * FROM products where product_id = (%s)", (product_ids[0],))
        else:
            cursor.execute("SELECT * FROM products where product_id in {}".format(tuple(product_ids)))

        cart_items = cursor.fetchall()

        return render_template("cart.html", cart=cart_items)


@app.route("/ordered", methods=["GET", "POST"])
@login_required
def ordered():
    if request.method == "POST":
        product_id = request.form.get("form_id")

        cursor.execute(
            """select users.id, users.name as uname, users.uid, 
                    products.product_id, products.name as pname, products.cost
                        from users, products 
                            where products.product_id = (%s) 
                                and users.id = products.seller_id""", 
                                (product_id,)
        )

        order_info = cursor.fetchall()

        cursor.execute("INSERT INTO transactions (buyer_id, seller_id, product_id) VALUES(%s, %s, %s)", 
                       (session["user_id"], order_info[0]["id"], order_info[0]["product_id"]))
        db.commit()

        return render_template("ordered.html", order_info=order_info[0])
    
    else:
        return apology("Invalid request")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
