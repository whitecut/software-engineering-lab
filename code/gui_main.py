"""Standalone GUI entry point used by PyInstaller."""

from hotel_booking.app import App
from hotel_booking.gui import HotelGUI


def main() -> None:
    """Open the desktop client."""
    HotelGUI(App()).run()


if __name__ == "__main__":
    main()
