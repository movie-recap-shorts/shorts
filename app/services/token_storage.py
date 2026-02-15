
import os
import json
import datetime
from typing import Optional, Dict, Any
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from loguru import logger
from typing import Tuple

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
        if not self.creds_json:
            logger.warning("GOOGLE_SHEETS_CREDENTIALS not set. Token storage disabled.")
            return False
        if not self.sheet_id:
            logger.warning("SHEET_ID not set. Token storage disabled.")
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
            sh = self.client.open_by_key(self.sheet_id)
            try:
                worksheet = sh.worksheet("Tokens")
            except gspread.WorksheetNotFound:
                worksheet = sh.sheet1
                if worksheet.title != "Tokens":
                    if not worksheet.get_all_values():
                        worksheet.update('A1:D1', [['Channel Name', 'Token JSON', 'Client Secret JSON', 'Last Updated']])
                        worksheet.update_title("Tokens")
            return worksheet
        except Exception as e:
            logger.error(f"Failed to access worksheet: {e}")
            return None

    def save_token(self, channel_name: str, token_data: Dict[str, Any], client_secret_data: Optional[Dict[str, Any]] = None) -> bool:
        """Save token and optional client secret to Google Sheet."""
        worksheet = self._get_worksheet()
        if not worksheet:
            return False
            
        try:
            token_json = json.dumps(token_data)
            secret_json = json.dumps(client_secret_data) if client_secret_data else ""
            timestamp = datetime.datetime.now().isoformat()
            
            cell = worksheet.find(channel_name)
            
            if cell:
                row_num = cell.row
                worksheet.update_cell(row_num, 2, token_json)
                if secret_json:
                    worksheet.update_cell(row_num, 3, secret_json)
                worksheet.update_cell(row_num, 4, timestamp)
                logger.info(f"Updated credentials for {channel_name} in Google Sheet")
            else:
                worksheet.append_row([channel_name, token_json, secret_json, timestamp])
                logger.info(f"Saved new credentials for {channel_name} to Google Sheet")
                
            return True
        except Exception as e:
            logger.error(f"Failed to save to Google Sheet: {e}")
            return False

    def get_credentials(self, channel_name: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Retrieve token and client secret from Google Sheet."""
        worksheet = self._get_worksheet()
        if not worksheet:
            return None, None
            
        try:
            cell = worksheet.find(channel_name)
            if cell:
                row_data = worksheet.row_values(cell.row)
                token_json = row_data[1] if len(row_data) > 1 else None
                secret_json = row_data[2] if len(row_data) > 2 else None
                
                token_data = json.loads(token_json) if token_json else None
                secret_data = json.loads(secret_json) if secret_json and secret_json.strip() else None
                return token_data, secret_data
            else:
                logger.warning(f"No credentials found for {channel_name} in Google Sheet")
                return None, None
        except Exception as e:
            logger.error(f"Failed to retrieve from Google Sheet: {e}")
            return None, None
