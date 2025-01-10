from datetime import datetime, timedelta

def format_date(date: datetime) -> str:
    """Format date to YYYYMMDD for ESPN API."""
    return date.strftime("%Y%m%d")

def find_next_game_date(current_date: datetime, max_days: int = 14) -> datetime:
    """Find the next date with games within max_days."""
    for i in range(max_days):
        next_date = current_date + timedelta(days=i)
        # Logic to check if date has games
        yield next_date
