What is this:
dockerized strike flask server for scraping endpoints

run instructions:
1. docker build -t flask-app .
2. docker run -d -p 5000:5000 --name flask-container flask-app

Note: python version is Python 3.12.8

Note: url is hardcoded to an old url in utils/nba_scraper. change it when necessary