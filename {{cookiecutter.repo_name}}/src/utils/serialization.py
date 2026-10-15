from datetime import date, datetime

import pandas as pd


def convert_timestamps(obj):
    if isinstance(obj, dict):
        for key in obj:
            obj[key] = convert_timestamps(obj[key])
    elif isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    return obj
