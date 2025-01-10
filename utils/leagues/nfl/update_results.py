import requests
import os

GO_BACKEND_URL = os.getenv('GO_BACKEND_URL')
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.getenv("TOKEN")}'
}


def update_results(parsed_players, closed):
    """
    Updates or closes NFL betting events based on scraped 'parsed_players' data.
    """

    # Map from your DB-friendly "stat_type" -> raw keys used in 'player_statistics'.
    #
    # If you see multi-stat lines like "Pass+Rush Yds" in your DB, the code below
    # handles it by splitting on "+" and summing each sub-stat, e.g. "Pass" + "Rush Yds".
    # Just make sure each sub-stat is a key in STAT_MAP.
    STAT_MAP = {
        # Passing
        "Pass Yds": "passingYards",
        "Pass TDs": "passingTouchdowns",
        "Pass Attempts": "completions/passingAttempts",
        "Completions": "completions/passingAttempts",
        "Interceptions": "interceptions",

        # Rushing
        "Rush Yds": "rushingYards",
        "Rush TDs": "rushingTouchdowns",
        "Rush Attempts": "rushingAttempts",
        "Longest Rush": "longRushing",

        # Receiving
        "Receptions": "receptions",
        "Receiving Yards": "receivingYards",
        "Rec TDs": "receivingTouchdowns",
        "Longest Reception": "longReception",

        # Common combos (split on '+')
        "Pass": "passingYards",    # For "Pass+Rush Yds" => stat_list = ["Pass", "Rush Yds"]
        "Rush": "rushingYards",    # For "Pass+Rush Yds"
        "Rush+Rec TDs": "rushingTouchdowns+receivingTouchdowns",  
        # ^ You can also store "rushingTouchdowns+receivingTouchdowns" if you want a single string
        #   and handle it with special logic, or rely on the + split approach.

        # Defense
        "Sacks": "sacks", 
        "Defensive TDs": "defensiveTouchdowns",
        "Total Tackles": "totalTackles",
        "Solo Tackles": "soloTackles",
        "TFL": "tacklesForLoss",
        "QB Hits": "QBHits",
        "Passes Defended": "passesDefended",

        # Some leagues combine pass + rush yards, etc.
        "Pass+Rush Yds": "passingYards+rushingYards",  # optional; see notes on special handling
        "Kicking Points": "kickingPoints",              # example if you have a kicker stat
        "Fantasy Score": "fantasyScore"                 # if you want to store a user-defined sum
    }

    for player in parsed_players:
        player_name = player.get("player_name")
       
        # 1) Fetch betting events for this player.
        try:
            response = requests.post(
                url=f"{GO_BACKEND_URL}/betting-events/by-player",
                headers=headers,
                json={"player_name": player_name}
            )
        except Exception as e:
            print(f"[ERROR] Getting betting events for {player_name}: {e}")
            continue

        if response.status_code != 200:
            print(f"[ERROR] by-player call failed for {player_name}, status code {response.status_code}")
            continue

        event_ids = response.json().get("event_ids", [])
        if not event_ids:
            # No bets on this player
            continue

        # 2) Process each bet event
        for event_id in event_ids:
            event_resp = requests.get(f"{GO_BACKEND_URL}/betting-events/{event_id}", headers=headers)
            if event_resp.status_code != 200:
                print(f"[ERROR] Could not get event {event_id}, status code {event_resp.status_code}")
                continue

            data = event_resp.json()
            desired_stat_type = data["stat_type"]  # e.g. "Pass+Rush Yds", "Receptions", "Longest Reception"

            # Handle combos (e.g. "Rush+Rec TDs", "Pass+Rush Yds", etc.) by splitting on '+'
            stat_list = desired_stat_type.split("+")  
            # If desired_stat_type = "Pass+Rush Yds", then stat_list = ["Pass", "Rush Yds"]

            # We'll sum up the partial results from each sub-stat.
            result = 0.0

            for sub_stat in stat_list:
                sub_stat = sub_stat.strip()  # remove extra whitespace
                raw_key = STAT_MAP.get(sub_stat)
                if not raw_key:
                    print(f"[WARNING] Unknown or unmapped NFL stat type: '{sub_stat}'")
                    continue

                # raw_key might itself contain '+' or '/', so handle it if needed
                # e.g. "passingYards+rushingYards" or "completions/passingAttempts"
                if "+" in raw_key:
                    # Example: "rushingTouchdowns+receivingTouchdowns"
                    # We'll handle each piece individually
                    combined_keys = raw_key.split("+")
                    for ck in combined_keys:
                        partial_val = get_stat_value(player["player_statistics"], ck, sub_stat)
                        result += partial_val
                else:
                    # Normal single key scenario (e.g. "passingYards")
                    partial_val = get_stat_value(player["player_statistics"], raw_key, sub_stat)
                    result += partial_val

            # 3) Update or close the betting event
            if closed:
                close_resp = requests.post(
                    f"{GO_BACKEND_URL}/betting-events/{event_id}/complete",
                    headers=headers,
                    json={"result": str(result)}
                )
                if close_resp.status_code == 200:
                    print(f"[INFO] Betting line for {player_name} {desired_stat_type} closed successfully with result={result}")
                else:
                    print(f"[ERROR] Failed to close betting line {event_id}, status={close_resp.status_code}")
            else:
                update_resp = requests.put(
                    f"{GO_BACKEND_URL}/betting-events/{event_id}",
                    headers=headers,
                    json={"result": str(result)}
                )
                if update_resp.status_code == 200:
                    print(f"[INFO] Betting line for {player_name} {desired_stat_type} updated successfully with result={result}")
                else:
                    print(f"[ERROR] Failed to update betting line {event_id}, status={update_resp.status_code}")


def get_stat_value(player_stats, raw_key, friendly_name):
    """
    Looks up the 'raw_key' in the player's 'player_statistics' list, then
    parses/returns the numerical value. Handles slash or dash if needed.
    """
    # player_stats is a list of [key, label, value], e.g.
    # ["completions/passingAttempts", "completions/passingAttempts", "26/34"]
    # or ["sacks-sackYardsLost", "sacks-sackYardsLost", "2-16"]

    for (stat_key, _label, value_str) in player_stats:
        if stat_key == raw_key:
            # If it has a slash, e.g. "26/34" for completions/passingAttempts
            if "/" in value_str:
                left_val, right_val = value_str.split("/")
                # Decide which to return
                if friendly_name.lower() in ("completions", "pass attempts"):
                    # If user asked for "Completions", return left_val
                    # If user asked for "Pass Attempts", return right_val
                    if "completions" in friendly_name.lower():
                        return float(left_val)
                    return float(right_val)
                else:
                    # By default, take the left side as main
                    return float(left_val)

            # If it has a dash, e.g. "2-16" for sacks-sackYardsLost
            if "-" in value_str:
                left_val, right_val = value_str.split("-")
                # If user asked for "Sacks", we might interpret left_val
                if "sacks" in raw_key.lower():
                    # e.g. "Sacks" -> parse the left side
                    return float(left_val)
                else:
                    # Otherwise, take left side by default or handle special logic
                    return float(left_val)

            # Normal numeric value
            try:
                return float(value_str)
            except ValueError:
                print(f"[WARNING] Could not parse numeric value from '{value_str}' for stat '{raw_key}'")
                return 0.0

    # If we never found the raw_key in the player's stats, fallback to 0
    print(f"[WARNING] Stat '{raw_key}' not found in player statistics.")
    return 0.0