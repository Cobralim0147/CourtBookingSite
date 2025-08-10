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
from display_service import AvailabilityDisplayService

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
            h, m = map(int, s.split(":"))
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
            print("\n=== Cobra's ZooKeeping Sport Center ===")
            print("1) Login as User")
            print("2) Login as Admin")
            print("3) View Sports / About")
            print("4) Exit")
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
                print("Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Enter 1–4.")

    def login_flow(self, role: Role):
        print(f"\n== Login ({role.upper()}) ==")
        username = self._inp("Username: ")
        password = getpass.getpass("Password: ")
        
        acc = self.auth.login(username, password, role)
        if not acc:
            print("Login error: invalid name or password.")
            self._pause()
            self.current = None
        else:
            print(f"Login successful! Welcome, {username}")
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
            print(f"\n== User Menu ({acc.username}, balance ${acc.balance_usd:.2f}) ==")
            print("1) Search availability")
            print("2) Book a court")
            print("3) View my bookings")
            print("4) View account")
            print("5) Logout")
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
                print("Logging out...")
                self.current = None
                return
            else:
                print("Invalid choice. Enter 1–5.")

    # ---- admin menus ----
    def menu_admin(self):
        while True:
            acc = self.current
            assert acc is not None and acc.role == "admin"
            print(f"\n== Admin Menu ({acc.username}) ==")
            print("1) Search availability")
            print("2) Book a court")
            print("3) Manage bookings")
            print("4) View account")
            print("5) Logout")
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
                print("Logging out...")
                self.current = None
                return
            else:
                print("Invalid choice. Enter 1–5.")

    # ---- flows ----

    def _choose_sport(self) -> Optional[str]:
        sports = self.inventory.list_sports()
        print("\nAvailable sports:")
        for i, s in enumerate(sports, 1):
            print(f"{i}) {s.title()}")
        idx = self._inp("Choose sport #: ")
        try:
            sel = sports[int(idx) - 1]
            return sel
        except Exception:
            print("Invalid selection.")
            return None

    def flow_search(self):
        sport = self._choose_sport()
        if not sport:
            return
        d_str = self._inp("Enter date (YYYY-MM-DD): ")
        d = self._parse_date(d_str)
        if not d:
            print("Invalid date.")
            return
        
        # Get availability grid
        grid = self.bookings.availability_grid(sport, d)
        if not grid:
            print("No courts configured for this sport.")
            return

        # Display options
        print("\nAvailability Display Options:")
        print("1) Compact Grid View")
        print("2) Detailed Grid View") 
        print("3) Available Slots List")
        print("4) All Views")
        
        view_choice = self._inp("Choose display format (1-4): ").strip()
        
        if view_choice == "1":
            self.display_service.display_compact_grid(sport, d, grid)
        elif view_choice == "2":
            self.display_service.display_detailed_grid(sport, d, grid)
        elif view_choice == "3":
            self.display_service.display_available_slots_list(sport, d, grid)
        elif view_choice == "4":
            self.display_service.display_compact_grid(sport, d, grid)
            self.display_service.display_detailed_grid(sport, d, grid)
            self.display_service.display_available_slots_list(sport, d, grid)
        else:
            # Default to compact view
            self.display_service.display_compact_grid(sport, d, grid)
        
        self.display_service.display_legend()

        go = self._inp("\nPress B to start booking now for this sport, or Enter to return: ").strip().upper()
        if go == "B":
            self.flow_book(pref_sport=sport)

    def flow_book(self, pref_sport: Optional[str] = None):
        acc = self.current
        if not acc:
            print("Please login first.")
            return
        sport = pref_sport or self._choose_sport()
        if not sport:
            return
        d_str = self._inp("Enter date (YYYY-MM-DD): ")
        d = self._parse_date(d_str)
        if not d:
            print("Invalid date.")
            return
        t_str = self._inp("Enter start time (HH:MM, 24h, minutes must be 00 or 30): ")
        t = self._parse_time(t_str)
        if not t:
            print("Invalid time (use HH:MM, minutes 00 or 30).")
            return
        try:
            dur_hours = float(self._inp("Enter duration in hours (e.g., 1.0, 1.5, 2): "))
            if dur_hours <= 0:
                raise ValueError
        except Exception:
            print("Invalid duration.")
            return
        # convert to 30-min slots
        slots = int(dur_hours * 2)
        if abs(dur_hours - (slots * 0.5)) > 1e-9:
            print("Duration must be in increments of 0.5 hours.")
            return

        start_dt = datetime.combine(d, t)
        avail_courts = self.bookings.courts_available_for_span(sport, start_dt, slots)
        if not avail_courts:
            print("Fully booked for the selected period.")
            return

        print("\nCourts available for the entire span:")
        for i, c in enumerate(avail_courts, 1):
            print(f"{i}) {c}")
        idx = self._inp("Choose court #: ")
        try:
            court_id = avail_courts[int(idx) - 1]
        except Exception:
            print("Invalid selection.")
            return

        # place hold
        try:
            hold = self.bookings.place_hold(acc.username, sport, court_id, start_dt, slots)
        except Exception as e:
            print(str(e))
            return

        # checkout summary
        price = hold.price_usd
        print("\n=== Checkout ===")
        print(f"Venue:          {self.venue_name}")
        print(f"Booking ID:     {hold.booking_id}")
        print(f"User:           {acc.username}")
        print(f"Sport:          {sport.title()}")
        print(f"Court:          {court_id}")
        print(f"Date/Start:     {self._fmt_dt(hold.start)}")
        print(f"Duration:       {dur_hours:.1f} hours")
        print(f"Price (USD):    ${price:.2f}")
        print(f"Balance:        ${acc.balance_usd:.2f}")
        print(f"Hold expires:   {self._fmt_dt(hold.hold_expires_at)} (in {int((hold.hold_expires_at - datetime.now()).total_seconds() // 60)} min)")

        pay = self._inp('Type "PAID" to confirm, or anything else to abort: ').strip().upper()
        if pay != "PAID":
            # abort and release
            ok = self.bookings.cancel_pending(acc.username, hold.booking_id)
            print("Not paid — aborting." if ok else "No change.")
            return

        success, msg, paid = self.bookings.confirm_payment(acc, hold.booking_id)
        if not success:
            print(msg)
            # if insufficient funds, keep pending for user to edit/cancel later
            if paid is not None:
                print("Your booking is still pending. You can cancel it from 'View my bookings'.")
            return

        # final confirmation
        print("\n=== Payment received. Booking confirmed. ===")
        print(f"Venue:          {self.venue_name}")
        print(f"Booking ID:     {paid.booking_id}")
        print(f"User:           {acc.username}")
        print(f"Sport:          {sport.title()}")
        print(f"Court:          {paid.court_id}")
        print(f"Date/Start:     {self._fmt_dt(paid.start)}")
        print(f"End:            {self._fmt_dt(paid.end_time())}")
        print(f"Duration:       {dur_hours:.1f} hours")
        print(f"Price (USD):    ${paid.price_usd:.2f}")
        print(f"New balance:    ${acc.balance_usd:.2f}")
        print("Booking status: PAID")
        print("Returning to home...")
        # Auto-return to home per spec

    def flow_view_my_bookings(self):
        acc = self.current
        if not acc:
            return
        my = self.bookings.user_bookings(acc.username)
        if not my:
            print("\n(No bookings yet)")
            self._pause()
            return
        print("\n== My bookings ==")
        for b in my:
            print(f"- {b.booking_id} | {b.sport.title()} {b.court_id} | {self._fmt_dt(b.start)} → {self._fmt_dt(b.end_time())} | {b.status} | ${b.price_usd:.2f}")

        # Allow cancel/edit for PENDING
        pending = [b for b in my if b.status == "PENDING"]
        if pending:
            print("\nPending actions:")
            print("1) Cancel a pending booking")
            print("2) (Re)attempt payment for a pending booking")
            print("3) Back")
            ch = self._inp("Choose (1-3): ")
            if ch == "1":
                bid = self._inp("Enter Booking ID to cancel: ").strip()
                ok = self.bookings.cancel_pending(acc.username, bid)
                print("Cancelled." if ok else "Could not cancel (check ID/status).")
            elif ch == "2":
                bid = self._inp("Enter Booking ID to pay now: ").strip()
                conf = self._inp('Type "PAID" to confirm: ').strip().upper()
                if conf != "PAID":
                    print("Not paid — aborting.")
                else:
                    success, msg, b = self.bookings.confirm_payment(acc, bid)
                    if success:
                        print("Payment received. Booking now PAID.")
                    else:
                        print(msg)
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
            print("\n== Manage bookings ==")
            print("1) View all bookings")
            print("2) Remove a booking")
            print("3) Back")
            ch = self._inp("Choose (1-3): ")
            if ch == "1":
                allb = self.bookings.all_bookings()
                if not allb:
                    print("(No bookings found)")
                else:
                    for b in allb:
                        print(f"- {b.booking_id} | {b.username} | {b.sport.title()} {b.court_id} | {self._fmt_dt(b.start)} → {self._fmt_dt(b.end_time())} | {b.status} | ${b.price_usd:.2f}")
                self._pause()
            elif ch == "2":
                bid = self._inp("Enter Booking ID to remove: ").strip()
                ok = self.bookings.admin_remove(bid)
                print("Booking removed and court freed." if ok else "Not found.")
                self._pause()
            elif ch == "3":
                return
            else:
                print("Invalid choice. Enter 1–3.")