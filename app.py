from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = "ricozportal-development-secret"

DATABASE = "ricozportal.db"


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def initialize_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            company TEXT,
            plan TEXT
        )
    """)

    # Create demo account if it does not exist
    existing_user = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        ("demo@ricozportal.com",)
    ).fetchone()

    if existing_user is None:

        password_hash = generate_password_hash("Demo@123")

        connection.execute("""
            INSERT INTO users
            (name, email, password, company, plan)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "Demo Customer",
            "demo@ricozportal.com",
            password_hash,
            "Ricoz Solutions",
            "Professional"
        ))

    connection.commit()

    connection.close()


# ==========================================
# LOGIN
# ==========================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            return redirect(
                url_for("dashboard")
            )

        return render_template(
            "index.html",
            error="Invalid email or password."
        )


    success = session.pop(
        "success",
        None
    )

    return render_template(
        "index.html",
        success=success
    )


# ==========================================
# REGISTER / CREATE ACCOUNT
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        company = request.form.get(
            "company",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        # Validate required fields

        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all required fields.",
                name=name,
                email=email,
                company=company
            )


        # Check password confirmation

        if password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match.",
                name=name,
                email=email,
                company=company
            )


        # Password length

        if len(password) < 8:

            return render_template(
                "register.html",
                error="Password must be at least 8 characters long.",
                name=name,
                email=email,
                company=company
            )


        connection = get_db()


        # Check existing email

        existing_user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()


        if existing_user:

            connection.close()

            return render_template(
                "register.html",
                error="An account with this email already exists.",
                name=name,
                email=email,
                company=company
            )


        # Hash password

        password_hash = generate_password_hash(
            password
        )


        # Create user

        connection.execute("""
            INSERT INTO users
            (name, email, password, company, plan)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            email,
            password_hash,
            company,
            "Free"
        ))


        connection.commit()

        connection.close()


        # Registration success

        session["success"] = (
            "Account created successfully. "
            "You can now sign in."
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# ==========================================
# FORGOT PASSWORD
# ==========================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()


        if user is None:

            return render_template(
                "forgot_password.html",
                error="No account was found with this email."
            )


        # Save user ID temporarily for password reset

        session["reset_user_id"] = user["id"]

        return redirect(
            url_for("reset_password")
        )


    return render_template(
        "forgot_password.html"
    )


# ==========================================
# RESET PASSWORD
# ==========================================

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    # Make sure user started the reset process

    if "reset_user_id" not in session:

        return redirect(
            url_for("forgot_password")
        )


    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        # Password length

        if len(password) < 8:

            return render_template(
                "reset_password.html",
                error="Password must be at least 8 characters long."
            )


        # Password confirmation

        if password != confirm_password:

            return render_template(
                "reset_password.html",
                error="Passwords do not match."
            )


        # Hash new password

        password_hash = generate_password_hash(
            password
        )


        connection = get_db()

        connection.execute(
            """
            UPDATE users
            SET password = ?
            WHERE id = ?
            """,
            (
                password_hash,
                session["reset_user_id"]
            )
        )

        connection.commit()

        connection.close()


        # Remove reset session

        session.pop(
            "reset_user_id",
            None
        )


        # Success message

        session["success"] = (
            "Password reset successfully. "
            "You can now sign in."
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "reset_password.html"
    )


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    connection = get_db()

    user = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    connection.close()


    return render_template(
        "dashboard.html",
        user=user
    )


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    initialize_database()

    app.run(debug=True)