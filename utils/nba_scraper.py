from scrapingbee import ScrapingBeeClient
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")

def scrape_current_nba_player_stats():
    try:
        # Define the main URL to scrape
        url = "https://www.espn.com/nba/scoreboard/_/date/20241204"

        # Initialize the ScrapingBee client with your API key
        client = ScrapingBeeClient(api_key=SCRAPINGBEE_API_KEY)  # Replace with your actual API key

        # Fetch the main page content using ScrapingBee
        response = client.get(url, params={"render_js": "false", "stealth_proxy": "false"})

        # Check if the response is successful
        if response.status_code != 200:
            return {"error": f"Failed to fetch main URL. Status code: {response.status_code}"}

        soup = BeautifulSoup(response.content, "html.parser")

        # Find all "Box Score" links
        box_score_links = soup.find_all("a", string="Box Score")
        hrefs = [f"https://www.espn.com{link.get('href')}" for link in box_score_links if link.get("href")]

        # Loop through each box score page
        players_data = {}
        for box_score_url in hrefs:
            try:
                print(f"Fetching Box Score page: {box_score_url}")
                box_response = client.get(box_score_url, params={"render_js": "false", "stealth_proxy": "false"})

                if box_response.status_code != 200:
                    return {"error": f"Failed to fetch {box_score_url}. Status code: {box_response.status_code}"}

                box_soup = BeautifulSoup(box_response.content, "html.parser")

                # Extract player names, jersey numbers, and stats
                stats_rows = box_soup.select("tbody.Table__TBODY tr.Table__TR--sm")
                html_content = ''.join(str(row) for row in stats_rows)
                soup = BeautifulSoup(html_content, 'html.parser')

                # Find all rows in the table
                rows = soup.find_all('tr', class_='Table__TR Table__TR--sm Table__even')

                # Create a list to hold all rows for reference
                all_rows = list(rows)

                # Iterate through each row to filter player rows and extract data
                for i, row in enumerate(all_rows):
                    # Check if the row contains a player name with the specified class
                    player_name_tag = row.find('span', class_="truncate db Boxscore__AthleteName Boxscore__AthleteName--long")
                    
                    if player_name_tag:
                        # Extract the player's name and jersey number
                        player_name = player_name_tag.text.strip()
                        player_jersey = row.find('span', class_='playerJersey').text.strip()

                        # Use data-idx to match the corresponding stats row
                        data_idx = row.get('data-idx')

                        # Find the first stats row with a higher index and the same data-idx
                        stats_row = None
                        for j in range(i + 1, len(all_rows)):  # Iterate forward
                            if all_rows[j].get('data-idx') == data_idx:
                                stats_row = all_rows[j]
                                break

                        if stats_row:
                            # Extract stats from the stats row
                            stats = [td.text.strip() for td in stats_row.find_all('td')]

                            # Store player data in the dictionary
                            players_data[player_name] = {
                                'jersey': player_jersey,
                                'stats': stats
                            }
            except Exception as e:
                # Log error for this specific box score page
                return {"error": f"Error fetching {box_score_url}: {str(e)}"}

        return players_data

    except Exception as e:
        # Handle general errors
        return {"error": f"Unexpected error: {str(e)}"}
