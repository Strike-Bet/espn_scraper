from datetime import datetime, timedelta
from typing import Dict
import os
from utils.auth_service import AuthService

def format_date(date: datetime) -> str:
    """Format date to YYYYMMDD for ESPN API."""
    return date.strftime("%Y%m%d")

def find_next_game_date(current_date: datetime, max_days: int = 14) -> datetime:
    """Find the next date with games within max_days."""
    for i in range(max_days):
        next_date = current_date + timedelta(days=i)
        # Logic to check if date has games
        yield next_date



def get_hasura_headers():
    # Replace this with however you generate or fetch your headers
    print("Auth service token", AuthService().get_token())
    return {
        "Authorization": f"Bearer {AuthService().get_token()}",
        "Content-Type": "application/json",
        "x-hasura-admin-secret": "DHieJhzOpml0wBIbEZC5mvsDdSKMnyMC4b8Kx04p0adKUO0zd2e2LSganKK6CRAb"
    }


def parse_shot_stats(stat_string: str, get_made: bool = True) -> int:
    """
    Parse shot statistics in format "X-Y" where X is made and Y is attempted.
    
    Args:
        stat_string: String in format "X-Y"
        get_made: If True returns makes, if False returns attempts
    
    Returns:
        Integer value of makes or attempts
    """
    try:
        made, attempted = stat_string.split("-")
        return int(made) if get_made else int(attempted)
    except (ValueError, AttributeError):
        return 0
    

def calculate_fantasy_score(player_stats: dict) -> int:
    """
    Calculate ESPN fantasy basketball score based on player stats.
    
    Scoring system:
    - 3PM: 1 point
    - FGA: -1 point
    - FGM: 2 points
    - FTA: -1 point
    - FTM: 1 point
    - REB: 1 point
    - AST: 2 points
    - STL: 4 points
    - BLK: 4 points
    - TOV: -2 points
    """
    score = 0
    
    # Handle field goals (including three pointers)
    fg_made = parse_shot_stats(player_stats['FG'], True)
    fg_attempts = parse_shot_stats(player_stats['FG'], False)
    three_made = parse_shot_stats(player_stats['3PT'], True)
    
    # FGM (2 points) and FGA (-1 point)
    score += (fg_made * 2) - fg_attempts
    
    # Additional point for each 3PM
    score += three_made
    
    # Handle free throws
    ft_made = parse_shot_stats(player_stats['FT'], True)
    ft_attempts = parse_shot_stats(player_stats['FT'], False)
    score += ft_made - ft_attempts  # FTM (1 point) and FTA (-1 point)
    
    # Handle other stats
    score += player_stats['REB']  # 1 point per rebound
    score += player_stats['AST'] * 2  # 2 points per assist
    score += player_stats['STL'] * 4  # 4 points per steal
    score += player_stats['BLK'] * 4  # 4 points per block
    score += player_stats['TO'] * -2  # -2 points per turnover
    
    return score

# Updated STAT_MAP
NBA_STAT_MAP = {
    "Minutes": "MIN",
    "Field Goals Made": {"key": "FG", "made": True},
    "FG Made": {"key": "FG", "made": True},
    "FG Attempted": {"key": "FG", "made": False},
    "3-PT Made": {"key": "3PT", "made": True},
    "3PT Made": {"key": "3PT", "made": True},
    "3-PT Attempted": {"key": "3PT", "made": False},
    "3PT Attempted": {"key": "3PT", "made": False},
    "FT Made": {"key": "FT", "made": True},
    "Free Throws Made": {"key": "FT", "made": True},
    "FT Attempted": {"key": "FT", "made": False},
    "Offensive Rebounds": "OREB",
    "Defensive Rebounds": "DREB",
    "Rebounds": "REB",
    "Assists": "AST",
    "Steals": "STL",
    "Blocked Shots": "BLK",
    "Turnovers": "TO",
    "Fouls": "PF",
    "+/-": "+/-",
    "Points": "PTS",
    "Pts": "PTS",
    "Rebs": "REB",
    "Asts": "AST",
    "Stls": "STL",
    "Blks": "BLK",
    "TOs": "TO",
    "Fls": "PF",
    # Combos
    "Pts+Rebs": ["PTS", "REB"],
    "Pts+Asts": ["PTS", "AST"],
    "Rebs+Asts": ["REB", "AST"],
    "Pts+Rebs+Asts": ["PTS", "REB", "AST"],
    "Blks+Stls": ["BLK", "STL"],
    # Fantasy Score
    "Fantasy Score": {"key": "fantasy", "calculator": calculate_fantasy_score}
}


NFL_STAT_MAP = {
    # Passing
    "Pass Yards": "passingYards",
    "Pass TDs": "passingTouchdowns",
    "Pass Attempts": "passingAttempts",
    "Pass Completions": "completions",
    "INT": "interceptions",

    # Rushing
    "Rush Yards": "rushingYards",
    "Rush Yards in First 5 Attempts": "rushingYardsFirst5Attempts",
    "Rush TDs": "rushingTouchdowns",
    "Rush Attempts": "rushingAttempts",
    "Longest Rush": "longRushing",

    # Receiving
    "Receptions": "receptions",
    "Receiving Yards": "receivingYards",
    "Longest Reception": "longReception",

    # Combos
    "Pass+Rush Yds": "passingYards+rushingYards",
    "Rush+Rec Yds": "rushingYards+receivingYards",
    "Rush+Rec TDs": "rushingTouchdowns+receivingTouchdowns",

    # Kicking
    "FG Made": "fieldGoalsMade",
    "Kicking Points": "kickingPoints",

    # Fantasy
    "Fantasy Score": "fantasyScore"
}