import json
import boto3
import os
STATS_KEYS = ["MIN", "FG", "3PT", "FT", "OREB", "DREB", "REB",
              "AST", "STL", "BLK", "TO", "PF", "+/-", "PTS"]

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

def parse_stat(stat_key: str, raw_value: str) -> float:
    """
    Converts the raw stat string into a float or int that can be averaged.
    - FG, 3PT, FT are stored as (made / attempted).
    - +/- is an integer (e.g., '+5' -> 5, '-3' -> -3).
    - Most others are integers.
    """
    if stat_key in ["FG", "3PT", "FT"]:
        # e.g. "4-9"
        made_attempted = raw_value.split("-")
        if len(made_attempted) == 2:
            try:
                made = int(made_attempted[0])
                attempted = int(made_attempted[1])
                if attempted != 0:
                    return made / attempted
                else:
                    return 0.0
            except ValueError:
                return 0.0
        else:
            return 0.0

    elif stat_key == "+/-":
        # Remove '+' sign if present, then convert to float
        try:
            return float(raw_value.replace("+", "")) if raw_value else 0.0
        except ValueError:
            return 0.0

    else:
        # Parse as float for consistency
        try:
            return float(raw_value)
        except ValueError:
            return 0.0

def update_average_stat(avg: float, count: int, new_val: float) -> (float, int):
    """
    Given an old average (avg) and count, update them with a new value (new_val).
    Returns the (updated_avg, updated_count).
    """
    updated_avg = (avg * count + new_val) / (count + 1)
    return updated_avg, count + 1

def collect_player_stats_with_averages(
    aws_access_key_id: str = AWS_ACCESS_KEY_ID,
    aws_secret_access_key: str = AWS_SECRET_ACCESS_KEY,
    bucket_name: str = "strike-prizepicks",
    base_prefix: str = "NBA/NBA_PLAYERDATA/"
) -> dict:
    """
    1. Lists ALL objects in the specified S3 'base_prefix'.
    2. Loads each file (JSON).
    3. Extracts stats for each player.
    4. Maintains a running average for each stat across all files (up to 10 updates).
    Returns a dict of structure:
    {
      playerName: {
        statKey: { "avg": float, "count": int },
        ...
      },
      ...
    }
    """
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name="us-east-1",
    )

    paginator = s3_client.get_paginator("list_objects_v2")
    player_stats = {}  # { playerName: { statKey: {"avg": float, "count": int} } }

    for page in paginator.paginate(Bucket=bucket_name, Prefix=base_prefix):
        # If no files in this page, move on
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            key = obj["Key"]

            try:
                # Read file from S3
                s3_object = s3_client.get_object(Bucket=bucket_name, Key=key)
                file_content = s3_object["Body"].read().decode("utf-8")
            except Exception as e:
                # If we fail to read or decode, skip this file
                print(f"Skipping file {key} due to read error: {e}")
                continue

            # If file content is empty, skip
            if not file_content.strip():
                print(f"Skipping file {key} because it is empty.")
                continue

            try:
                data = json.loads(file_content)
            except json.JSONDecodeError as e:
                print(f"Skipping file {key} due to JSON decode error: {e}")
                continue

            # If the JSON data is empty (e.g. `[]` or `{}`), skip
            if not data:
                print(f"Skipping file {key} because it contains no data.")
                continue

            # Traverse each "team" or "entry" in the JSON
            for entry in data:
                # The "statistics" field has the stat groups for the team
                stat_groups = entry.get("statistics", [])
                for stat_group in stat_groups:
                    # "athletes" is a list of players with their stats
                    for athlete in stat_group.get("athletes", []):
                        athlete_info = athlete.get("athlete", {})
                        player_name = athlete_info.get("displayName", "Unknown Player")

                        # Initialize player in dictionary if new
                        if player_name not in player_stats:
                            player_stats[player_name] = {
                                k: {"avg": 0.0, "count": 0} for k in STATS_KEYS
                            }

                        raw_stats = athlete.get("stats", [])
                        # Update each stat’s running average, up to 10 times
                        for i, stat_key in enumerate(STATS_KEYS):
                            # Only update if i < len(raw_stats) and count < 10
                            if i < len(raw_stats) and player_stats[player_name][stat_key]["count"] < 10:
                                parsed_val = parse_stat(stat_key, raw_stats[i])
                                old_avg = player_stats[player_name][stat_key]["avg"]
                                old_count = player_stats[player_name][stat_key]["count"]

                                new_avg, new_count = update_average_stat(old_avg, old_count, parsed_val)
                                player_stats[player_name][stat_key]["avg"] = new_avg
                                player_stats[player_name][stat_key]["count"] = new_count

    return player_stats

def get_final_averages(player_stats: dict) -> dict:
    """
    Convert the {statKey: {avg: float, count: int}} structure
    into just {statKey: final_avg} for each player.
    """
    final_dict = {}
    for player_name, stats_dict in player_stats.items():
        final_dict[player_name] = {}
        for stat_key, stat_data in stats_dict.items():
            final_dict[player_name][stat_key] = stat_data["avg"]
    return final_dict
