from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
import os
import json
from bot import process_link_with_agent
import agentops

from normal_bot import create_response, scrape_site, find_link_in_string, format_output, update_csv

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
verifier = SignatureVerifier(os.getenv('SLACK_SIGNING_SECRET'))

print(f"SLACK_BOT_TOKEN: {os.getenv('SLACK_BOT_TOKEN')}")
print(f"SLACK_SIGNING_SECRET: {os.getenv('SLACK_SIGNING_SECRET')}")


# Global dictionary to store event IDs
processed_events = {}


def is_duplicate_event(event_id: str) -> bool:
    """
    Check if an event ID has already been processed.

    Args:
    - event_id: The unique ID of the Slack event.

    Returns:
    - True if the event has already been processed, False otherwise.
    """
    if event_id in processed_events:
        return True
    else:
        # Mark this event as processed by adding it to the dictionary
        processed_events[event_id] = True
        return False


@app.post("/slack/events")
async def slack_events(request: Request):

    ao_client = agentops.Client()
    form_data = await request.body()
    headers = request.headers

    if not verifier.is_valid_request(form_data, headers):
        print("Invalid request signature")
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    request_data = json.loads(form_data)

    print(request_data)
    if 'challenge' in request_data:
        print("Challenge request received")
        return PlainTextResponse(request_data['challenge'])

    # Check for duplicate events
    event_id = request_data.get('event_id')

    if is_duplicate_event(event_id):
        return Response(status_code=status.HTTP_200_OK)

    # Check if the incoming request is an event we're interested in
    if request_data['event']['type'] in ['app_mention', 'message']:
        try:
            event = request_data['event']
            user = event['user']
            text = event['text']
            channel = event['channel']
            print(f"Received message from {user}: {text}")

            # # Respond to the message
            # response = client.chat_postMessage(channel=channel,
            #                                    text=f"Hello <@{user}>, you said: {text}")
            ao_client.record(agentops.Event(event_type="Received link"))
            link = find_link_in_string(text)

            client.chat_postMessage(channel=channel,
                                    text=f"*(づ ◕‿◕ )づ*\n Hey! I'm finding info for `{link}` (this may take a minute)...")
            event = agentops.Event(event_type="Scraping")
            ao_client.record(event)
            web_data = scrape_site(link)
            ao_client.record(agentops.Event(event_type="Scraped"))

#             web_data = """Company name: AgentOps
# Website: [agentops.ai](http://agentops.ai)
# Description: AgentOps helps build compliant AI agents with observability, evaluations, and replay analytics. The platform provides instant testing and debugging for AI agents that work.
# Tags: AI, Compliance, Testing, Debugging, Observability, Evaluations, Replay Analytics
# Takeaways:

# * AgentOps fixes the issue of AI agents being black boxes and prompt guessing.
# * The platform allows for unlimited testing and debugging with just three lines of code.
# * AgentOps offers generous free limits, allowing users to upgrade only when needed.

# Questions:

# * What specific industries or use cases does AgentOps cater to?
# * How does AgentOps ensure compliance for AI agents?
# * Are there any success stories or case studies from companies that have used AgentOps?"""

            client.chat_postMessage(channel=channel,
                                    text="*໒(⊙ᴗ⊙)७✎▤*\n I just read through the page. I'm asking Mistral to summarize it for you...")

            response = create_response(web_data, link)

            client.chat_postMessage(channel=channel,
                                    text="*(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧*\nhere you go")

            client.chat_postMessage(channel=channel,
                                    text=response)

            formated_output = format_output(response)
            update_csv(formated_output)

            client.chat_postMessage(channel=channel,
                                    text="*-(๑☆‿ ☆#)ᕗ*\nI went ahead and saved this to your CRM. Send me more links if you want to learn about them")

            # # agent_response = process_link_with_agent(text)
            # # print(agent_response)
            # response = client.chat_postMessage(channel=channel,
            #                                    text=process_link_with_agent(agent_response))

            ao_client.end_session('Success', end_state_reason=formated_output)
            return Response(status_code=status.HTTP_200_OK)
        except SlackApiError as e:
            print(f"Slack API Error: {e.response['error']}")
            client.chat_postMessage(channel=channel,
                                    text=f"*(⋋°̧̧̧ω°̧̧̧⋌)*\nSorry, I couldn't read that. {str(e)}")
            ao_client.end_session('Fail', end_state_reason=str(e))

        except Exception as e:
            client.chat_postMessage(channel=channel,
                                    text=f"*(⋋°̧̧̧ω°̧̧̧⋌)*\nSorry, I couldn't read that. {str(e)}")
            ao_client.end_session('Fail', end_state_reason=str(e))
    return Response(status_code=status.HTTP_200_OK)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
