"""
Data models for rowers and boats in the rowing lineup setter.
"""

from enum import Enum
from typing import List, Optional
from dataclasses import dataclass


class Side(Enum):
    """Side preference for rowing"""
    PORT = "port"
    STARBOARD = "starboard"
    BOTH = "both"


class Experience(Enum):
    """Experience level of rower"""
    NOVICE = "novice"
    VARSITY = "varsity"


def convert_6k_to_2k(time_6k: float) -> float:
    """
    Convert a 6k erg time to an estimated 2k time using Paul's Law.
    Paul's Law states that for every doubling of distance, the 500m split increases by 5 seconds.
    6k is 3 times 2k. We can't directly apply the doubling rule.
    A common approximation is that the 2k split is about 10-12 seconds faster than the 6k split.
    Let's use a factor to estimate.
    (6000/2000)^(log2(1 + 5/split_500))
    A simpler and more common estimation is to find the 500m split for the 6k, subtract a value (e.g., 8-12 seconds),
    and then calculate the 2k time from that new split.

    Let's take the 6k split, subtract 10 seconds, and calculate the 2k time.
    """
    split_6k_500m = time_6k / 12
    split_2k_500m_estimated = split_6k_500m - 10
    time_2k_estimated = split_2k_500m_estimated * 4
    return time_2k_estimated


@dataclass
class Rower:
    """Represents a rower with their attributes"""
    name: str
    erg_score: float  # 2k erg time in seconds
    side_preference: Side
    experience: Experience
    attendance_history: List[str]  # List of "yes" or "no"
    days_since_boated: int

    def __post_init__(self):
        if isinstance(self.side_preference, str):
            self.side_preference = Side(self.side_preference)
        if isinstance(self.experience, str):
            self.experience = Experience(self.experience)

    @property
    def attendance_score(self) -> float:
        """Calculates an attendance score. Higher is better."""
        if not self.attendance_history:
            return 0.0
        return self.attendance_history.count("yes") / len(self.attendance_history)

    @property
    def fitness_score(self) -> float:
        """Calculate a fitness score for the rower (lower is better)"""
        # Base score on erg time
        score = self.erg_score

        # Add a penalty if the rower was absent yesterday.
        if self.attendance_history and self.attendance_history[-1] == "no":
            score += 500.0  # Significant penalty for missing practice

        # Adjust score based on how long it's been since they were boated.
        # Add a bonus for each day they've waited.
        # The larger the days_since_boated, the more we reduce the score.
        score -= self.days_since_boated * 5  # 5 seconds bonus per day waited

        return score

    def to_dict(self) -> dict:
        """Convert rower to dictionary"""
        return {
            'name': self.name,
            'erg_score': self.erg_score,
            'side_preference': self.side_preference.value,
            'experience': self.experience.value,
            'attendance_history': self.attendance_history,
            'days_since_boated': self.days_since_boated
        }

    @classmethod
    def from_dict(cls, data: dict, convert_6k: bool = False) -> 'Rower':
        """Create rower from dictionary"""
        erg_score = data['erg_score']
        if convert_6k:
            erg_score = convert_6k_to_2k(erg_score)
        
        return cls(
            name=data['name'],
            erg_score=erg_score,
            side_preference=Side(data['side_preference']),
            experience=Experience(data['experience']),
            attendance_history=data['attendance_history'],
            days_since_boated=data['days_since_boated']
        )


@dataclass
class Seat:
    """Represents a seat in a boat"""
    position: int  # 1-8 for eights, 1-4 for fours
    side: Side  # Port or starboard
    rower: Optional[Rower] = None


class Boat:
    """Represents a rowing boat lineup"""
    
    def __init__(self, boat_type: int):
        """
        Initialize a boat
        
        Args:
            boat_type: 4 for fours, 8 for eights
        """
        if boat_type not in [4, 8]:
            raise ValueError("Boat type must be 4 or 8")
        
        self.boat_type = boat_type
        self.seats: List[Seat] = []
        
        # Create seats with alternating sides
        # Standard rowing: port/starboard alternates
        # For eights: stroke side is typically port
        for i in range(1, boat_type + 1):
            if boat_type == 8:
                # Eights: 1,3,5,7 are starboard, 2,4,6,8 are port
                side = Side.PORT if i % 2 == 0 else Side.STARBOARD
            else:
                # Fours: 1,3 are starboard, 2,4 are port
                side = Side.PORT if i % 2 == 0 else Side.STARBOARD
            self.seats.append(Seat(position=i, side=side))
    
    def assign_rower(self, position: int, rower: Rower):
        """Assign a rower to a position"""
        if position < 1 or position > self.boat_type:
            raise ValueError(f"Position must be between 1 and {self.boat_type}")
        self.seats[position - 1].rower = rower
    
    def get_rower(self, position: int) -> Optional[Rower]:
        """Get the rower at a position"""
        if position < 1 or position > self.boat_type:
            return None
        return self.seats[position - 1].rower
    
    def is_full(self) -> bool:
        """Check if all seats are filled"""
        return all(seat.rower is not None for seat in self.seats)
    
    def get_lineup(self) -> List[Optional[Rower]]:
        """Get the current lineup as a list of rowers"""
        return [seat.rower for seat in self.seats]
    
    def clear(self):
        """Clear all seat assignments"""
        for seat in self.seats:
            seat.rower = None
    
    def __str__(self) -> str:
        """String representation of the boat"""
        result = [f"Boat ({self.boat_type}):"]
        for seat in self.seats:
            rower_name = seat.rower.name if seat.rower else "Empty"
            result.append(f"  Seat {seat.position} ({seat.side.value}): {rower_name}")
        return "\n".join(result)
