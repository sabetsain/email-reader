# import the required libraries
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

import pickle
import os.path
import base64
import email
import lxml

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def getEmails():
    # Variable creds will store the user access token.
    # If no valid token found, we will create one.
    creds = None

    # The file token.pickle contains the user access token.
    # Check if it exists
    if os.path.exists('token.pickle'):
        # Read the token from the file and store it in the variable creds
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        # print("Creds are:", creds)

    # If credentials are not available or are invalid, ask the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the access token in token.pickle file for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Connect to the Gmail API
    service = build('gmail', 'v1', credentials=creds)

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")

    # request a list of all the messages
    result = service.users().messages().list(userId='me', q=f'after:{yesterday}').execute()

    # We can also pass maxResults to get any number of emails. Like this:
    # result = service.users().messages().list(maxResults=200, userId='me').execute()
    messages = result.get('messages')

    # messages is a list of dictionaries where each dictionary contains a message id.

    # iterate through all the messages
    # iterate through all the messages
    for msg in messages:
        txt = service.users().messages().get(userId='me', id=msg['id']).execute()

        try:
            payload = txt['payload']
            headers = payload['headers']

            subject = "No Subject"
            sender = "Unknown Sender"

            # Look for Subject and Sender Email in the headers
            for d in headers:
                if d['name'] == 'Subject':
                    subject = d['value']
                if d['name'] == 'From':
                    sender = d['value']

            # Robust Body Extraction handling singlepart and multipart structures
            body_data = ""
            if 'parts' in payload:
                # Loop through parts to find plain text or html
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' or part['mimeType'] == 'text/html':
                        body_data = part['body'].get('data', '')
                        break
            else:
                # Single part email
                body_data = payload['body'].get('data', '')

            if body_data:
                # Clean and decode the base64url data safely
                data = body_data.replace("-", "+").replace("_", "/")
                decoded_data = base64.b64decode(data)

                # Parse it with BeautifulSoup
                soup = BeautifulSoup(decoded_data, "lxml")
                
                # FIX: Use .get_text() instead of trying to call .body() like a function
                body = soup.get_text(separator="\n", strip=True) 
            else:
                body = "[Empty Message Body]"

            # Printing the results
            print("Subject: ", subject)
            print("From: ", sender)
            print("Message:\n", body)
            print('-' * 50)

        except Exception as e:
            # Expose the error if one actually manages to bypass the structure checks
            print(f"Error parsing message {msg['id']}: {e}")

# if __name__ == "__main__":
#     getEmails()