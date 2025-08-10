from datetime import datetime, timedelta, date, time
from typing import Dict, List, Optional, Tuple
from domain import User, Admin, Account, Booking, Sport, Court, Role

class AuthenticationService:
    """Handles user authentication and account management."""
    
    def __init__(self, config: dict):
        self._users: Dict[str, User] = {}
        self._load_accounts(config)
    
    def _load_accounts(self, config: dict):
        """Load user and admin accounts from configuration."""
        # Load regular users
        for user_data in config["accounts"]["users"]:
            user = User(
                username=user_data["username"],
                password=user_data["password"],
                balance_usd=float(user_data.get("balance_usd", 0.0))
            )
            self._users[user.username] = user
        
        # Load admin users
        for admin_data in config["accounts"]["admins"]:
            admin = Admin(
                username=admin_data["username"],
                password=admin_data["password"],
                balance_usd=float(admin_data.get("balance_usd", 0.0))
            )
            self._users[admin.username] = admin
    
    def authenticate(self, username: str, password: str, expected_role: Role) -> Optional[User]:
        """Authenticate user with username, password and expected role."""
        user = self._users.get(username)
        if user and user.password == password and user.role == expected_role:
            return user
        return None
    
    def get_user(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self._users.get(username)

class SportInventoryService:
    """Manages sports and court inventory."""
    
    def __init__(self, config: dict):
        self._sports: Dict[str, Sport] = {}
        self._load_sports_and_courts(config)
    
    def _load_sports_and_courts(self, config: dict):
        """Load sports, courts and rates from configuration."""
        rates = config["rates_usd_per_hour"]
        courts_config = config["courts"]
        
        for sport_name, court_ids in courts_config.items():
            courts = [Court(court_id, sport_name) for court_id in court_ids]
            hourly_rate = float(rates[sport_name])
            sport = Sport(sport_name, hourly_rate, courts)
            self._sports[sport_name] = sport
    
    def get_sport(self, sport_name: str) -> Optional[Sport]:
        """Get sport by name."""
        return self._sports.get(sport_name)
    
    def get_all_sports(self) -> List[Sport]:
        """Get all available sports."""
        return list(self._sports.values())
    
    def get_sport_names(self) -> List[str]:
        """Get list of all sport names."""
        return list(self._sports.keys())
    
    def get_courts_for_sport(self, sport_name: str) -> List[str]:
        """Get court IDs for a specific sport."""
        sport = self._sports.get(sport_name)
        return sport.get_court_ids() if sport else []

class PricingService:
    """Handles pricing calculations."""
    
    def __init__(self, inventory_service: SportInventoryService):
        self._inventory = inventory_service
    
    def get_hourly_rate(self, sport_name: str) -> float:
        """Get hourly rate for a sport."""
        sport = self._inventory.get_sport(sport_name)
        return sport.hourly_rate if sport else 0.0
    
    def calculate_price(self, sport_name: str, duration_slots: int) -> float:
        """Calculate price for booking duration."""
        sport = self._inventory.get_sport(sport_name)
        return sport.calculate_price(duration_slots) if sport else 0.0

class BookingIDGenerator:
    """Generates unique booking IDs."""
    
    def __init__(self):
        self._daily_counters: Dict[str, int] = {}
    
    def generate_id(self, booking_date: date) -> str:
        """Generate a new booking ID for the given date."""
        date_key = booking_date.strftime("%Y%m%d")
        counter = self._daily_counters.get(date_key, 0) + 1
        self._daily_counters[date_key] = counter
        return f"BK-{date_key}-{counter:04d}"

class BookingManagementService:
    """Manages court bookings and availability."""
    
    def __init__(self, config: dict, inventory_service: SportInventoryService, 
                 pricing_service: PricingService, id_generator: BookingIDGenerator):
        self._inventory = inventory_service
        self._pricing = pricing_service
        self._id_generator = id_generator
        
        # Configuration
        self._venue_name = config["venue"]["name"]
        self._booking_window_days = int(config["venue"]["booking_window_days"])
        self._hold_timeout_minutes = int(config["venue"]["hold_timeout_minutes"])
        self._slot_minutes = 30
        
        # Storage
        self._bookings_by_court: Dict[str, List[Booking]] = {}
        self._bookings_by_user: Dict[str, List[Booking]] = {}
    
    def _cleanup_expired_holds(self):
        """Remove expired pending bookings."""
        current_time = datetime.now()
        
        for court_id, bookings in self._bookings_by_court.items():
            # Filter out expired bookings
            valid_bookings = []
            for booking in bookings:
                if not booking.is_expired():
                    valid_bookings.append(booking)
            self._bookings_by_court[court_id] = valid_bookings
        
        # Clean user bookings as well
        for username, bookings in self._bookings_by_user.items():
            valid_bookings = []
            for booking in bookings:
                if not booking.is_expired():
                    valid_bookings.append(booking)
            self._bookings_by_user[username] = valid_bookings
    
    def _is_within_booking_window(self, target_date: date) -> bool:
        """Check if date is within allowed booking window."""
        today = date.today()
        max_date = today + timedelta(days=self._booking_window_days)
        return today <= target_date <= max_date
    
    def _check_court_availability(self, court_id: str, start_time: datetime, end_time: datetime) -> bool:
        """Check if court is available for the given time span."""
        court_bookings = self._bookings_by_court.get(court_id, [])
        
        for booking in court_bookings:
            booking_end = booking.end_time()
            # Check for overlap
            if not (end_time <= booking.start or start_time >= booking_end):
                return False
        return True
    
    def get_availability_grid(self, sport_name: str, target_date: date) -> Dict[str, List[Tuple[datetime, bool]]]:
        """Get availability grid for all courts of a sport on a specific date."""
        self._cleanup_expired_holds()
        
        court_ids = self._inventory.get_courts_for_sport(sport_name)
        grid = {}
        
        # Generate 48 slots for 24 hours (30-minute slots)
        day_start = datetime.combine(target_date, time(0, 0))
        slots = [day_start + timedelta(minutes=i * self._slot_minutes) for i in range(48)]
        
        for court_id in court_ids:
            court_slots = []
            for slot_start in slots:
                slot_end = slot_start + timedelta(minutes=self._slot_minutes)
                is_available = self._check_court_availability(court_id, slot_start, slot_end)
                court_slots.append((slot_start, is_available))
            grid[court_id] = court_slots
        
        return grid
    
    def get_available_courts(self, sport_name: str, start_time: datetime, duration_slots: int) -> List[str]:
        """Get courts available for the entire booking duration."""
        self._cleanup_expired_holds()
        
        court_ids = self._inventory.get_courts_for_sport(sport_name)
        end_time = start_time + timedelta(minutes=30 * duration_slots)
        available_courts = []
        
        for court_id in court_ids:
            if self._check_court_availability(court_id, start_time, end_time):
                available_courts.append(court_id)
        
        return available_courts
    
    def create_booking_hold(self, username: str, sport_name: str, court_id: str, 
                          start_time: datetime, duration_slots: int) -> Booking:
        """Create a new booking with hold."""
        if not self._is_within_booking_window(start_time.date()):
            raise ValueError(f"Date outside booking window (0-{self._booking_window_days} days)")
        
        # Check availability one more time
        end_time = start_time + timedelta(minutes=30 * duration_slots)
        if not self._check_court_availability(court_id, start_time, end_time):
            raise ValueError("Court no longer available for selected time")
        
        # Generate booking ID and calculate price
        booking_id = self._id_generator.generate_id(start_time.date())
        price = self._pricing.calculate_price(sport_name, duration_slots)
        
        # Create booking
        booking = Booking(booking_id, username, sport_name, court_id, start_time, duration_slots, price)
        
        # Set hold expiration
        hold_expiration = datetime.now() + timedelta(minutes=self._hold_timeout_minutes)
        booking.set_hold_expiration(hold_expiration)
        
        # Store booking
        self._bookings_by_court.setdefault(court_id, []).append(booking)
        self._bookings_by_user.setdefault(username, []).append(booking)
        
        return booking
    
    def confirm_payment(self, user: User, booking_id: str) -> Tuple[bool, str, Optional[Booking]]:
        """Confirm payment for a booking."""
        self._cleanup_expired_holds()
        
        # Find booking
        user_bookings = self._bookings_by_user.get(user.username, [])
        booking = None
        
        for b in user_bookings:
            if b.booking_id == booking_id and b.status == "PENDING":
                booking = b
                break
        
        if not booking:
            return False, "Booking not found or not pending", None
        
        if booking.is_expired():
            self.cancel_pending_booking(user.username, booking_id)
            return False, "Hold expired. Please start again.", None
        
        if not user.can_afford(booking.price_usd):
            return False, "Insufficient balance", booking
        
        # Process payment
        if user.deduct_balance(booking.price_usd):
            booking.confirm_payment()
            return True, "Payment successful", booking
        
        return False, "Payment failed", booking
    
    def cancel_pending_booking(self, username: str, booking_id: str) -> bool:
        """Cancel a pending booking."""
        self._cleanup_expired_holds()
        
        # Find and remove booking
        user_bookings = self._bookings_by_user.get(username, [])
        booking_to_remove = None
        
        for booking in user_bookings:
            if booking.booking_id == booking_id and booking.status == "PENDING":
                booking_to_remove = booking
                break
        
        if not booking_to_remove:
            return False
        
        # Remove from court bookings
        court_bookings = self._bookings_by_court.get(booking_to_remove.court_id, [])
        self._bookings_by_court[booking_to_remove.court_id] = [
            b for b in court_bookings if b.booking_id != booking_id
        ]
        
        # Remove from user bookings
        self._bookings_by_user[username] = [
            b for b in user_bookings if b.booking_id != booking_id
        ]
        
        return True
    
    def admin_remove_booking(self, booking_id: str) -> bool:
        """Admin function to remove any booking."""
        self._cleanup_expired_holds()
        
        # Find booking across all courts
        target_booking = None
        target_court = None
        
        for court_id, bookings in self._bookings_by_court.items():
            for booking in bookings:
                if booking.booking_id == booking_id:
                    target_booking = booking
                    target_court = court_id
                    break
            if target_booking:
                break
        
        if not target_booking:
            return False
        
        # Remove from court and user lists
        self._bookings_by_court[target_court] = [
            b for b in self._bookings_by_court[target_court] if b.booking_id != booking_id
        ]
        
        user_bookings = self._bookings_by_user.get(target_booking.username, [])
        self._bookings_by_user[target_booking.username] = [
            b for b in user_bookings if b.booking_id != booking_id
        ]
        
        return True
    
    def get_user_bookings(self, username: str) -> List[Booking]:
        """Get all bookings for a user."""
        self._cleanup_expired_holds()
        user_bookings = self._bookings_by_user.get(username, [])
        return sorted(user_bookings, key=lambda b: (b.start, b.booking_id))
    
    def get_all_bookings(self) -> List[Booking]:
        """Get all bookings in the system."""
        self._cleanup_expired_holds()
        all_bookings = []
        for bookings in self._bookings_by_court.values():
            all_bookings.extend(bookings)
        return sorted(all_bookings, key=lambda b: (b.start, b.booking_id))

# Legacy compatibility classes
class AuthService(AuthenticationService):
    def login(self, username: str, password: str, role: Role) -> Optional[Account]:
        user = self.authenticate(username, password, role)
        if user:
            return Account(username=user.username, password=user.password, 
                         role=user.role, balance_usd=user.balance_usd)
        return None

class InventoryService(SportInventoryService):
    def list_sports(self) -> List[str]:
        return self.get_sport_names()
    
    def list_courts(self, sport: str) -> List[str]:
        return self.get_courts_for_sport(sport)

class BookingService(BookingManagementService):
    def __init__(self, cfg: dict, inventory: InventoryService, pricing: PricingService, idgen: 'BookingIDService'):
        # Convert new services to legacy format for compatibility
        sport_inventory = SportInventoryService(cfg)
        pricing_service = PricingService(sport_inventory)
        id_generator = BookingIDGenerator()
        super().__init__(cfg, sport_inventory, pricing_service, id_generator)
        
        # Store legacy references
        self.inventory = inventory
        self.pricing = pricing
        self.idgen = idgen
        self.venue_name = cfg["venue"]["name"]
        self.booking_window_days = int(cfg["venue"]["booking_window_days"])
        self.hold_timeout = timedelta(minutes=int(cfg["venue"]["hold_timeout_minutes"]))
        self.time_format_24h = bool(cfg["venue"]["time_format_24h"])
        self.slot_minutes = 30
    
    # Legacy method names - delegate to new methods
    def availability_grid(self, sport: str, d: date) -> Dict[str, List[Tuple[datetime, bool]]]:
        return self.get_availability_grid(sport, d)
    
    def courts_available_for_span(self, sport: str, start_dt: datetime, duration_slots: int) -> List[str]:
        return self.get_available_courts(sport, start_dt, duration_slots)
    
    def place_hold(self, username: str, sport: str, court_id: str, start_dt: datetime, duration_slots: int) -> Booking:
        return self.create_booking_hold(username, sport, court_id, start_dt, duration_slots)
    
    def cancel_pending(self, username: str, booking_id: str) -> bool:
        return self.cancel_pending_booking(username, booking_id)
    
    def admin_remove(self, booking_id: str) -> bool:
        return self.admin_remove_booking(booking_id)
    
    def user_bookings(self, username: str) -> List[Booking]:
        return self.get_user_bookings(username)
    
    def all_bookings(self) -> List[Booking]:
        return self.get_all_bookings()
    
    def confirm_payment(self, account: Account, booking_id: str) -> Tuple[bool, str, Optional[Booking]]:
        # Convert Account to User for new service
        user = User(account.username, account.password, account.balance_usd)
        if account.role == "admin":
            user = Admin(account.username, account.password, account.balance_usd)
        
        success, message, booking = super().confirm_payment(user, booking_id)
        
        # Update account balance
        account.balance_usd = user.balance_usd
        
        return success, message, booking

class BookingIDService(BookingIDGenerator):
    def next_id(self, d: date) -> str:
        return self.generate_id(d)