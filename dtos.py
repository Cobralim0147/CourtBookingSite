"""
Data Transfer Objects for clean data passing between layers.
"""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from domain import BookingStatus, Role

@dataclass
class BookingRequest:
    """Request to create a new booking."""
    username: str
    sport_name: str
    court_id: str
    start_time: datetime
    duration_slots: int

@dataclass
class BookingResponse:
    """Response containing booking information."""
    booking_id: str
    username: str
    sport_name: str
    court_id: str
    start_time: datetime
    end_time: datetime
    duration_hours: float
    price_usd: float
    status: BookingStatus
    hold_expires_at: Optional[datetime] = None

@dataclass
class UserInfo:
    """User information DTO."""
    username: str
    role: Role
    balance_usd: float

@dataclass
class AvailabilityQuery:
    """Query for availability information."""
    sport_name: str
    target_date: date
    start_time: Optional[datetime] = None
    duration_slots: Optional[int] = None
