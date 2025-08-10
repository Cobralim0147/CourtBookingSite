from datetime import datetime, timedelta, date, time
from dataclasses import dataclass, field
from typing import Literal, Optional, List, Dict
from abc import ABC, abstractmethod

Role = Literal["user", "admin"]
BookingStatus = Literal["PENDING", "PAID"]

class User:
    """Base User class with common user functionality."""
    
    def __init__(self, username: str, password: str, balance_usd: float = 0.0):
        self._username = username
        self._password = password
        self._balance_usd = balance_usd
        self._role = "user"
    
    @property
    def username(self) -> str:
        return self._username
    
    @property
    def password(self) -> str:
        return self._password
    
    @property
    def balance_usd(self) -> float:
        return self._balance_usd
    
    @balance_usd.setter
    def balance_usd(self, value: float):
        if value < 0:
            raise ValueError("Balance cannot be negative")
        self._balance_usd = round(value, 2)
    
    @property
    def role(self) -> Role:
        return self._role
    
    def deduct_balance(self, amount: float) -> bool:
        """Deduct amount from balance if sufficient funds exist."""
        if self._balance_usd >= amount:
            self.balance_usd = self._balance_usd - amount
            return True
        return False
    
    def can_afford(self, amount: float) -> bool:
        """Check if user can afford the given amount."""
        return self._balance_usd >= amount

class Admin(User):
    """Admin class inheriting from User with additional privileges."""
    
    def __init__(self, username: str, password: str, balance_usd: float = 0.0):
        super().__init__(username, password, balance_usd)
        self._role = "admin"

@dataclass
class Account:
    username: str
    password: str
    role: Role
    balance_usd: float = 0.0

class Booking:
    """Represents a court booking with proper encapsulation."""
    
    def __init__(self, booking_id: str, username: str, sport: str, court_id: str, 
                 start: datetime, duration_slots: int, price_usd: float):
        self._booking_id = booking_id
        self._username = username
        self._sport = sport
        self._court_id = court_id
        self._start = start
        self._duration_slots = duration_slots
        self._price_usd = price_usd
        self._status: BookingStatus = "PENDING"
        self._created_at = datetime.now()
        self._hold_expires_at: Optional[datetime] = None
    
    @property
    def booking_id(self) -> str:
        return self._booking_id
    
    @property
    def username(self) -> str:
        return self._username
    
    @property
    def sport(self) -> str:
        return self._sport
    
    @property
    def court_id(self) -> str:
        return self._court_id
    
    @property
    def start(self) -> datetime:
        return self._start
    
    @property
    def duration_slots(self) -> int:
        return self._duration_slots
    
    @property
    def price_usd(self) -> float:
        return self._price_usd
    
    @property
    def status(self) -> BookingStatus:
        return self._status
    
    @status.setter
    def status(self, value: BookingStatus):
        self._status = value
    
    @property
    def created_at(self) -> datetime:
        return self._created_at
    
    @property
    def hold_expires_at(self) -> Optional[datetime]:
        return self._hold_expires_at
    
    @hold_expires_at.setter
    def hold_expires_at(self, value: Optional[datetime]):
        self._hold_expires_at = value

    def end_time(self) -> datetime:
        """Calculate the end time of the booking."""
        return self._start + timedelta(minutes=30 * self._duration_slots)
    
    def is_expired(self) -> bool:
        """Check if the booking hold has expired."""
        if self._status == "PENDING" and self._hold_expires_at:
            return datetime.now() >= self._hold_expires_at
        return False
    
    def confirm_payment(self):
        """Mark booking as paid and remove hold expiration."""
        self._status = "PAID"
        self._hold_expires_at = None
    
    def set_hold_expiration(self, expiration_time: datetime):
        """Set when the hold expires for pending bookings."""
        if self._status == "PENDING":
            self._hold_expires_at = expiration_time

class Court:
    """Represents a sports court."""
    
    def __init__(self, court_id: str, sport: str):
        self._court_id = court_id
        self._sport = sport
    
    @property
    def court_id(self) -> str:
        return self._court_id
    
    @property
    def sport(self) -> str:
        return self._sport

class Sport:
    """Represents a sport with its associated courts and pricing."""
    
    def __init__(self, name: str, hourly_rate: float, courts: List[Court]):
        self._name = name
        self._hourly_rate = hourly_rate
        self._courts = courts
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def hourly_rate(self) -> float:
        return self._hourly_rate
    
    @property
    def courts(self) -> List[Court]:
        return self._courts.copy()
    
    def get_court_ids(self) -> List[str]:
        """Get list of court IDs for this sport."""
        return [court.court_id for court in self._courts]
    
    def calculate_price(self, duration_slots: int) -> float:
        """Calculate price for given duration in 30-minute slots."""
        hours = 0.5 * duration_slots
        return round(self._hourly_rate * hours, 2)
