"""Application entry point for the Campus Parcel Station web app."""

from config import Config
from parcel_station.web import create_app


app = create_app(Config)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
