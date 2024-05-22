import logging
from flask import current_app, jsonify
import json
import requests

# from app.services.openai_service import generate_response
import re


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def generate_response(response,name,wa_id):
    # convert message to lower case
    response=response.lower()
    print("response:",response)

    try:
        if all(item in response for item in ["all", "site"]):
            payload = {
                "wa_id" : str(wa_id)
            }
            # try:
            res = requests.post(current_app.config['BACKEND_URL']+"/api/whatsapp/sites",json=payload, timeout=15)
            resJson= res.json()
            sites = resJson["sites"]
            ans=""
            for item in sites:
                ans+=(item["site"]+"\n")
            return ans
            # except Exception as e:
            #     return e
        elif response.count(" ")==0 and all(item in response for item in ["www."]):
            response= response.lstrip("https://")
            response= response.lstrip("http://")
            payload= {
                "wa_id" : str(wa_id),
                "site": str(response)
            }
            # try:
            res = requests.post(current_app.config['BACKEND_URL']+"/api/whatsapp/password",json=payload, timeout=15)
            resJson= res.json()
            return f"*Site:* {resJson['site']}\n*Username:* ```{resJson['username']}```\n*Password:* ```{resJson['password']}```"
            # except Exception as e:
            #     return e
        else:
            return "hello i am static"
    except requests.Timeout:
        return "Timeout occured in getting response from backend"
    except Exception  as e:
        if res.status_code >= 400:  # Check for error status code (adjust if needed)
            try:
                error_data = res.json()  # Attempt to parse error JSON
                return f"Error: {error_data.get('error', 'Unknown error')}"  # Use get to handle missing 'error' key
            except:
                    return "An error occurred while processing your request."  # Fallback for non-JSON errors
        else:
            raise  # Re-raise the exception for unexpected errors


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    # print(body["entry"][0]["changes"][0]["value"]["contacts"])
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    # TODO: implement custom function here
    response = generate_response(message_body,name,wa_id)

    # OpenAI Integration
    # response = generate_response(message_body, wa_id, name)
    # response = process_text_for_whatsapp(response)
    reciepent_id= "+" + wa_id

    data = get_text_message_input(reciepent_id, response)
    send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
