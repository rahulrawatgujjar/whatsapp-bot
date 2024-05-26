import logging
from flask import current_app, jsonify
import json
import requests
import datetime
from .token_utils import generate_token

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
    print("\nresponse:",response)

    test= requests.get(f"{current_app.config['BACKEND_URL']}/login", timeout=60)
    print(test.status_code)
    if test.status_code == 200:
        print("\nbackend connected")
    else:
        print("\nbackend not connected")
        return f"- Visit *{current_app.config['BACKEND_URL']}* so that server becomes active.\n- Wait until page loads and then come back here."

    if all(item in response for item in ["all", "site"]):
        data = {
            "wa_id" : wa_id,
            "message": response
        }
        payload = f"{wa_id}:{response}"
        try:
            token = generate_token(payload)
        except Exception as e:
            return "Unable to generate token\n"+str(e)
        headers = {
            'Authorization': f'Bearer {token}'
        }
        try:
            res = requests.post(f"{current_app.config['BACKEND_URL']}/api/whatsapp/sites",json=data, headers=headers, timeout=60)
            res.raise_for_status()
        except requests.exceptions.Timeout:
            return "Timeout occured in getting response from backend"
        except requests.exceptions.HTTPError as err:
            try:
                return err.response.json().get("error", "unknown HTTP error")
            except ValueError:
                return f"Value error in handling http error\n{err.response.text}"
            except Exception as e:
                return f"Any expception in handling http error\n {str(e)}"
        except requests.exceptions.ConnectionError as err:
            return f"Connection error\n{str(err)}"
        except requests.exceptions.RequestException as err:
            return "Requests exceptions\n"+str(err)
        except Exception as e:
            return "All other exceptions\n"+str(e)
        else:
            if res.content:
                try:
                    resJson=res.json()
                except ValueError as e:
                    return f"JSON decode error: {str(e)}"
            else:
                return "Empty response from server"
            sites = resJson["sites"]
            ans=""
            for item in sites:
                ans+=(item["site"]+"\n")
            return ans
    elif response.count(" ")==0 and all(item in response for item in ["www."]):
        response= response.lstrip("https://")
        response= response.lstrip("http://")
        data= {
            "wa_id" : wa_id,
            "site": response
        }
        payload = f"{wa_id}:{response}"
        try:
            token = generate_token(payload)
        except Exception as e:
            return "Unable to generate token\n"+str(e)
        headers = {
            'Authorization': f'Bearer {token}'
        }
        try:
            res = requests.post(f"{current_app.config['BACKEND_URL']}/api/whatsapp/password",json=data, headers=headers, timeout=60)
            res.raise_for_status()
        except requests.exceptions.Timeout:
            return "Timeout occured in getting response from backend"
        except requests.exceptions.HTTPError as err:
            try:
                return err.response.json().get("error", "unknown HTTP error")
            except ValueError:
                return f"Value error in handling http error\n{err.response.text}"
            except Exception as e:
                return f"Any expception in handling http error\n {str(e)}"
        except requests.exceptions.ConnectionError as err:
            return f"Connection error\n{str(err)}"
        except requests.exceptions.RequestException as err:
            return "Requests exceptions\n"+str(err)
        except Exception as e:
            return "All other exceptions\n"+str(e)
        else:
            if res.content:
                try:
                    resJson=res.json()
                except ValueError as e:
                    return f"JSON decode error: {str(e)}"
            else:
                return "Empty response from server"
            return f"*Site:* {resJson['site']}\n*Username:* ```{resJson['username']}```\n*Password:* ```{resJson['password']}```"
    elif all(item in response for item in ["command"]) and any(item in response for item in ["show", "display","view","list"]):
        return "- *all site*: To get a list of all website for which you have stored passwords.\n- *www.siteName.com*: To get username and password associated with this site."
    else:
        return f"Hey! I am a whatsapp bot.\nI will help you in *managing your passwords*.\nYou can visit our site *{current_app.config['BACKEND_URL']}* to manage your passwords more effectively.\nTo view all commands, message me ```show commands```"


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
