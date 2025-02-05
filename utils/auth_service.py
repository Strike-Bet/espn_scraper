import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class AuthService:
    def __init__(self):
        self.server_url = os.getenv("BACKEND_URL")
        self.email = "ronitrjain@gmail.com"
        self.password = "MaggieWalker1!"
        self._access_token = None

        print(self.server_url, self.email, self.password)

    def get_token(self) -> Optional[str]:
        """Get authentication token, login if necessary"""
        if not self._access_token:
            self._access_token = self._login()
        return self._access_token

    def _login(self) -> Optional[str]:
        """Authenticate with the backend server"""
        try:
            response = requests.post(
                f"{self.server_url}/auth/login",
                json={
                    "email": self.email,
                    "password": self.password
                }
            )
            
            if response.status_code == 401:
                self._register()
                return self._login()
            
            if response.status_code != 200:
                raise Exception(f"Login failed: {response.status_code} {response.text}")
            
            print(response.json())  
            return response.json()["access_token"]
            
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")
        
    def _register(self) -> Optional[str]:
        """Register a new user with the backend server"""
        try:
            response = requests.post(
                f"{self.server_url}/register",
                json={
                    "username": "espn_scraper",
                    "email": "espn_scraper@strikebet.app",
                    "password": "espnScraper1!"
                }
            )
            if response.status_code != 200:
                raise Exception(f"Registration failed: {response.status_code} {response.text}")
            
            return response.json()["access_token"]
        except Exception as e:
            raise Exception(f"Registration failed: {str(e)}")

# Create a singleton instance
