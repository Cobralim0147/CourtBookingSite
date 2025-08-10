from typing import Dict, List, Tuple
from datetime import datetime, date, time
from enum import Enum

class Color(Enum):
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class AvailabilityDisplayService:
    """Service for displaying court availability in a visual grid format."""
    
    def __init__(self):
        self.slot_minutes = 30
        self.slots_per_hour = 2
        self.hours_per_day = 24
        self.total_slots = self.hours_per_day * self.slots_per_hour
    
    def _colorize_text(self, text: str, color: Color, bold: bool = False) -> str:
        """Apply color formatting to text."""
        prefix = color.value
        if bold:
            prefix = Color.BOLD.value + prefix
        return f"{prefix}{text}{Color.RESET.value}"
    
    def _format_time_slot(self, slot_time: datetime) -> str:
        """Format time slot for display."""
        return slot_time.strftime("%H:%M")
    
    def _get_availability_symbol(self, is_available: bool) -> str:
        """Get colored symbol for availability status."""
        if is_available:
            return self._colorize_text("█", Color.GREEN)  # Green block for available
        else:
            return self._colorize_text("█", Color.RED)    # Red block for not available
    
    def display_compact_grid(self, sport_name: str, target_date: date, 
                           availability_grid: Dict[str, List[Tuple[datetime, bool]]]) -> None:
        """Display a compact grid showing availability for all courts."""
        print(f"\n{self._colorize_text('Availability Grid', Color.CYAN, True)} for {self._colorize_text(sport_name.title(), Color.YELLOW, True)} on {self._colorize_text(target_date.isoformat(), Color.YELLOW, True)}")
        print(f"{self._colorize_text('Green', Color.GREEN)} = Available, {self._colorize_text('Red', Color.RED)} = Not Available")
        print("=" * 120)
        
        if not availability_grid:
            print("No courts configured for this sport.")
            return
        
        # Get time slots from first court (all courts have same time structure)
        first_court = next(iter(availability_grid.keys()))
        time_slots = [slot_time for slot_time, _ in availability_grid[first_court]]
        
        # Display header with time slots (every hour for better readability)
        print(f"{'Court':<6}", end="")
        for i, slot_time in enumerate(time_slots):
            if i % 2 == 0:  # Every hour (2 slots of 30 minutes)
                hour = slot_time.hour
                print(f"{hour:02d}:00 {hour:02d}:30", end=" ")
        print()
        
        # Display availability for each court
        for court_id, slots in availability_grid.items():
            print(f"{court_id:<6}", end="")
            for i, (slot_time, is_available) in enumerate(slots):
                if i % 2 == 0:  # Display both 30-minute slots for each hour
                    # Get current slot (00 minutes)
                    symbol_00 = self._get_availability_symbol(is_available)
                    
                    # Get next slot (30 minutes) if it exists
                    if i + 1 < len(slots):
                        _, is_available_30 = slots[i + 1]
                        symbol_30 = self._get_availability_symbol(is_available_30)
                    else:
                        symbol_30 = " "
                    
                    print(f"  {symbol_00}   {symbol_30} ", end=" ")
            print()
    
    def display_detailed_grid(self, sport_name: str, target_date: date, 
                            availability_grid: Dict[str, List[Tuple[datetime, bool]]]) -> None:
        """Display a detailed grid showing all 30-minute time slots."""
        print(f"\n{self._colorize_text('Detailed Availability Grid', Color.CYAN, True)} for {self._colorize_text(sport_name.title(), Color.YELLOW, True)} on {self._colorize_text(target_date.isoformat(), Color.YELLOW, True)}")
        print(f"{self._colorize_text('Green', Color.GREEN)} = Available, {self._colorize_text('Red', Color.RED)} = Not Available")
        print("=" * 130)
        
        if not availability_grid:
            print("No courts configured for this sport.")
            return
        
        # Get time slots and courts
        courts = list(availability_grid.keys())
        first_court = courts[0]
        time_slots = [slot_time for slot_time, _ in availability_grid[first_court]]
        
        # Display in 4-hour blocks for readability
        for start_hour in range(0, 24, 4):
            end_hour = min(start_hour + 4, 24)
            print(f"\n{self._colorize_text(f'Time Block: {start_hour:02d}:00 - {end_hour:02d}:00', Color.BLUE, True)}")
            print("-" * 100)
            
            # Header with all 30-minute slots in this 4-hour block
            print(f"{'Court':<8}", end="")
            start_slot = start_hour * 2  # 2 slots per hour
            end_slot = min(end_hour * 2, len(time_slots))
            
            for slot_idx in range(start_slot, end_slot):
                if slot_idx < len(time_slots):
                    time_label = self._format_time_slot(time_slots[slot_idx])
                    print(f"{time_label:>5}", end=" ")
            print()
            
            # Display availability for each court in this time block
            for court_id in courts:
                print(f"{court_id:<8}", end="")
                slots = availability_grid[court_id]
                
                for slot_idx in range(start_slot, end_slot):
                    if slot_idx < len(slots):
                        _, is_available = slots[slot_idx]
                        symbol = self._get_availability_symbol(is_available)
                        print(f"  {symbol:>2}", end=" ")
                    else:
                        print("     ", end=" ")
                print()
    
    def display_available_slots_list(self, sport_name: str, target_date: date, 
                                   availability_grid: Dict[str, List[Tuple[datetime, bool]]]) -> None:
        """Display a list of available time slots for each court."""
        print(f"\n{self._colorize_text('Available Slots', Color.CYAN, True)} for {self._colorize_text(sport_name.title(), Color.YELLOW, True)} on {self._colorize_text(target_date.isoformat(), Color.YELLOW, True)}")
        print("=" * 80)
        
        if not availability_grid:
            print("No courts configured for this sport.")
            return
        
        for court_id, slots in availability_grid.items():
            available_slots = []
            for slot_time, is_available in slots:
                if is_available:
                    available_slots.append(self._format_time_slot(slot_time))
            
            print(f"\n{self._colorize_text(court_id, Color.YELLOW, True)}:")
            if available_slots:
                # Group consecutive slots for better readability
                slot_groups = self._group_consecutive_slots(available_slots)
                for group in slot_groups:
                    if len(group) == 1:
                        print(f"  {self._colorize_text(group[0], Color.GREEN)}")
                    else:
                        print(f"  {self._colorize_text(f'{group[0]} - {group[-1]}', Color.GREEN)}")
            else:
                print(f"  {self._colorize_text('Fully booked', Color.RED)}")
    
    def _group_consecutive_slots(self, time_slots: List[str]) -> List[List[str]]:
        """Group consecutive time slots together."""
        if not time_slots:
            return []
        
        groups = []
        current_group = [time_slots[0]]
        
        for i in range(1, len(time_slots)):
            # Convert to minutes for comparison
            prev_minutes = self._time_to_minutes(time_slots[i-1])
            curr_minutes = self._time_to_minutes(time_slots[i])
            
            if curr_minutes - prev_minutes == 30:  # Consecutive 30-minute slots
                current_group.append(time_slots[i])
            else:
                groups.append(current_group)
                current_group = [time_slots[i]]
        
        groups.append(current_group)
        return groups
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string (HH:MM) to minutes since midnight."""
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    
    def display_legend(self) -> None:
        """Display legend for the grid symbols."""
        print(f"\n{self._colorize_text('Legend:', Color.CYAN, True)}")
        print(f"  {self._get_availability_symbol(True)} = {self._colorize_text('Available for booking', Color.GREEN)}")
        print(f"  {self._get_availability_symbol(False)} = {self._colorize_text('Not available (booked/held)', Color.RED)}")
        print("  Each slot = 30 minutes")
    
    def display_full_30min_grid(self, sport_name: str, target_date: date, 
                              availability_grid: Dict[str, List[Tuple[datetime, bool]]]) -> None:
        """Display a complete grid showing every 30-minute slot."""
        print(f"\n{self._colorize_text('Complete 30-Minute Grid', Color.CYAN, True)} for {self._colorize_text(sport_name.title(), Color.YELLOW, True)} on {self._colorize_text(target_date.isoformat(), Color.YELLOW, True)}")
        print(f"{self._colorize_text('Green', Color.GREEN)} = Available, {self._colorize_text('Red', Color.RED)} = Not Available")
        print("=" * 150)
        
        if not availability_grid:
            print("No courts configured for this sport.")
            return
        
        # Get time slots and courts
        courts = list(availability_grid.keys())
        first_court = courts[0]
        time_slots = [slot_time for slot_time, _ in availability_grid[first_court]]
        
        # Display header with all time slots
        print(f"{'Court':<6}", end="")
        for slot_time in time_slots:
            time_label = self._format_time_slot(slot_time)
            print(f"{time_label:>5}", end="|")
        print()
        
        # Display availability for each court
        for court_id in courts:
            print(f"{court_id:<6}", end="")
            slots = availability_grid[court_id]
            
            for _, is_available in slots:
                symbol = self._get_availability_symbol(is_available)
                print(f"  {symbol:>2}", end="")
            print()
