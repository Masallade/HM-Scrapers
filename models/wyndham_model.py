from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

@dataclass
class WyndhamUpdateRecord:
    property_uuid: str

    record_timestamp: datetime
    record_date: date
    day_of_week: str

    algo_output_price: Decimal | None 
    standard_price: Decimal
    standard_previous_price: Decimal
    standard_price_change: Decimal
    competitor_set_avg_price: Decimal

    occupancy: Decimal
    forecasted_occupancy: Decimal
    updated_by_rm: bool

    revenue_per_room: Optional[Decimal]

    ly_occupancy: Decimal
    ly_adr: Decimal
    on_the_books_occ: Decimal

    arrivals_forecast: int
    departure_forecast: int

    total_rooms: Optional[int]
    ooo: Optional[int]          # Out Of Order rooms
    otb_rooms: Optional[int]    # On The Books rooms
    avl_rooms: Optional[int]    # Available rooms

    created_at: Optional[datetime]
    updated_at: Optional[datetime]
