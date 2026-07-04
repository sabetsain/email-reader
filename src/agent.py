from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage, SystemMessage, HumanMessage
from langgraph.types import Command, Send
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Literal
from IPython.display import Image, display
from dotenv import load_dotenv

import operator
import pickle
import os.path
import base64
import email
import lxml


load_dotenv()

SYSTEM_PROMPT = "You are a helpful AI assistant. You summarize emails into 1-2 sentences."
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Definig the model
model = init_chat_model(
    "gemini-3.5-flash",
    model_provider="google-genai",
    temperature=0,
    timeout=600,
    max_tokens=50000,
    streaming=True,
)


# Structure for classifiying emails
class EmailClassification(TypedDict):
    type: Literal["newsletter", "marketting", "misc.", "job", "event"]
    summary: str

class EmailStates(TypedDict):
    subject: list[str]
    sender: list[str]
    message: list[str]
    id: list[int]

    classification: Annotated[list[EmailClassification | None], operator.add]

class SingleEmailState(TypedDict):
    subject: str
    sender: str
    message: str
    id: int

# Get emails node
def get_emails(state: EmailStates):
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

            state["message"].append(body)
            state["sender"].append(sender)
            state["subject"].append(subject)
            state['id'].append(msg['id'])

        except Exception as e:
            # Expose the error if one actually manages to bypass the structure checks
            print(f"Error parsing message {msg['id']}: {e}")
    
    return [Send("classify_email", SingleEmailState({"subject": s, "message": m, "sender": f, "id": i})) for s, m, f in zip(state['subject'], state['message'], state['sender'], state['id'])]

# Classify emails node
def classify_emails(state: SingleEmailState):
    """Use LLM to classify email intent and urgency, then route accordingly"""

    # Create structured LLM that returns EmailClassification dict
    structured_llm = model.with_structured_output(EmailClassification)

    # Format the prompt on-demand, not stored in state
    classification_prompt = f"""
        Analyze and appropriately classify this email with a label.

        From: {state['sender']}
        Subject: {state['subject']}
        Body: {state['message']}

        Class descriptions:
        - newsletter: for emails that are newsletters to which the user is subscribed.
        - marketting: ads and marketting campaigns from companies.
        - job: for job updates, LinkedIn digests, return offers, and application declines.
        - event: if a given event is established with a save the date (e.g. concerts, interviews, meetings).
        - misc.: anything that does not fall into the above four categories.

        Once the email is classified, summarize it in 1-2 sentences.
    """

    # Get structured response directly as dict
    classification = (structured_llm.invoke(classification_prompt))

    # Store classification as a single dict in state
    return {"classification": [{"id": state["id"], **classification}]}
    

def assign_class_to_state(state: EmailStates):
    {c["id"]: c for c in state["classification"]} # NEEDS FIXING

    # all_classifications = state['classification']

    return state

# Build and compile agent: 
agent_builder = StateGraph(EmailStates)

# Add nodes
agent_builder.add_node("get_emails", get_emails)
agent_builder.add_node("classify_emails", classify_emails)
agent_builder.add_node("assign_class_to_state", assign_class_to_state)

# Add edges to connect nodes
agent_builder.add_edge(START, "get_emails")
agent_builder.add_edge("get_emails", "classify_emails")
agent_builder.add_edge("classify_emails", "assign_class_to_state")
agent_builder.add_edge("assign_class_to_state", END)

# Compile the agent
agent = agent_builder.compile()

# Invoke
# messages = [HumanMessage(content=EXAMPLE_EMAIL)]
messages = agent.invoke(EmailStates([], [], [], [])) # NEEDS FIXING
for m in messages["messages"]:
    m.pretty_print()

