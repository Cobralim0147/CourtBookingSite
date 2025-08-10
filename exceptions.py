"""
Custom exceptions for the booking system.
"""

class BookingSystemException(Exception):
    """Base exception for booking system."""
    pass

class AuthenticationException(BookingSystemException):
    """Raised when authentication fails."""
    pass

class BookingException(BookingSystemException):
    """Base exception for booking-related errors."""
    pass

class BookingNotAvailableException(BookingException):
    """Raised when trying to book an unavailable slot."""
    pass

class BookingNotFoundException(BookingException):
    """Raised when booking is not found."""
    pass

class InsufficientFundsException(BookingException):
    """Raised when user has insufficient balance."""
    pass

class BookingExpiredException(BookingException):
    """Raised when booking hold has expired."""
    pass

class InvalidDateException(BookingException):
    """Raised when date is outside booking window."""
    pass

class ConfigurationException(BookingSystemException):
    """Raised when configuration is invalid."""
    pass
