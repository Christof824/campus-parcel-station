"""Flask application factory and foundation routes."""

from datetime import datetime, timezone
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from parcel_station import auth
from parcel_station import database
from parcel_station.errors import ParcelStationError
from parcel_station.services import parcels
from parcel_station.services import reports


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent


def create_app(config_object=None, config_overrides=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=str(PROJECT_DIR / "templates"),
        static_folder=str(PROJECT_DIR / "static"),
    )

    if config_object is not None:
        app.config.from_object(config_object)
    if config_overrides:
        app.config.update(config_overrides)

    instance_dir = Path(app.config.get("INSTANCE_DIR", PROJECT_DIR / "instance"))
    instance_dir.mkdir(parents=True, exist_ok=True)

    database.init_app(app)
    auth.init_app(app)

    @app.after_request
    def add_security_headers(response):
        """Add conservative browser security headers."""
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "script-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'",
        )
        if g.get("user") is not None:
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    def render_error_page(code, title, message):
        """Render a consistent public error page."""
        return (
            render_template(
                "error.html",
                app_name=app.config["APP_NAME"],
                version=app.config["APP_VERSION"],
                error_code=code,
                error_title=title,
                error_message=message,
            ),
            code,
        )

    @app.errorhandler(400)
    def bad_request(_error):
        return render_error_page(
            400,
            "That request could not be completed.",
            "The form may have expired. Please return to the previous page and try again.",
        )

    @app.errorhandler(404)
    def page_not_found(_error):
        return render_error_page(
            404,
            "This page does not exist.",
            "Check the address or return to the staff workspace.",
        )

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error("Unhandled application error: %s", error)
        return render_error_page(
            500,
            "Something went wrong.",
            "The station could not complete that operation. Please try again.",
        )

    @app.get("/")
    @auth.login_required
    def dashboard():
        """Render the authenticated staff dashboard."""
        report = reports.build_operations_report()
        return render_template(
            "dashboard.html",
            app_name=app.config["APP_NAME"],
            version=app.config["APP_VERSION"],
            active_count=report["active_count"],
            overdue_count=report["overdue_count"],
            available_slots=report["available_slots"],
            total_shelf_slots=report["total_slots"],
            fees_collected=report["fees_total"],
            recent_logs=report["recent_logs"],
        )

    @app.get("/packages")
    @auth.login_required
    def package_list():
        """List and search parcels in the staff workspace."""
        query = request.args.get("q", "").strip()
        status = request.args.get("status", "all").strip()
        if status not in {"all", "stored", "collected", "overdue"}:
            status = "all"

        now = datetime.now(timezone.utc)
        if query:
            package_records = parcels.search_packages(query, status, now=now)
        else:
            package_records = parcels.list_packages(status, now=now)

        return render_template(
            "packages.html",
            app_name=app.config["APP_NAME"],
            version=app.config["APP_VERSION"],
            packages=package_records,
            query=query,
            selected_status=status,
        )

    @app.post("/packages/check-in")
    @auth.login_required
    def package_check_in():
        """Process the staff check-in form."""
        if not auth.validate_csrf():
            abort(400, description="Invalid or missing CSRF token.")
        try:
            parcel = parcels.check_in(
                request.form.get("courier", ""),
                request.form.get("recipient", ""),
                request.form.get("recipient_contact", ""),
                request.form.get("parcel_reference", ""),
            )
        except ParcelStationError as error:
            flash(str(error), "error")
        else:
            flash(
                f"Parcel {parcel['pickup_code']} checked in at "
                f"{parcel['shelf_slot']}.",
                "success",
            )
        return redirect(url_for("package_list"), code=303)

    @app.get("/pickup")
    @auth.login_required
    def pickup_page():
        """Render the staff pickup workflow."""
        return render_template(
            "pickup.html",
            app_name=app.config["APP_NAME"],
            version=app.config["APP_VERSION"],
            found_package=None,
            lookup_error=None,
            lookup_code="",
        )

    @app.post("/pickup/lookup")
    @auth.login_required
    def pickup_lookup():
        """Look up a parcel before confirming collection."""
        if not auth.validate_csrf():
            abort(400, description="Invalid or missing CSRF token.")
        code = request.form.get("pickup_code", "").strip()
        now = datetime.now(timezone.utc)
        try:
            found_package = parcels.find_stored_package(code, now=now)
        except ParcelStationError as error:
            return (
                render_template(
                    "pickup.html",
                    app_name=app.config["APP_NAME"],
                    version=app.config["APP_VERSION"],
                    found_package=None,
                    lookup_error=str(error),
                    lookup_code=code,
                ),
                400,
            )
        return render_template(
            "pickup.html",
            app_name=app.config["APP_NAME"],
            version=app.config["APP_VERSION"],
            found_package=found_package,
            lookup_error=None,
            lookup_code=code,
        )

    @app.post("/pickup/confirm")
    @auth.login_required
    def pickup_confirm():
        """Confirm parcel collection and record its fee."""
        if not auth.validate_csrf():
            abort(400, description="Invalid or missing CSRF token.")
        try:
            package = parcels.pick_up(request.form.get("pickup_code", ""))
        except ParcelStationError as error:
            flash(str(error), "error")
        else:
            flash(
                f"Parcel {package['pickup_code']} collected from "
                f"{package['shelf_slot']}. Fee: ${package['fee_charged']:.2f}.",
                "success",
            )
        return redirect(url_for("pickup_page"), code=303)

    @app.get("/reports")
    @auth.login_required
    def reports_page():
        """Render the daily report, analytics, and shelf map."""
        report = reports.build_operations_report()
        return render_template(
            "reports.html",
            app_name=app.config["APP_NAME"],
            version=app.config["APP_VERSION"],
            report=report,
        )

    @app.get("/health")
    def health():
        """Return a lightweight service health response."""
        db_status = database.database_status()
        status_code = 200 if db_status == "ready" else 503
        return (
            jsonify(
                {
                    "status": "ok" if status_code == 200 else "error",
                    "service": "campus-parcel-station",
                    "version": app.config["APP_VERSION"],
                    "stage": "hardened-release",
                    "database": db_status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            status_code,
        )

    return app
