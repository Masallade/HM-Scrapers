import json
import sys
from pathlib import Path
from decimal import Decimal
from typing import List

# Add parent directory to path to allow imports from models and mappers
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.model import UpdateRecord
from mappers.mapper import map_json_to_update_record

def load_update_records_from_json(file_path: str) -> List[UpdateRecord]:
    records: List[UpdateRecord] = []

    with open(file_path, "r") as f:
        data = json.load(f)

    for property_obj in data:
        property_uuid = property_obj["id"]

        for date_obj in property_obj.get("dates", []):

            record = map_json_to_update_record(
                property_uuid=property_uuid,
                date_str=date_obj["date"],

                price_value=Decimal(str(date_obj["price"]["value"]))
                if date_obj.get("price") else None,

                previousRate_value=Decimal(str(date_obj["previousRate"]["value"]))
                if date_obj.get("previousLrv") is not None else None,

                priceDiff_value=Decimal(str(date_obj["priceDiff"]["value"]))
                if date_obj.get("priceDiff") is not None else None,

                compSetAvg=Decimal(str(date_obj["compSetAvg"]["value"]))
                if date_obj.get("compSetAvg") is not None else None,

                onBookPercent=int(str(date_obj["onBookPercent"]))
                if date_obj.get("onBookPercent") is not None else None,

                forecastPercent=int(str(date_obj["forecastPercent"]))
                if date_obj.get("forecastPercent") is not None else None,

                updated_by_rm=False,

                lyBookingPercent=int(str(date_obj["lyBookingPercent"]))
                if date_obj.get("lyBookingPercent") is not None else None,

                lyAdr=Decimal(str(date_obj["lyAdr"]))
                if date_obj.get("lyAdr") is not None else None,

                arrivals=date_obj.get("arrivals"),
                departures=date_obj.get("departures"),

                physicalCapacity=date_obj.get("physicalCapacity"),
                outOfOrder=date_obj.get("outOfOrder"),
                onBook=date_obj.get("onBook")
            )

            records.append(record)

    return records


if __name__ == "__main__":
    records = load_update_records_from_json("new_record_json.json")

    print(f"Total records loaded: {len(records)}\n")

    for record in records:
        print(record)
