"""
Abstract interfaces for better OOP design and testability.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from domain import User, Booking, Sport, Role

class IAuthenticationService(ABC):
    """Interface for authentication services."""
    
    @abstractmethod
    def authenticate(self, username: str, password: str, expected_role: Role) -> Optional[User]:
        pass
    
    @abstractmethod
    def get_user(self, username: str) -> Optional[User]:
        pass

class IInventoryService(ABC):
    """Interface for inventory management services."""
    
    @abstractmethod
    def get_sport(self, sport_name: str) -> Optional[Sport]:
        pass
    
    @abstractmethod
    def get_all_sports(self) -> List[Sport]:
        pass
    
    @abstractmethod
    def get_courts_for_sport(self, sport_name: str) -> List[str]:
        pass

class IPricingService(ABC):
    """Interface for pricing services."""
    
    @abstractmethod
    def get_hourly_rate(self, sport_name: str) -> float:
        pass
    
    @abstractmethod
    def calculate_price(self, sport_name: str, duration_slots: int) -> float:
        pass

class IBookingService(ABC):
    """Interface for booking management services."""
    
    @abstractmethod
    def get_availability_grid(self, sport_name: str, target_date: date) -> Dict[str, List[Tuple[datetime, bool]]]:
        pass
    
    @abstractmethod
    def create_booking_hold(self, username: str, sport_name: str, court_id: str, 
                          start_time: datetime, duration_slots: int) -> Booking:
        pass
    
    @abstractmethod
    def confirm_payment(self, user: User, booking_id: str) -> Tuple[bool, str, Optional[Booking]]:
        pass

class IDisplayService(ABC):
    """Interface for display services."""
    
    @abstractmethod
    def display_compact_grid(self, sport_name: str, target_date: date, 
                           availability_grid: Dict[str, List[Tuple[datetime, bool]]]) -> None:
        pass
    
    @abstractmethod
    def display_legend(self) -> None:
        pass
