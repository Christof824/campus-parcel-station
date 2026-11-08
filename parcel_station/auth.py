"""Staff authentication, CSRF protection, and login routes."""

import hmac
import re
import secrets
from functools import wraps
from typing import Callable, Optional
from urllib.parse import urlsplit

import click
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from parcel_station.database import get_db
from parcel_station.errors import ValidationError


bp = Blueprint("auth", __name__)
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


def create_staff_user(
    username: str,
    display_name: str,
    password: str,
    role: str = "staff",
) -> int:
    """Create a staff account with a securely hashed password."""
    username = username.strip()
    display_name = " ".join(display_name.split())
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValidationError(
            "Username must be 3-32 characters using letters, numbers, _, . or -."
        )
    if not display_name:
        raise ValidationError("Display name cannot be empty.")
    if len(password) < 8:
        raise ValidationError("Password must contain at least 8 characters.")
    if role not in {"staff", "manager"}:
        raise ValidationError("Unknown staff role.")

    password_hash = generate_password_hash(
        password,
        method="pbkdf2:sha256:600000",
        salt_length=16,
    )
    connection = get_db()
    try:
        cursor = connection.execute(
            """
            INSERT INTO staff_users (
                username,
                password_hash,
                display_name,
                role
            )
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, display_name, role),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return cursor.lastrowid


def get_csrf_token() -> str:
    """Get or create a session-bound CSRF token."""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf() -> bool:
    """Validate the CSRF token submitted with a form."""
    expected = session.get("_csrf_token", "")
    submitted = request.form.get("csrf_token", "")
    return bool(expected and submitted and hmac.compare_digest(expected, submitted))


def _safe_next_url(target: Optional[str]) -> Optional[str]:
    """Reject external redirect targets."""
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/"):
        return None
    if target.startswith("//"):
        return None
    return target


def login_required(view: Callable):
    """Redirect unauthenticated visitors to the sign-in page."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            next_url = request.full_path.rstrip("?")
            return redirect(url_for("auth.login", next=next_url))
        return view(*args, **kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    """Load the active staff account for the current request."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return
    g.user = get_db().execute(
        """
        SELECT id, username, display_name, role
        FROM staff_users
        WHERE id = ? AND is_active = 1
        """,
        (user_id,),
    ).fetchone()
    if g.user is None:
        session.clear()


@bp.get("/login")
def login():
    """Render the staff sign-in form."""
    if g.user is not None:
        return redirect(url_for("dashboard"))
    return render_template(
        "login.html",
        error=None,
        next_url=_safe_next_url(request.args.get("next")) or "",
    )


@bp.post("/login")
def login_post():
    """Authenticate a staff member and start a new session."""
    if not validate_csrf():
        abort(400, description="Invalid or missing CSRF token.")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    next_url = _safe_next_url(request.form.get("next_url"))
    user = get_db().execute(
        """
        SELECT *
        FROM staff_users
        WHERE username = ? AND is_active = 1
        """,
        (username,),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Incorrect username or password.", "error")
        return (
            render_template(
                "login.html",
                error="Incorrect username or password.",
                next_url=next_url or "",
            ),
            401,
        )

    session.clear()
    session["user_id"] = user["id"]
    session.permanent = True
    return redirect(next_url or url_for("dashboard"))


@bp.post("/logout")
def logout():
    """End the current staff session."""
    if not validate_csrf():
        abort(400, description="Invalid or missing CSRF token.")
    session.clear()
    return redirect(url_for("auth.login"))


def init_app(app):
    """Register authentication routes, hooks, and staff CLI commands."""
    app.register_blueprint(bp)
    app.jinja_env.globals["csrf_token"] = get_csrf_token

    @app.cli.command("create-staff")
    @click.option("--username", prompt="Username")
    @click.option("--display-name", prompt="Display name")
    @click.password_option(confirmation_prompt=True)
    @click.option(
        "--role",
        type=click.Choice(["staff", "manager"]),
        default="staff",
        show_default=True,
    )
    def create_staff_command(username, display_name, password, role):
        """Create a staff login account."""
        try:
            user_id = create_staff_user(
                username, display_name, password, role=role
            )
        except ValidationError as error:
            raise click.ClickException(str(error)) from error
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise click.ClickException("That username already exists.") from error
            raise
        click.echo(f"Created staff user {username!r} with id {user_id}.")
