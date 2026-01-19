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


@dataclass
class Rower:
    """Represents a rower with their attributes"""
    name: str
    erg_score: float  # 2k erg time in seconds
    side_preference: Side
    experience: Experience
    attendance: float  # Attendance percentage (0.0 to 1.0)
    
    def __post_init__(self):
        if isinstance(self.side_preference, str):
            self.side_preference = Side(self.side_preference)
        if isinstance(self.experience, str):
            self.experience = Experience(self.experience)
    
    @property
    def fitness_score(self) -> float:
        """Calculate a fitness score for the rower (lower is better)"""
        # Lower erg time is better, weighted with attendance
        return self.erg_score / self.attendance if self.attendance > 0 else float('inf')
    
    def to_dict(self) -> dict:
        """Convert rower to dictionary"""
        return {
            'name': self.name,
            'erg_score': self.erg_score,
            'side_preference': self.side_preference.value,
            'experience': self.experience.value,
            'attendance': self.attendance
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Rower':
        """Create rower from dictionary"""
        return cls(
            name=data['name'],
            erg_score=data['erg_score'],
            side_preference=Side(data['side_preference']),
            experience=Experience(data['experience']),
            attendance=data['attendance']
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
