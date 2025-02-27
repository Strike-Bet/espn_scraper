from datetime import datetime
import os

# Base URLs
ESPN_BASE_URL = "https://site.web.api.espn.com/apis/site/v2/sports"
ESPN_PARAMS = "region=us&lang=en&contentorigin=espn&calendartype=offdays&includeModules=videos"

# Status constants
STATUS_FINAL = "STATUS_FINAL"
STATUS_IN_PROGRESS = "STATUS_IN_PROGRESS"
STATUS_SCHEDULED = "STATUS_SCHEDULED"
STATUS_HALFTIME = "STATUS_HALFTIME"

# League specific endpoints
LEAGUE_ENDPOINTS = {
    "nba": f"{ESPN_BASE_URL}/basketball/nba/scoreboard",
    "nfl": f"{ESPN_BASE_URL}/football/nfl/scoreboard",
    "cbb": f"{ESPN_BASE_URL}/basketball/mens-college-basketball/scoreboard"
}

NFL_LEAGUE_ID = 9
NBA_LEAGUE_ID = 7
TENNIS_LEAGUE_ID = 5
UFC_LEAGUE_ID = 12
SOCCER_LEAGUE_ID = 82
CBB_LEAGUE_ID = 20