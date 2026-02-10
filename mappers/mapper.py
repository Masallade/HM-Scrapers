from datetime import datetime
from decimal import Decimal
from datetime import date
from models.model import UpdateRecord

def percent_to_decimal(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value) / Decimal(100)


def map_json_to_update_record(
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
    lyAdr: Decimal | None,
    arrivals: int | None,
    departures: int | None,
    physicalCapacity: int | None,
    outOfOrder: int | None,
    onBook: int | None
):
    record_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    return UpdateRecord(
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
        ly_adr=lyAdr,
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
