import pickle
import os.path
from pathlib import Path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

project_root = Path(__file__).parent.parent

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def download_sheet(spreadsheet_id, range_name):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = get_credentials()

    service = connect_service(creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=range_name).execute()
    values = result.get('values', [])
    return values


def get_credentials():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    tokenpath = project_root / '_private=token.pickle'
    credentialspath = project_root / 'google_credentials.json'
    if tokenpath.exists():
        with tokenpath.ope('rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentialspath.absolute(), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with tokenpath.open('wb') as token:
            pickle.dump(creds, token)
    return creds


def connect_service(creds):
    service = build('sheets', 'v4', credentials=creds)
    return service


def create_spreadsheet(title):
    spreadsheet = {
        'properties': {
            'title': title
        }
    }
    creds = get_credentials()
    service = connect_service(creds)
    spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                                fields='spreadsheetId').execute()
    print('Spreadsheet ID: {0}'.format(spreadsheet.get('spreadsheetId')))
    return spreadsheet.get('spreadsheetId')


def write_to_sheet(spreadsheet_id, range_name):
    raise NotImplementedError
