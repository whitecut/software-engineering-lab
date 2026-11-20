"""Domain errors for the hotel booking system."""


class DomainError(Exception):
    """Base class for all business errors."""


class ValidationError(DomainError):
    """Raised when user input violates a business rule."""


class NotFoundError(DomainError):
    """Raised when an entity does not exist."""


class PermissionDeniedError(DomainError):
    """Raised when the current actor may not perform the action."""


class ConflictError(DomainError):
    """Raised when a unique constraint or state conflict happens."""


class InsufficientInventoryError(DomainError):
    """Raised when the requested rooms are not available."""

    def __init__(self, message: str, date: str | None = None) -> None:
        super().__init__(message)
        self.date = date


class InvalidStateError(DomainError):
    """Raised when an order or room transition is not allowed."""
