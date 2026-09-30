# RicozPortal

A modern customer portal MVP built with Flask, SQLite, HTML, and CSS.

RicozPortal provides a secure and user-friendly interface where customers can create an account, sign in, access their dashboard, and manage basic account access through a password recovery flow.

---

## Overview

RicozPortal is a Flask-based customer portal designed as an MVP for managing customer authentication and portal access.

The project currently focuses on the core authentication experience:

- User registration
- Secure password hashing
- User login
- Session-based authentication
- Customer dashboard
- Logout
- Forgot password
- Password reset
- SQLite database integration
- Responsive customer-facing interface

The application is structured so that additional customer portal features can be added later.

---

## Features

### Authentication

- User registration
- Email-based login
- Password confirmation during registration
- Password hashing using Werkzeug
- Session-based authentication
- Logout functionality

### Password Recovery

- Forgot password page
- Account email verification
- Password reset page
- New password validation
- Secure password hashing after reset

> Note: The current password recovery flow is an MVP implementation using a temporary Flask session. Email-based password reset tokens can be added in a future version.

### Customer Dashboard

- Personalized dashboard
- Customer name display
- Company information
- Current plan information
- Protected dashboard route

### User Interface

- Modern responsive design
- Dedicated login experience
- Registration interface
- Password recovery interface
- Password reset interface
- Customer dashboard
- Mobile-friendly layout

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Database |
| HTML5 | Page structure |
| CSS3 | Styling and responsive design |
| Jinja2 | Dynamic HTML templates |
| Werkzeug | Password hashing and security utilities |

---

## Project Structure

```text
RicozPortal/
│
├── app.py
├── README.md
├── .gitignore
│
├── templates/
│   ├── index.html
│   ├── register.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   └── dashboard.html
│
└── static/
    └── css/
        ├── style.css
        ├── register.css
        └── dashboard.css
