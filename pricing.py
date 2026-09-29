from datetime import datetime
import math

FMT = "%Y-%m-%d %H:%M:%S"   # cùng định dạng với lúc ghi vào DB

def calculate_fee(time_in, time_out):
    if isinstance(time_in, str):
        time_in = datetime.strptime(time_in, FMT)
    if isinstance(time_out, str):
        time_out = datetime.strptime(time_out, FMT)

    duration = (time_out - time_in).total_seconds() / 3600  

    if duration < 0:
        raise ValueError("time_out sớm hơn time_in")

    if duration <= 4:
        return 5000
    if duration <=8:
        return 10000
    if duration < 24:
        return 20000
    else:
        days = math.floor(duration / 24)
        hours_remaining = duration % 24
        if hours_remaining <= 4:
            return days * 30000 + 7000 
        if hours_remaining <= 8:
            return days * 30000 + 12000 
        else:
            return days * 30000 + 20000


