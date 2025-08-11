import sys
import getpass
from datetime import datetime, date, time
from typing import Optional
from domain import User, Admin, Role, Account
from services import (
    AuthenticationService, SportInventoryService, PricingService, 
    BookingIDGenerator, BookingManagementService,
    # Legacy compatibility
    AuthService, InventoryService, BookingService, BookingIDService
)
from display_service import AvailabilityDisplayService, Color

class CLI:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.auth = AuthService(cfg)
        self.inventory = InventoryService(cfg)
        self.pricing = PricingService(cfg)
        self.idgen = BookingIDService()
        self.bookings = BookingService(cfg, self.inventory, self.pricing, self.idgen)
        self.display_service = AvailabilityDisplayService()

        self.venue_name = cfg["venue"]["name"]
        self.booking_window_days = int(cfg["venue"]["booking_window_days"])
        self.time_format_24h = bool(cfg["venue"]["time_format_24h"])
        self.slot_minutes = 30

        self.current: Optional[Account] = None

    # ---- color helper ----
    def _colorize_text(self, text: str, color: Color, bold: bool = False) -> str:
        """Apply color formatting to text."""
        prefix = color.value
        if bold:
            prefix = Color.BOLD.value + prefix
        return f"{prefix}{text}{Color.RESET.value}"

    def _error(self, message: str) -> None:
        """Print error message in red."""
        print(self._colorize_text(message, Color.RED))

    def _success(self, message: str) -> None:
        """Print success message in green."""
        print(self._colorize_text(message, Color.GREEN))

    def _info(self, message: str) -> None:
        """Print info message in cyan."""
        print(self._colorize_text(message, Color.CYAN))

    # ---- input helpers ----
    def _inp(self, prompt: str) -> str:
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

    def _pause(self):
        self._inp("\n[Enter] to continue...")

    def _parse_date(self, s: str) -> Optional[date]:
        # Expect YYYY-MM-DD
        try:
            y, m, d = map(int, s.split("-"))
            return date(y, m, d)
        except Exception:
            return None

    def _parse_time(self, s: str) -> Optional[time]:
        # Support HH:MM (24h) 
        try:
            if ":" in s:
                h, m = map(int, s.split(":"))
            else:
                h = int(s)
                m = 0
            if h < 0 or h > 23 or m not in (0, 30):
                return None
            return time(hour=h, minute=m)
        except Exception:
            return None

    def _fmt_dt(self, dt: datetime) -> str:
        if self.time_format_24h:
            return dt.strftime("%Y-%m-%d %H:%M")
        else:
            return dt.strftime("%Y-%m-%d %I:%M %p")

    # ---- menu flows ----
    def run(self):
        while True:
            self.current = None
            self.menu_home()

    def menu_home(self):
        while True:
            title = "=== Cobra's ZooKeeping Sport Center ==="
            print(f"\n{self._colorize_text(title, Color.CYAN, True)}")
            print(f"{self._colorize_text('1) Login as User', Color.BLUE)}")
            print(f"{self._colorize_text('2) Login as Admin', Color.BLUE)}")
            print(f"{self._colorize_text('3) View Sports / About', Color.BLUE)}")
            print(f"{self._colorize_text('4) Exit', Color.BLUE)}")
            choice = self._inp("Choose (1-4): ")
            if choice == "1":
                self.login_flow("user")
                if self.current:  # go into user menu
                    self.menu_user()
            elif choice == "2":
                self.login_flow("admin")
                if self.current:
                    self.menu_admin()
            elif choice == "3":
                self.show_about()
            elif choice == "4":
                self._success("Goodbye!")
                sys.exit(0)
            else:
                self._error("Invalid choice. Enter 1–4.")

    def login_flow(self, role: Role):
        print(f"\n{self._colorize_text(f'== Login ({role.upper()}) ==', Color.YELLOW, True)}")
        username = self._inp("Username: ")
        password = getpass.getpass("Password: ")
        
        acc = self.auth.login(username, password, role)
        if not acc:
            self._error("Login error: invalid name or password.")
            self._pause()
            self.current = None
        else:
            self._success(f"Login successful! Welcome, {username}")
            self.current = acc

    def show_about(self):
        print(f"\nVenue: {self.venue_name}")
        print("Sports:", ", ".join(self.inventory.list_sports()))
        print("Booking window: 0..%d days ahead" % self.booking_window_days)
        print("Slot length: 30 minutes (24×7)")
        print("Rates (USD/hr):")
        for s in self.inventory.list_sports():
            print(f"  - {s.title()}: ${self.pricing.hourly_rate(s):.2f}")
        self._pause()

    # ---- user menus ----
    def menu_user(self):
        while True:
            acc = self.current
            assert acc is not None and acc.role == "user" or acc.role == "admin"
            print(f"\n{self._colorize_text(f'== User Menu ({acc.username}, balance ${acc.balance_usd:.2f}) ==', Color.GREEN, True)}")
            print(f"{self._colorize_text('1) Search availability', Color.BLUE)}")
            print(f"{self._colorize_text('2) Book a court', Color.BLUE)}")
            print(f"{self._colorize_text('3) View my bookings', Color.BLUE)}")
            print(f"{self._colorize_text('4) View account', Color.BLUE)}")
            print(f"{self._colorize_text('5) Logout', Color.BLUE)}")
            choice = self._inp("Choose (1-5): ")
            if choice == "1":
                self.flow_search()
            elif choice == "2":
                self.flow_book()
            elif choice == "3":
                self.flow_view_my_bookings()
            elif choice == "4":
                self.flow_view_account()
            elif choice == "5":
                self._info("Logging out...")
                self.current = None
                return
            else:
                self._error("Invalid choice. Enter 1–5.")

    # ---- admin menus ----
    def menu_admin(self):
        while True:
            acc = self.current
            assert acc is not None and acc.role == "admin"
            print(f"\n{self._colorize_text(f'== Admin Menu ({acc.username}) ==', Color.MAGENTA, True)}")
            print(f"{self._colorize_text('1) Search availability', Color.BLUE)}")
            print(f"{self._colorize_text('2) Book a court', Color.BLUE)}")
            print(f"{self._colorize_text('3) Manage bookings', Color.BLUE)}")
            print(f"{self._colorize_text('4) View account', Color.BLUE)}")
            print(f"{self._colorize_text('5) Logout', Color.BLUE)}")
            choice = self._inp("Choose (1-5): ")
            if choice == "1":
                self.flow_search()
            elif choice == "2":
                self.flow_book()
            elif choice == "3":
                self.flow_manage_bookings()
            elif choice == "4":
                self.flow_view_account()
            elif choice == "5":
                self._info("Logging out...")
                self.current = None
                return
            else:
                self._error("Invalid choice. Enter 1–5.")

    # ---- flows ----

    def _choose_sport(self) -> Optional[str]:
        sports = self.inventory.list_sports()
        print(f"\n{self._colorize_text('Available sports:', Color.CYAN)}")
        for i, s in enumerate(sports, 1):
            print(f"{self._colorize_text(f'{i}) {s.title()}', Color.YELLOW)}")
        idx = self._inp("Choose sport #: ")
        try:
            sel = sports[int(idx) - 1]
            return sel
        except Exception:
            self._error("Invalid selection.")
            return None

    def flow_search(self):
        sport = self._choose_sport()
        if not sport:
            return
        d_str = self._inp("Enter date (YYYY-MM-DD): ")
        d = self._parse_date(d_str)
        if not d:
            self._error("Invalid date.")
            return
        
        # Get availability grid
        grid = self.bookings.availability_grid(sport, d)
        if not grid:
            self._error("No courts configured for this sport.")
            return

        # Display options
        print("\nAvailability Display Options:")
        print("1) Compact Grid View (30 minutes)")
        print("2) Detailed Grid View (4-hour blocks)") 
        print("3) Available Slots List")
        print("4 All Views")
        
        view_choice = self._inp("Choose display format (1-4): ").strip()
        
        if view_choice == "1":
            self.display_service.display_full_30min_grid(sport, d, grid)
        elif view_choice == "2":
            self.display_service.display_detailed_grid(sport, d, grid)
        elif view_choice == "3":
            self.display_service.display_available_slots_list(sport, d, grid)
        elif view_choice == "4":
            self.display_service.display_full_30min_grid(sport, d, grid)
            self.display_service.display_detailed_grid(sport, d, grid)
            self.display_service.display_available_slots_list(sport, d, grid)
        else:
            # Default to compact view (30-minute grid)
            self.display_service.display_full_30min_grid(sport, d, grid)
        
        self.display_service.display_legend()

        go = self._inp("\nPress B to start booking now for this sport, or Enter to return: ").strip().upper()
        if go == "B":
            self.flow_book(pref_sport=sport, pref_date=d)

    def flow_book(self, pref_sport: Optional[str] = None, pref_date: Optional[date] = None):
        acc = self.current
        if not acc:
            self._error("Please login first.")
            return
        sport = pref_sport or self._choose_sport()
        if not sport:
            return
        if pref_date is not None:
            d = pref_date
        else:
            d_str = self._inp("Enter date (YYYY-MM-DD): ")
            d = self._parse_date(d_str)
            if not d:
                self._error("Invalid date.")
                return
        t_str = self._inp("Enter start time (HH:MM, 24h, minutes must be 00 or 30): ")
        t = self._parse_time(t_str)
        if not t:
            self._error("Invalid time (use HH:MM, minutes 00 or 30).")
            return
        attempts = 0
        dur_hours = None
        while attempts < 3:
            try:
                dur_hours = float(self._inp("Enter duration in hours (e.g., 1.0, 1.5, 2): "))
                if dur_hours <= 0:
                    raise ValueError
            except Exception:
                self._error("Invalid duration.")
                attempts += 1
                continue
            # convert to 30-min slots
            slots = int(dur_hours * 2)
            if abs(dur_hours - (slots * 0.5)) > 1e-9:
                self._error("Duration must be in increments of 0.5 hours.")
                attempts += 1
                continue
            break
        else:
            return

        start_dt = datetime.combine(d, t)
        avail_courts = self.bookings.courts_available_for_span(sport, start_dt, slots)
        if not avail_courts:
            self._error("Fully booked for the selected period.")
            return

        print(f"\n{self._colorize_text('Courts available for the entire span:', Color.CYAN)}")
        for i, c in enumerate(avail_courts, 1):
            print(f"{self._colorize_text(f'{i}) {c}', Color.YELLOW)}")
        idx = self._inp("Choose court #: ")
        try:
            court_id = avail_courts[int(idx) - 1]
        except Exception:
            self._error("Invalid selection.")
            return

        # place hold
        try:
            hold = self.bookings.place_hold(acc.username, sport, court_id, start_dt, slots)
        except Exception as e:
            self._error(str(e))
            return

        # checkout summary
        price = hold.price_usd
        print(f"\n{self._colorize_text('=== Checkout ===', Color.CYAN, True)}")
        print(f"Venue:          {self._colorize_text(self.venue_name, Color.YELLOW)}")
        print(f"Booking ID:     {self._colorize_text(hold.booking_id, Color.YELLOW)}")
        print(f"User:           {self._colorize_text(acc.username, Color.YELLOW)}")
        print(f"Sport:          {self._colorize_text(sport.title(), Color.YELLOW)}")
        print(f"Court:          {self._colorize_text(court_id, Color.YELLOW)}")
        print(f"Date/Start:     {self._colorize_text(self._fmt_dt(hold.start), Color.YELLOW)}")
        print(f"Duration:       {self._colorize_text(f'{dur_hours:.1f} hours', Color.YELLOW)}")
        print(f"Price (USD):    {self._colorize_text(f'${price:.2f}', Color.GREEN)}")
        print(f"Balance:        {self._colorize_text(f'${acc.balance_usd:.2f}', Color.GREEN)}")
        print(f"Hold expires:   {self._colorize_text(f'{self._fmt_dt(hold.hold_expires_at)} (in {int((hold.hold_expires_at - datetime.now()).total_seconds() // 60)} min)', Color.RED)}")

        pay = self._inp('Type "PAID" to confirm, or anything else to abort: ').strip().upper()
        if pay != "PAID":
            # abort and release
            ok = self.bookings.cancel_pending(acc.username, hold.booking_id)
            self._info("Not paid — aborting." if ok else "No change.")
            return

        success, msg, paid = self.bookings.confirm_payment(acc, hold.booking_id)
        if not success:
            self._error(msg)
            # if insufficient funds, keep pending for user to edit/cancel later
            if paid is not None:
                self._info("Your booking is still pending. You can cancel it from 'View my bookings'.")
            return

        # final confirmation
        print(f"\n{self._colorize_text('=== Payment received. Booking confirmed. ===', Color.GREEN, True)}")
        print(f"Venue:          {self._colorize_text(self.venue_name, Color.YELLOW)}")
        print(f"Booking ID:     {self._colorize_text(paid.booking_id, Color.YELLOW)}")
        print(f"User:           {self._colorize_text(acc.username, Color.YELLOW)}")
        print(f"Sport:          {self._colorize_text(sport.title(), Color.YELLOW)}")
        print(f"Court:          {self._colorize_text(paid.court_id, Color.YELLOW)}")
        print(f"Date/Start:     {self._colorize_text(self._fmt_dt(paid.start), Color.YELLOW)}")
        print(f"End:            {self._colorize_text(self._fmt_dt(paid.end_time()), Color.YELLOW)}")
        print(f"Duration:       {self._colorize_text(f'{dur_hours:.1f} hours', Color.YELLOW)}")
        print(f"Price (USD):    {self._colorize_text(f'${paid.price_usd:.2f}', Color.GREEN)}")
        print(f"New balance:    {self._colorize_text(f'${acc.balance_usd:.2f}', Color.GREEN)}")
        print(f"Booking status: {self._colorize_text('PAID', Color.GREEN, True)}")
        self._success("Returning to home...")
        # Auto-return to home per spec

    def flow_view_my_bookings(self):
        acc = self.current
        if not acc:
            return
        my = self.bookings.user_bookings(acc.username)
        if not my:
            self._info("\n(No bookings yet)")
            self._pause()
            return
        print(f"\n{self._colorize_text('== My bookings ==', Color.CYAN, True)}")
        for b in my:
            status_color = Color.GREEN if b.status == "PAID" else Color.YELLOW
            print(f"- {self._colorize_text(b.booking_id, Color.BLUE)} | {self._colorize_text(f'{b.sport.title()} {b.court_id}', Color.YELLOW)} | {self._fmt_dt(b.start)} → {self._fmt_dt(b.end_time())} | {self._colorize_text(b.status, status_color)} | {self._colorize_text(f'${b.price_usd:.2f}', Color.GREEN)}")

        # Allow cancel/edit for PENDING
        pending = [b for b in my if b.status == "PENDING"]
        if pending:
            print(f"\n{self._colorize_text('Pending actions:', Color.CYAN)}")
            print(f"{self._colorize_text('1) Cancel a pending booking', Color.BLUE)}")
            print(f"{self._colorize_text('2) (Re)attempt payment for a pending booking', Color.BLUE)}")
            print(f"{self._colorize_text('3) Back', Color.BLUE)}")
            ch = self._inp("Choose (1-3): ")
            if ch == "1":
                bid = self._inp("Enter Booking ID to cancel: ").strip()
                ok = self.bookings.cancel_pending(acc.username, bid)
                if ok:
                    self._success("Cancelled.")
                else:
                    self._error("Could not cancel (check ID/status).")
            elif ch == "2":
                bid = self._inp("Enter Booking ID to pay now: ").strip()
                conf = self._inp('Type "PAID" to confirm: ').strip().upper()
                if conf != "PAID":
                    self._info("Not paid — aborting.")
                else:
                    success, msg, b = self.bookings.confirm_payment(acc, bid)
                    if success:
                        self._success("Payment received. Booking now PAID.")
                    else:
                        self._error(msg)
        self._pause()

    def flow_view_account(self):
        acc = self.current
        if not acc:
            return
        print(f"\nAccount: {acc.username}")
        print(f"Role:    {acc.role}")
        print(f"Balance: ${acc.balance_usd:.2f}")
        self._pause()

    def flow_manage_bookings(self):
        acc = self.current
        if not acc or acc.role != "admin":
            return
        while True:
            print(f"\n{self._colorize_text('== Manage bookings ==', Color.MAGENTA, True)}")
            print(f"{self._colorize_text('1) View all bookings', Color.BLUE)}")
            print(f"{self._colorize_text('2) Remove a booking', Color.BLUE)}")
            print(f"{self._colorize_text('3) Back', Color.BLUE)}")
            ch = self._inp("Choose (1-3): ")
            if ch == "1":
                allb = self.bookings.all_bookings()
                if not allb:
                    self._info("(No bookings found)")
                else:
                    for b in allb:
                        status_color = Color.GREEN if b.status == "PAID" else Color.YELLOW
                        print(f"- {self._colorize_text(b.booking_id, Color.BLUE)} | {self._colorize_text(b.username, Color.CYAN)} | {self._colorize_text(f'{b.sport.title()} {b.court_id}', Color.YELLOW)} | {self._fmt_dt(b.start)} → {self._fmt_dt(b.end_time())} | {self._colorize_text(b.status, status_color)} | {self._colorize_text(f'${b.price_usd:.2f}', Color.GREEN)}")
                self._pause()
            elif ch == "2":
                bid = self._inp("Enter Booking ID to remove: ").strip()
                ok = self.bookings.admin_remove(bid)
                if ok:
                    self._success("Booking removed and court freed.")
                else:
                    self._error("Not found.")
                self._pause()
            elif ch == "3":
                return
            else:
                self._error("Invalid choice. Enter 1–3.")