from flask import Flask, render_template, request, redirect, url_for, session
import os
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)


app.secret_key = os.environ.get(
    "SECRET_KEY",
    "ricozportal-development-secret"
)


DATABASE_URL = os.environ.get("DATABASE_URL")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is not configured."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_database():

    connection = get_db()

    try:

        # -------------------------
        # USERS
        # -------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                company TEXT,
                plan TEXT DEFAULT 'Free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # -------------------------
        # SUPPORT TICKETS
        # -------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'Open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # -------------------------
        # BILLING INVOICES
        # -------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                invoice_number TEXT UNIQUE NOT NULL,
                amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'Pending',
                invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # -------------------------
        # NOTIFICATIONS
        # -------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # -------------------------
        # DEMO ACCOUNT
        # -------------------------

        existing_user = connection.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            """,
            ("demo@ricozportal.com",)
        ).fetchone()


        if existing_user is None:

            password_hash = generate_password_hash(
                "Demo@123"
            )

            demo_user = connection.execute(
                """
                INSERT INTO users
                (name, email, password, company, plan)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    "Demo Customer",
                    "demo@ricozportal.com",
                    password_hash,
                    "Ricoz Solutions",
                    "Professional"
                )
            ).fetchone()


            demo_user_id = demo_user["id"]


            connection.execute(
                """
                INSERT INTO notifications
                (user_id, title, message)
                VALUES (%s, %s, %s)
                """,
                (
                    demo_user_id,
                    "Welcome to RicozPortal",
                    "Your customer portal account is ready."
                )
            )


        connection.commit()

    finally:

        connection.close()


# =========================================================
# CURRENT USER HELPER
# =========================================================

def get_current_user():

    if "user_id" not in session:
        return None


    connection = get_db()

    try:

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE id = %s
            """,
            (session["user_id"],)
        ).fetchone()

        return user

    finally:

        connection.close()


# =========================================================
# LANDING PAGE
# =========================================================

@app.route("/")
def landing():

    return render_template(
        "landing.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
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

        try:

            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                """,
                (email,)
            ).fetchone()

        finally:

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


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
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


        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all required fields.",
                name=name,
                email=email,
                company=company
            )


        if password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match.",
                name=name,
                email=email,
                company=company
            )


        if len(password) < 8:

            return render_template(
                "register.html",
                error="Password must be at least 8 characters long.",
                name=name,
                email=email,
                company=company
            )


        connection = get_db()

        try:

            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                """,
                (email,)
            ).fetchone()


            if existing_user:

                return render_template(
                    "register.html",
                    error="An account with this email already exists.",
                    name=name,
                    email=email,
                    company=company
                )


            password_hash = generate_password_hash(
                password
            )


            new_user = connection.execute(
                """
                INSERT INTO users
                (name, email, password, company, plan)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    name,
                    email,
                    password_hash,
                    company,
                    "Free"
                )
            ).fetchone()


            new_user_id = new_user["id"]


            connection.execute(
                """
                INSERT INTO notifications
                (user_id, title, message)
                VALUES (%s, %s, %s)
                """,
                (
                    new_user_id,
                    "Welcome to RicozPortal",
                    "Your account has been created successfully."
                )
            )


            connection.commit()

        finally:

            connection.close()


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


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        connection = get_db()

        try:

            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                """,
                (email,)
            ).fetchone()

        finally:

            connection.close()


        if user is None:

            return render_template(
                "forgot_password.html",
                error="No account was found with this email."
            )


        session["reset_user_id"] = user["id"]


        return redirect(
            url_for("reset_password")
        )


    return render_template(
        "forgot_password.html"
    )


# =========================================================
# RESET PASSWORD
# =========================================================

@app.route(
    "/reset-password",
    methods=["GET", "POST"]
)
def reset_password():

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


        if len(password) < 8:

            return render_template(
                "reset_password.html",
                error="Password must be at least 8 characters long."
            )


        if password != confirm_password:

            return render_template(
                "reset_password.html",
                error="Passwords do not match."
            )


        password_hash = generate_password_hash(
            password
        )


        connection = get_db()

        try:

            connection.execute(
                """
                UPDATE users
                SET password = %s
                WHERE id = %s
                """,
                (
                    password_hash,
                    session["reset_user_id"]
                )
            )


            connection.commit()

        finally:

            connection.close()


        session.pop(
            "reset_user_id",
            None
        )


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


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    user = get_current_user()


    if user is None:

        return redirect(
            url_for("login")
        )


    connection = get_db()

    try:

        ticket_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM support_tickets
            WHERE user_id = %s
            AND status = 'Open'
            """,
            (user["id"],)
        ).fetchone()["count"]


        notifications = connection.execute(
            """
            SELECT *
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user["id"],)
        ).fetchall()

    finally:

        connection.close()


    return render_template(
        "dashboard.html",
        user=user,
        ticket_count=ticket_count,
        notifications=notifications
    )


# =========================================================
# MY ACCOUNT
# =========================================================

@app.route(
    "/account",
    methods=["GET", "POST"]
)
def account():

    user = get_current_user()


    if user is None:

        return redirect(
            url_for("login")
        )


    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        company = request.form.get(
            "company",
            ""
        ).strip()


        if not name:

            return render_template(
                "account.html",
                user=user,
                error="Name cannot be empty."
            )


        connection = get_db()

        try:

            connection.execute(
                """
                UPDATE users
                SET name = %s,
                    company = %s
                WHERE id = %s
                """,
                (
                    name,
                    company,
                    user["id"]
                )
            )


            connection.commit()

        finally:

            connection.close()


        session["success"] = (
            "Your account information has been updated."
        )


        return redirect(
            url_for("account")
        )


    success = session.pop(
        "success",
        None
    )


    return render_template(
        "account.html",
        user=user,
        success=success
    )


# =========================================================
# SUBSCRIPTION
# =========================================================

@app.route("/subscription")
def subscription():

    user = get_current_user()


    if user is None:

        return redirect(
            url_for("login")
        )


    return render_template(
        "subscription.html",
        user=user
    )


# =========================================================
# BILLING
# =========================================================

@app.route("/billing")
def billing():

    user = get_current_user()


    if user is None:

        return redirect(
            url_for("login")
        )


    connection = get_db()

    try:

        invoices = connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE user_id = %s
            ORDER BY invoice_date DESC
            """,
            (user["id"],)
        ).fetchall()

    finally:

        connection.close()


    return render_template(
        "billing.html",
        user=user,
        invoices=invoices
    )


# =========================================================
# SUPPORT
# =========================================================

@app.route(
    "/support",
    methods=["GET", "POST"]
)
def support():

    user = get_current_user()


    if user is None:

        return redirect(
            url_for("login")
        )


    connection = get_db()

    try:

        if request.method == "POST":

            subject = request.form.get(
                "subject",
                ""
            ).strip()

            message = request.form.get(
                "message",
                ""
            ).strip()


            if not subject or not message:

                tickets = connection.execute(
                    """
                    SELECT *
                    FROM support_tickets
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user["id"],)
                ).fetchall()


                return render_template(
                    "support.html",
                    user=user,
                    tickets=tickets,
                    error="Please enter both a subject and message."
                )


            connection.execute(
                """
                INSERT INTO support_tickets
                (user_id, subject, message)
                VALUES (%s, %s, %s)
                """,
                (
                    user["id"],
                    subject,
                    message
                )
            )


            connection.execute(
                """
                INSERT INTO notifications
                (user_id, title, message)
                VALUES (%s, %s, %s)
                """,
                (
                    user["id"],
                    "Support ticket created",
                    f"Your support request '{subject}' has been received."
                )
            )


            connection.commit()


            session["success"] = (
                "Your support ticket has been submitted."
            )


            return redirect(
                url_for("support")
            )


        tickets = connection.execute(
            """
            SELECT *
            FROM support_tickets
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user["id"],)
        ).fetchall()


    finally:

        connection.close()


    success = session.pop(
        "success",
        None
    )


    return render_template(
        "support.html",
        user=user,
        tickets=tickets,
        success=success
    )


# =========================================================
# SETTINGS
# =========================================================

@app.route(
    "/settings",
    methods=["GET", "POST"]
)
def settings():

    user = get_current_user()


    if user is None:

        return redirect(
            url_for("login")
        )


    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        if not check_password_hash(
            user["password"],
            current_password
        ):

            return render_template(
                "settings.html",
                user=user,
                error="Current password is incorrect."
            )


        if len(new_password) < 8:

            return render_template(
                "settings.html",
                user=user,
                error="New password must be at least 8 characters long."
            )


        if new_password != confirm_password:

            return render_template(
                "settings.html",
                user=user,
                error="New passwords do not match."
            )


        password_hash = generate_password_hash(
            new_password
        )


        connection = get_db()

        try:

            connection.execute(
                """
                UPDATE users
                SET password = %s
                WHERE id = %s
                """,
                (
                    password_hash,
                    user["id"]
                )
            )


            connection.commit()

        finally:

            connection.close()


        session["success"] = (
            "Your password has been updated successfully."
        )


        return redirect(
            url_for("settings")
        )


    success = session.pop(
        "success",
        None
    )


    return render_template(
        "settings.html",
        user=user,
        success=success
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@app.route("/notifications")
def notifications():

    user = get_current_user()


    if user is None:

        return redirect(
            url_for("login")
        )


    connection = get_db()

    try:

        user_notifications = connection.execute(
            """
            SELECT *
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user["id"],)
        ).fetchall()


        connection.execute(
            """
            UPDATE notifications
            SET is_read = TRUE
            WHERE user_id = %s
            """,
            (user["id"],)
        )


        connection.commit()

    finally:

        connection.close()


    return render_template(
        "notifications.html",
        user=user,
        notifications=user_notifications
    )


# =========================================================
# PRIVACY POLICY
# =========================================================

@app.route("/privacy")
def privacy():

    return render_template(
        "privacy.html"
    )


# =========================================================
# TERMS OF SERVICE
# =========================================================

@app.route("/terms")
def terms():

    return render_template(
        "terms.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

initialize_database()


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )