from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 🔹 Set Environment Variables (Set these in Render Dashboard)
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "secure_token")  # Default for testing

# ✅ Webhook Verification for Facebook API
@app.route('/webhook', methods=['GET', 'POST'])
def fb_webhook():
    if request.method == 'GET':  # Verification step
        verify_token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if verify_token == VERIFY_TOKEN:
            return challenge
        return "Verification failed", 403

    elif request.method == 'POST':  # Handle messages
        data = request.json
        print("🔹 Received Meta Webhook Data:", data)

        if 'entry' in data:
            for entry in data['entry']:
                if 'messaging' in entry:
                    for messaging_event in entry['messaging']:
                        if 'message' in messaging_event:
                            sender_id = messaging_event['sender']['id']
                            message_text = messaging_event['message'].get('text', '').lower()
                            send_message(sender_id, f"Hello! You said: {message_text}")
        return "EVENT_RECEIVED", 200

# ✅ Function to Send a Message via Meta API
def send_message(sender_id, text):
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={FB_PAGE_TOKEN}"
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": text}
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    print("🔹 Meta API Response:", response.json())

# ✅ Run Flask Server for Render Deployment
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Render assigns a port dynamically
    app.run(host='0.0.0.0', port=port, debug=True)
