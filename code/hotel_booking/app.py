"""Application container wiring repositories and services."""

from __future__ import annotations

from pathlib import Path

from .audit import AuditService
from .auth import AuthService
from .billing import BillingService
from .booking import BookingService
from .db import connect, init_db, seed_demo
from .frontdesk import FrontDeskService
from .governance import GovernanceService
from .hotel_admin import HotelAdminService
from .inventory import InventoryService
from .pricing import PricingService
from .reports import ReportService
from .repository import Repository


class App:
    """Composition root used by the CLI, the demo and the tests."""

    def __init__(self, db_path: str | Path | None = None, seed: bool = True) -> None:
        self.conn = connect(db_path)
        init_db(self.conn)
        if seed:
            seed_demo(self.conn)
        self.repo = Repository(self.conn)
        self.audit = AuditService(self.repo)
        self.auth = AuthService(self.repo)
        self.pricing = PricingService(self.repo)
        self.inventory = InventoryService(self.repo)
        self.billing = BillingService(self.repo, self.audit)
        self.booking = BookingService(
            self.repo, self.audit, self.pricing, self.inventory, self.billing
        )
        self.frontdesk = FrontDeskService(self.repo, self.audit, self.billing)
        self.hotel_admin = HotelAdminService(self.repo, self.audit)
        self.governance = GovernanceService(self.repo, self.audit)
        self.reports = ReportService(self.repo)

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()


__all__ = ["App"]
