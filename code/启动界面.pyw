"""双击启动桌面界面（.pyw 由 pythonw 打开，不显示黑色控制台）。"""

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
