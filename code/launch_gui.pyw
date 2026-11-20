"""Double-click launcher (pythonw, no console)."""

import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hotel_booking.app import App
from hotel_booking.gui import HotelGUI


def main() -> None:
    """Open the desktop client."""
    HotelGUI(App()).run()


if __name__ == "__main__":
    main()
