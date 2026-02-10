from datetime import datetime
from decimal import Decimal
from datetime import date
from models.wyndham_model import WyndhamUpdateRecord

def percent_to_decimal(value: int | None) -> Decimal | None:
    """Convert percentage integer to decimal (e.g., 20 -> 0.20)"""
    if value is None:
        return None
    return Decimal(value) / Decimal(100)


def map_wyndham_json_to_update_record(
    property_uuid: str, 
    date_str: str,
    price_value: Decimal | None,
    previousRate_value: Decimal | None,
    priceDiff_value: Decimal | None,
    compSetAvg: Decimal | None,
    onBookPercent: int | None,
    forecastPercent: int | None,
    updated_by_rm: bool,
    lyBookingPercent: int | None,
    lyRevenue: Decimal | None,
    arrivals: int | None,
    departures: int | None,
    physicalCapacity: int | None,
    outOfOrder: int | None,
    onBook: int | None
):
    """
    Map Wyndham JSON data to WyndhamUpdateRecord model.
    
    Args:
        property_uuid: Property UUID from JSON
        date_str: Date string in YYYY-MM-DD format
        price_value: Current price
        previousRate_value: Previous rate
        priceDiff_value: Price difference
        compSetAvg: Competitor set average price
        onBookPercent: On the books percentage (0-100)
        forecastPercent: Forecast percentage (0-100)
        updated_by_rm: Whether updated by revenue manager
        lyBookingPercent: Last year booking percentage (0-100)
        lyRevenue: Last year revenue
        arrivals: Arrivals forecast
        departures: Departures forecast
        physicalCapacity: Total rooms
        outOfOrder: Out of order rooms
        onBook: On the books rooms
    
    Returns:
        WyndhamUpdateRecord object
    """
    record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Calculate LY ADR from LY Revenue and LY Occupancy
    ly_adr = None
    if lyRevenue is not None and lyBookingPercent is not None and physicalCapacity is not None:
        ly_occupancy_decimal = Decimal(lyBookingPercent) / Decimal(100)
        ly_occupied_rooms = ly_occupancy_decimal * Decimal(physicalCapacity)
        if ly_occupied_rooms > 0:
            ly_adr = lyRevenue / ly_occupied_rooms

    return WyndhamUpdateRecord(
        property_uuid=property_uuid,

        record_timestamp=datetime.utcnow(),
        record_date=record_date,
        day_of_week=record_date.strftime("%A"),

        algo_output_price=None,

        standard_price=price_value,
        standard_previous_price=previousRate_value,
        standard_price_change=priceDiff_value,
        competitor_set_avg_price=compSetAvg,

        occupancy=percent_to_decimal(onBookPercent),
        forecasted_occupancy=percent_to_decimal(forecastPercent),
        updated_by_rm=updated_by_rm,

        revenue_per_room=None,

        ly_occupancy=percent_to_decimal(lyBookingPercent),
        ly_adr=ly_adr,
        on_the_books_occ=percent_to_decimal(onBookPercent),

        arrivals_forecast=arrivals,
        departure_forecast=departures,

        total_rooms=physicalCapacity,
        ooo=outOfOrder,
        otb_rooms=onBook,
        avl_rooms=(physicalCapacity - outOfOrder - onBook)
        if physicalCapacity is not None and outOfOrder is not None and onBook is not None
        else None,

        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
