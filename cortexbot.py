import os

#from webex_bot.commands.echo import EchoCommand
from webexteamsbot import TeamsBot
from webexteamsbot.models import Response
from typing import Any, Dict, List, Optional
import snowflake.connector
import requests
import pandas as pd
from snowflake.core import Root
import generate_jwt
from dotenv import load_dotenv
import json
import io
import matplotlib
import matplotlib.pyplot as plt 
import time

# Set Webex API key as the WEBEX_TOKEN environment variable &
# we'll retrieve that here:

matplotlib.use('Agg')
load_dotenv()

USER = os.getenv("USER")
ACCOUNT = os.getenv("ACCOUNT")
DATABASE = os.getenv("DATABASE")
SCHEMA = os.getenv("SCHEMA")
ANALYST_ENDPOINT = os.getenv("ANALYST_ENDPOINT")
RSA_PRIVATE_KEY_PATH = os.getenv("RSA_PRIVATE_KEY_PATH")
STAGE = os.getenv("SEMANTIC_MODEL_STAGE")
FILE = os.getenv("SEMANTIC_MODEL_FILE")

# Retrieve required details from environment variables
bot_email = os.getenv("BOT_EMAIL")
teams_token = os.getenv("WEBEX_TOKEN")
bot_url = os.getenv("BOT_URL")
bot_app_name = os.getenv("BOT_APP_NAME")



# Create a Bot Object
bot = TeamsBot(
    bot_app_name,
    teams_bot_token=teams_token,
    teams_bot_url=bot_url,
    teams_bot_email=bot_email,
    webhook_resource_event=[
        {"resource": "messages", "event": "created"},
    ],
)
#bot.set_help_message("Welcome to the Super Cool Bot! You can use the following commands:\n")

def wait_message():
    return "Cortex Analyst is generating message. Please wait ..."

def hello_message(msg):
    """
    Sample function to do some action.
    :param incoming_msg: The incoming message object from Teams
    :return: A text or markdown based reply
    """
    return "i did what you said - {}".format(msg.text)

def ask_cortex(msg):
    prompt = msg.text
    return process_analyst_message(prompt)

def process_analyst_message(prompt) -> Any:
    response = query_cortex_analyst(prompt)
    content = response["message"]["content"]
    return display_analyst_content(content)

def query_cortex_analyst(prompt) -> Dict[str, Any]:
    request_body = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "semantic_model_file": f"@{DATABASE}.{SCHEMA}.{STAGE}/{FILE}",
    }
    # resp = requests.post(
    #     url=f"{ANALYST_ENDPOINT}",
    #     json=request_body,
    #     headers={
    #         "Content-Type": "application/json",
    #         "Accept": "application/json",
    #         "Authorization": f'Snowflake Token="{CONN.rest.token}"',
    #     },
    # )
    resp = requests.post(
        url=f"{ANALYST_ENDPOINT}",
        json=request_body,
        headers={
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {JWT}",
        },
    )
    request_id = resp.headers.get("X-Snowflake-Request-Id")
    if resp.status_code == 200:
        return {**resp.json(), "request_id": request_id}  
    else:
        raise Exception(
            f"Failed request (id: {request_id}) with status {resp.status_code}: {resp.text}"
        )

def display_analyst_content(
    content: List[Dict[str, str]]
) -> None:
    output = ''
    for item in content:
        if item["type"] == "sql":
            output += "Generated SQL \n"
            output += item['statement'] +"\n\n"
            df = pd.read_sql(item["statement"], CONN)
            output += "Answer: \n\n"
            output += df.to_string()
        elif item["type"] == "text":
            output += "Answer: \n\n"
            output += item['text']
            
    return output

# A simple command that returns a basic string that will be sent as a reply
# Create a custom bot greeting function returned when no command is given.
# The default behavior of the bot is to return the '/help' command response
def greeting(incoming_msg):
    # Loopkup details about sender
    sender = bot.teams.people.get(incoming_msg.personId)
    # Create a Response object and craft a reply in Markdown.
    response = Response()
    response.markdown = "Hello {}, I'm a snowflake cortex chat bot. ".format(sender.firstName)
    response.markdown += "You can ask me below questions:"
    response.markdown += process_analyst_message('what can I ask?')
    return response

bot.set_greeting(greeting)

# Add new commands to the box.
#bot.add_command("/dosomething", "help for do something", do_something)
#bot.add_command(WeatherByZIP())
bot.add_command("@cortex", "call snowflake cortex",ask_cortex)


def init():
    conn,jwt = None,None
    jwt = generate_jwt.JWTGenerator(ACCOUNT,USER,RSA_PRIVATE_KEY_PATH).get_token()
    conn = snowflake.connector.connect(
        account=ACCOUNT,
        user=USER,
        authenticator= 'SNOWFLAKE_JWT',
        private_key_file=RSA_PRIVATE_KEY_PATH 
    )
    return conn,jwt

# Start app
if __name__ == "__main__":
    CONN,JWT = init()
    if not CONN.rest.token:
        print("Error: Failed to connect to Snowflake! Please check your Snowflake user, password, and account environment variables and try again.")
        quit()
    Root = Root(CONN)
    bot.run(host="0.0.0.0", port=5001)