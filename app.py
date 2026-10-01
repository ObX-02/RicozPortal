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


def get_db():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is not configured."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


def initialize_database():
    connection = get_db()

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

    existing_user = connection.execute(
        "SELECT id FROM users WHERE email = %s",
        ("demo@ricozportal.com",)
    ).fetchone()

    if existing_user is None:
        password_hash = generate_password_hash("Demo@123")

        connection.execute("""
            INSERT INTO users
            (name, email, password, company, plan)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            "Demo Customer",
            "demo@ricozportal.com",
            password_hash,
            "Ricoz Solutions",
            "Professional"
        ))

    connection.commit()
    connection.close()


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = %s
            """,
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):
            session["user_id"] = user["id"]

            return redirect(url_for("dashboard"))

        return render_template(
            "index.html",
            error="Invalid email or password."
        )

    success = session.pop("success", None)

    return render_template(
        "index.html",
        success=success
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        company = request.form.get("company", "").strip()
        password = request.form.get("password", "")
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

        existing_user = connection.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            """,
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

        password_hash = generate_password_hash(password)

        connection.execute(
            """
            INSERT INTO users
            (name, email, password, company, plan)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                name,
                email,
                password_hash,
                company,
                "Free"
            )
        )

        connection.commit()
        connection.close()

        session["success"] = (
            "Account created successfully. "
            "You can now sign in."
        )

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        connection = get_db()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = %s
            """,
            (email,)
        ).fetchone()

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


@app.route("/reset-password", methods=["GET", "POST"])
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
        connection.close()

        session.pop("reset_user_id", None)

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


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    connection = get_db()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (session["user_id"],)
    ).fetchone()

    connection.close()

    if user is None:
        session.clear()

        return redirect(
            url_for("login")
        )

    return render_template(
        "dashboard.html",
        user=user
    )


@app.route("/logout")
def logout():
    session.clear()

    return redirect(
        url_for("login")
    )


# Initialize the PostgreSQL database
# when the application starts.
initialize_database()


if __name__ == "__main__":
    app.run(debug=True)