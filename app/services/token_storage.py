
import os
import json
import datetime
from typing import Optional, Dict, Any
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from loguru import logger

class TokenStorage:
    """
    Manages storage of YouTube API tokens in a private Google Sheet.
    """
    
    def __init__(self):
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        self.creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
        self.sheet_id = os.environ.get("SHEET_ID")
        self.client = None
        self.sheet = None

    def _authenticate(self) -> bool:
        """Authenticate with Google Sheets API."""
        if not self.creds_json or not self.sheet_id:
            logger.warning("GOOGLE_SHEETS_CREDENTIALS or SHEET_ID not set. Token storage disabled.")
            return False
            
        try:
            creds_dict = json.loads(self.creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.scope)
            self.client = gspread.authorize(creds)
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            return False

    def _get_worksheet(self):
        """Get or create the worksheet."""
        if not self.client:
            if not self._authenticate():
                return None
                
        try:
            # Open the spreadsheet by ID
            sh = self.client.open_by_key(self.sheet_id)
            
            # Try to get the 'Tokens' worksheet, or use the first one
            try:
                worksheet = sh.worksheet("Tokens")
            except gspread.WorksheetNotFound:
                # If 'Tokens' doesn't exist, check if we can use the first sheet or create one
                worksheet = sh.sheet1
                if worksheet.title != "Tokens":
                    # Initialize headers if it's a new/empty sheet
                    if not worksheet.get_all_values():
                        worksheet.update('A1:C1', [['Channel Name', 'Token JSON', 'Last Updated']])
                        worksheet.update_title("Tokens")
            
            return worksheet
        except Exception as e:
            logger.error(f"Failed to access worksheet: {e}")
            return None

    def save_token(self, channel_name: str, token_data: Dict[str, Any]) -> bool:
        """
        Save or update a token in the Google Sheet.
        
        Args:
            channel_name: Name of the YouTube channel (e.g., 'movies_en')
            token_data: Dictionary containing the token data
        """
        worksheet = self._get_worksheet()
        if not worksheet:
            return False
            
        try:
            token_json = json.dumps(token_data)
            timestamp = datetime.datetime.now().isoformat()
            
            # Check if channel already exists
            cell = worksheet.find(channel_name)
            
            if cell:
                # Update existing row
                row_num = cell.row
                worksheet.update_cell(row_num, 2, token_json)
                worksheet.update_cell(row_num, 3, timestamp)
                logger.info(f"Updated token for {channel_name} in Google Sheet")
            else:
                # Append new row
                worksheet.append_row([channel_name, token_json, timestamp])
                logger.info(f"Saved new token for {channel_name} to Google Sheet")
                
            return True
        except Exception as e:
            logger.error(f"Failed to save token to Google Sheet: {e}")
            return False

    def get_token(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a token from the Google Sheet.
        
        Args:
            channel_name: Name of the YouTube channel
            
        Returns:
            Token data dictionary or None if not found
        """
        worksheet = self._get_worksheet()
        if not worksheet:
            return None
            
        try:
            cell = worksheet.find(channel_name)
            if cell:
                token_json = worksheet.cell(cell.row, 2).value
                return json.loads(token_json)
            else:
                logger.warning(f"No token found for {channel_name} in Google Sheet")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve token from Google Sheet: {e}")
            return None
