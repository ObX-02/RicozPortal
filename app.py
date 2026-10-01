from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
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
# DATABASE
# =========================================================

def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


def initialize_database():

    with get_db() as conn:

        with conn.cursor() as cur:

            # -------------------------------------------------
            # USERS
            # -------------------------------------------------

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    company VARCHAR(150),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # -------------------------------------------------
            # SUPPORT TICKETS
            # -------------------------------------------------

            cur.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    subject VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    status VARCHAR(50) DEFAULT 'Open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # -------------------------------------------------
            # INVOICES
            # -------------------------------------------------

            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    invoice_number VARCHAR(100) NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'Paid',
                    invoice_date DATE DEFAULT CURRENT_DATE
                )
            """)

            # -------------------------------------------------
            # NOTIFICATIONS
            # -------------------------------------------------

            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    type VARCHAR(50) DEFAULT 'info',
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # -------------------------------------------------
            # DEMO ACCOUNT
            # -------------------------------------------------

            cur.execute(
                "SELECT id FROM users WHERE email = %s",
                ("demo@ricoz.com",)
            )

            demo_user = cur.fetchone()

            if not demo_user:

                password_hash = generate_password_hash(
                    "Demo@12345"
                )

                cur.execute(
                    """
                    INSERT INTO users
                    (name, email, password_hash, company)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        "Ricoz Demo User",
                        "demo@ricoz.com",
                        password_hash,
                        "Ricoz",
                    )
                )

                demo_user = cur.fetchone()

                demo_user_id = demo_user["id"]

                cur.execute(
                    """
                    INSERT INTO invoices
                    (user_id, invoice_number, amount, status)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        demo_user_id,
                        "RICOZ-001",
                        99.00,
                        "Paid",
                    )
                )

                cur.execute(
                    """
                    INSERT INTO notifications
                    (user_id, title, message, type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        demo_user_id,
                        "Welcome to Ricoz",
                        "Your Ricoz customer portal is ready.",
                        "success",
                    )
                )

        conn.commit()


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user():

    user_id = session.get("user_id")

    if not user_id:
        return None

    with get_db() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT id, name, email, company, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            return cur.fetchone()


# =========================================================
# HOME / LANDING
# =========================================================

@app.route("/")
def home():

    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    return render_template("landing.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "error"
            )

            return redirect(url_for("login"))

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE email = %s
                    """,
                    (email,)
                )

                user = cur.fetchone()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session["user_id"] = user["id"]

            flash(
                "Welcome back!",
                "success"
            )

            return redirect(url_for("dashboard"))

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template("index.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        company = request.form.get("company", "").strip()

        if not name or not email or not password:

            flash(
                "Please complete all required fields.",
                "error"
            )

            return redirect(url_for("register"))

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

            return redirect(url_for("register"))

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE email = %s
                    """,
                    (email,)
                )

                existing_user = cur.fetchone()

                if existing_user:

                    flash(
                        "An account with this email already exists.",
                        "error"
                    )

                    return redirect(url_for("register"))

                password_hash = generate_password_hash(
                    password
                )

                cur.execute(
                    """
                    INSERT INTO users
                    (name, email, password_hash, company)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        name,
                        email,
                        password_hash,
                        company,
                    )
                )

                user = cur.fetchone()

                user_id = user["id"]

                cur.execute(
                    """
                    INSERT INTO notifications
                    (user_id, title, message, type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        "Welcome to Ricoz",
                        "Your customer portal account has been created successfully.",
                        "success",
                    )
                )

            conn.commit()

        session["user_id"] = user_id

        flash(
            "Account created successfully!",
            "success"
        )

        return redirect(url_for("dashboard"))

    return render_template("register.html")


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        if not email:

            flash(
                "Please enter your email address.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE email = %s
                    """,
                    (email,)
                )

                user = cur.fetchone()

        if user:

            session["reset_email"] = email

            return redirect(
                url_for("reset_password")
            )

        flash(
            "If an account exists with this email, you can continue with password reset.",
            "info"
        )

    return render_template("forgot_password.html")


# =========================================================
# RESET PASSWORD
# =========================================================

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    email = session.get("reset_email")

    if not email:
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

            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

            return redirect(
                url_for("reset_password")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("reset_password")
            )

        password_hash = generate_password_hash(
            password
        )

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s
                    WHERE email = %s
                    """,
                    (
                        password_hash,
                        email,
                    )
                )

            conn.commit()

        session.pop("reset_email", None)

        flash(
            "Password updated successfully. Please sign in.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("reset_password.html")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    with get_db() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM support_tickets
                WHERE user_id = %s
                AND status = 'Open'
                """,
                (user["id"],)
            )

            open_tickets = cur.fetchone()["count"]

            cur.execute(
                """
                SELECT title, message, type, created_at
                FROM notifications
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user["id"],)
            )

            recent_notifications = cur.fetchall()

    return render_template(
        "dashboard.html",
        user=user,
        open_tickets=open_tickets,
        recent_notifications=recent_notifications,
    )


# =========================================================
# ACCOUNT
# =========================================================

@app.route("/account", methods=["GET", "POST"])
def account():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

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

            flash(
                "Name cannot be empty.",
                "error"
            )

            return redirect(url_for("account"))

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    UPDATE users
                    SET name = %s,
                        company = %s
                    WHERE id = %s
                    """,
                    (
                        name,
                        company,
                        user["id"],
                    )
                )

            conn.commit()

        flash(
            "Account information updated successfully.",
            "success"
        )

        return redirect(url_for("account"))

    user = get_current_user()

    return render_template(
        "account.html",
        user=user
    )


# =========================================================
# SUBSCRIPTION
# =========================================================

@app.route("/subscription")
def subscription():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

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

    if not user:
        return redirect(url_for("login"))

    with get_db() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    invoice_number,
                    amount,
                    status,
                    invoice_date
                FROM invoices
                WHERE user_id = %s
                ORDER BY invoice_date DESC
                """,
                (user["id"],)
            )

            invoices = cur.fetchall()

    return render_template(
        "billing.html",
        user=user,
        invoices=invoices
    )


# =========================================================
# SUPPORT
# =========================================================

@app.route("/support", methods=["GET", "POST"])
def support():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

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

            flash(
                "Please enter both subject and message.",
                "error"
            )

            return redirect(url_for("support"))

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO support_tickets
                    (user_id, subject, message)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        user["id"],
                        subject,
                        message,
                    )
                )

                cur.execute(
                    """
                    INSERT INTO notifications
                    (user_id, title, message, type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        user["id"],
                        "Support Request Created",
                        "Your support request has been submitted successfully.",
                        "success",
                    )
                )

            conn.commit()

        flash(
            "Your support request has been submitted.",
            "success"
        )

        return redirect(url_for("support"))

    with get_db() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    subject,
                    message,
                    status,
                    created_at
                FROM support_tickets
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user["id"],)
            )

            tickets = cur.fetchall()

    return render_template(
        "support.html",
        user=user,
        tickets=tickets
    )


# =========================================================
# SETTINGS
# =========================================================

@app.route("/settings", methods=["GET", "POST"])
def settings():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

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

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT password_hash
                    FROM users
                    WHERE id = %s
                    """,
                    (user["id"],)
                )

                account_data = cur.fetchone()

        if not check_password_hash(
            account_data["password_hash"],
            current_password
        ):

            flash(
                "Current password is incorrect.",
                "error"
            )

            return redirect(url_for("settings"))

        if len(new_password) < 8:

            flash(
                "New password must contain at least 8 characters.",
                "error"
            )

            return redirect(url_for("settings"))

        if new_password != confirm_password:

            flash(
                "New passwords do not match.",
                "error"
            )

            return redirect(url_for("settings"))

        new_password_hash = generate_password_hash(
            new_password
        )

        with get_db() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s
                    WHERE id = %s
                    """,
                    (
                        new_password_hash,
                        user["id"],
                    )
                )

            conn.commit()

        flash(
            "Password changed successfully.",
            "success"
        )

        return redirect(url_for("settings"))

    return render_template(
        "settings.html",
        user=user
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@app.route("/notifications")
def notifications():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    with get_db() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    title,
                    message,
                    type,
                    is_read,
                    created_at
                FROM notifications
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user["id"],)
            )

            notifications_list = cur.fetchall()

            cur.execute(
                """
                UPDATE notifications
                SET is_read = TRUE
                WHERE user_id = %s
                """,
                (user["id"],)
            )

        conn.commit()

    return render_template(
        "notifications.html",
        user=user,
        notifications=notifications_list
    )


# =========================================================
# CHATBOT
# =========================================================

@app.route("/chatbot")
def chatbot():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    return render_template(
        "chatbot.html",
        user=user
    )


# =========================================================
# PRIVACY
# =========================================================

@app.route("/privacy")
def privacy():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    return render_template(
        "privacy.html",
        user=user
    )


# =========================================================
# TERMS
# =========================================================

@app.route("/terms")
def terms():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    return render_template(
        "terms.html",
        user=user
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

initialize_database()


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )