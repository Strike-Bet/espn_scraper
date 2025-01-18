from datetime import datetime

# Base URLs
ESPN_BASE_URL = "https://site.web.api.espn.com/apis/site/v2/sports"
ESPN_PARAMS = "region=us&lang=en&contentorigin=espn&calendartype=offdays&includeModules=videos"

# Status constants
STATUS_FINAL = "STATUS_FINAL"
STATUS_IN_PROGRESS = "STATUS_IN_PROGRESS"
STATUS_SCHEDULED = "STATUS_SCHEDULED"

# League specific endpoints
LEAGUE_ENDPOINTS = {
    "nba": f"{ESPN_BASE_URL}/basketball/nba/scoreboard",
    "nfl": f"{ESPN_BASE_URL}/football/nfl/scoreboard"
}

NFL_LEAGUE_ID = 9
NBA_LEAGUE_ID = 7
