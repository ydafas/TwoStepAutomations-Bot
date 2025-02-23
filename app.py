from flask import Flask, request, jsonify
import requests
import os

# Add these constants
INVENTORY_URL = "http://localhost:5001"  # Update with deployed URL
SCHEDULING_URL = "http://localhost:5002"  # Update with deployed URL

app = Flask(__name__)

# 🔹 Set your credentials (Replace with actual values)
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN") # Replace this for Facebook
# WECHAT_APP_ID = "YOUR_WECHAT_APP_ID"  # Comment out if not using WeChat
# WECHAT_APP_SECRET = "YOUR_WECHAT_APP_SECRET"  # Comment out if not using WeChat
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")  # Used in webhook validation for Meta platforms
# THREADS_PAGE_TOKEN = "YOUR_THREADS_PAGE_TOKEN"  # Add for Threads if needed

# 🔹 Configurable Business Variables (Easily Rename or Comment Out)
BUSINESS_NAME = "Automated Business"  # Rename for each client
SUPPORT_EMAIL = "support@automatedbusiness.com"  # Rename or comment
SUPPORT_PHONE = "(123) 456-7890"  # Rename or comment
BASE_PRICE = "$199"  # Rename or comment for pricing
SHIPPING_DAYS = "3-5"  # Rename or comment for shipping info
FREE_SHIPPING_THRESHOLD = "$50"  # Rename or comment
RETURN_POLICY_DAYS = "30"  # Rename or comment
PROMO_CODE = "CHAT20"  # Rename or comment for promotions
PRODUCT_CATALOG_LINK = "https://automatedbusiness.com/products"  # Rename or comment

# 🔹 User Data Storage (In-memory for simplicity; use a DB in production)
user_data = {}  # Dictionary to store user info (e.g., name, email, order)

# ✅ Webhooks for Multiple Platforms
@app.route('/webhook', methods=['GET', 'POST'])  # Facebook/Instagram/Threads
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
                            process_message(sender_id, message_text, platform="meta")

        return "EVENT_RECEIVED", 200

# ✅ WeChat Webhook (Comment out if not needed)
# @app.route('/wechat', methods=['POST'])
# def wechat_webhook():
#     data = request.get_data(as_text=True)  # WeChat sends XML, parse it if needed
#     sender_id = "wechat_user"  # Placeholder; parse from XML
#     message_text = data.lower()  # Simplify for demo; use XML parsing in production
#     process_message(sender_id, message_text, platform="wechat")
#     return "<xml><ToUserName><![CDATA[user]]></ToUserName><FromUserName><![CDATA[bot]]></FromUserName><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[Message received!]]></Content></xml>"

# ✅ Process Incoming Messages (Multi-Platform Compatible)
def process_message(sender_id, message, platform="meta"):
    if message in ['hi', 'hello', 'start']:
        send_message(sender_id, f"Hey there! Welcome to {BUSINESS_NAME}! 🚀 How can I help?",
                     quick_replies=[{"title": "Services", "payload": "services"},
                                    {"title": "FAQs", "payload": "faq"},
                                    {"title": "Support", "payload": "support"},
                                    {"title": "Sales", "payload": "sales"},
                                    {"title": "Contact Us", "payload": "contact"}],
                     platform=platform)
    elif message == 'inventory':
        send_message(sender_id, "Which product would you like to check? (e.g., chatbot_basic, chatbot_pro)",
                     quick_replies=[{"title": "Basic Chatbot", "payload": "check_basic"},
                                    {"title": "Pro Chatbot", "payload": "check_pro"},
                                    {"title": "Enterprise Chatbot", "payload": "check_enterprise"}],
                     platform=platform)
    elif message in ['check_basic', 'check_pro', 'check_enterprise']:
        product_id = message.replace("check_", "")
        response = requests.get(f"{INVENTORY_URL}/inventory/{product_id}")
        if response.status_code == 200:
            data = response.json()
            availability = "in stock" if data["available"] else "out of stock"
            send_message(sender_id,
                         f"{data['product']}: {data['quantity']} available ({availability}), Price: {data['price']}",
                         platform=platform)
        else:
            send_message(sender_id, "Sorry, couldn’t check inventory. Try again later.", platform=platform)

    elif message == 'schedule':
        send_message(sender_id, "When would you like to schedule a consultation? Enter a date (YYYY-MM-DD).",
                     platform=platform)
        user_data[sender_id] = {"state": "waiting_schedule_date"}
    elif user_data[sender_id]["state"] == "waiting_schedule_date" and message:
        date = message
        response = requests.get(f"{SCHEDULING_URL}/scheduling/available/{date}")
        if response.status_code == 200:
            slots = response.json()["available_slots"]
            if slots:
                send_message(sender_id, f"Available slots on {date}: {', '.join(slots)}. Pick a time (HH:MM).",
                             platform=platform)
                user_data[sender_id]["state"] = "waiting_schedule_time"
                user_data[sender_id]["schedule_date"] = date
            else:
                send_message(sender_id, "No slots available on that date. Try another.", platform=platform)
                user_data[sender_id].pop("state", None)
        else:
            send_message(sender_id, "Invalid date or error. Use YYYY-MM-DD.", platform=platform)
            user_data[sender_id].pop("state", None)
    elif user_data[sender_id]["state"] == "waiting_schedule_time" and message:
        time = message
        response = requests.post(f"{SCHEDULING_URL}/scheduling", json={
            "customer_id": sender_id,
            "date": user_data[sender_id]["schedule_date"],
            "time": time,
            "service": "Chatbot Consultation"
        })
        if response.status_code == 201:
            data = response.json()
            send_message(sender_id, f"Appointment booked for {data['details']['date']}. Anything else?",
                         quick_replies=[{"title": "Main Menu", "payload": "start"}],
                         platform=platform)
        else:
            send_message(sender_id, "Couldn’t book. Slot unavailable or invalid time. Try again.",
                         platform=platform)
        user_data[sender_id].pop("state", None)
        user_data[sender_id].pop("schedule_date", None)

    elif message == 'cancel_schedule':
        response = requests.delete(f"{SCHEDULING_URL}/scheduling/{sender_id}")
        if response.status_code == 200:
            send_message(sender_id, "Appointment canceled. Anything else?",
                         quick_replies=[{"title": "Main Menu", "payload": "start"}],
                         platform=platform)
        else:
            send_message(sender_id, "No appointment found to cancel. Try again.",
                         platform=platform)


    elif message == 'services':
        send_message(sender_id, f"We offer automated chatbots for businesses! How can we assist you?",
                     quick_replies=[{"title": "Learn More", "payload": "learn_more"},
                                    {"title": "Back to Menu", "payload": "start"}],
                     platform=platform)
    elif message == 'faq':
        send_message(sender_id, f"Here are some FAQs:\n1️⃣ What services do you offer?\n2️⃣ How much does it cost?\n3️⃣ Shipping info?",
                     quick_replies=[{"title": "Pricing", "payload": "pricing"},
                                    {"title": "Shipping", "payload": "shipping"},
                                    {"title": "Returns", "payload": "returns"},
                                    {"title": "Back to Menu", "payload": "start"}],
                     platform=platform)
    elif message == 'support':
        send_message(sender_id, "Let’s solve your issue! What’s the problem?",
                     quick_replies=[{"title": "Order Issue", "payload": "order_issue"},
                                    {"title": "Technical Issue", "payload": "tech_issue"},
                                    {"title": "Other", "payload": "other_issue"}],
                     platform=platform)
    elif message == 'sales':
        send_message(sender_id, "Interested in our products? What can I help with?",
                     quick_replies=[{"title": "Products", "payload": "products"},
                                    {"title": "Offers", "payload": "offers"},
                                    {"title": "Lead Capture", "payload": "lead"}],
                     platform=platform)
    elif message == 'contact':
        send_message(sender_id, f"📧 Email: {SUPPORT_EMAIL}\n📞 Phone: {SUPPORT_PHONE}", platform=platform)
    elif message == 'pricing':
        send_message(sender_id, f"Our chatbot setup starts at {BASE_PRICE}. Subscription plans available.", platform=platform)
    elif message == 'shipping':
        send_message(sender_id, f"Shipping takes {SHIPPING_DAYS} days. Free over {FREE_SHIPPING_THRESHOLD}!", platform=platform)
    elif message == 'returns':
        send_message(sender_id, f"Returns accepted within {RETURN_POLICY_DAYS} days. Contact us for details.", platform=platform)
    elif message == 'order_issue':
        send_message(sender_id, "Please provide your order number.", platform=platform)
        user_data[sender_id] = {"state": "waiting_order"}
    elif message == 'tech_issue' or message == 'other_issue':
        send_message(sender_id, "Describe your issue briefly.", platform=platform)
        user_data[sender_id] = {"state": "waiting_issue"}
    elif message == 'products':
        send_message(sender_id, f"Check our products: {PRODUCT_CATALOG_LINK}", platform=platform)
    elif message == 'offers':
        send_message(sender_id, f"Get 20% off with code {PROMO_CODE}!", platform=platform)
    elif message == 'lead':
        send_message(sender_id, "Interested in our services? Provide your info:\n1. Name\n2. Email\n3. Phone (optional)\n4. Company (optional)",
                     platform=platform)
        user_data[sender_id] = {"state": "waiting_lead", "lead_data": {}}
    else:
        if sender_id in user_data:
            if user_data[sender_id]["state"] == "waiting_order":
                user_data[sender_id]["order_number"] = message
                send_message(sender_id, "Thanks! How urgent is this? (Urgent/Not Urgent)",
                             quick_replies=[{"title": "Urgent", "payload": "urgent"},
                                            {"title": "Not Urgent", "payload": "not_urgent"}],
                             platform=platform)
                user_data[sender_id]["state"] = "waiting_urgency"
            elif user_data[sender_id]["state"] == "waiting_issue":
                user_data[sender_id]["issue"] = message
                send_message(sender_id, "Thanks! How urgent is this? (Urgent/Not Urgent)",
                             quick_replies=[{"title": "Urgent", "payload": "urgent"},
                                            {"title": "Not Urgent", "payload": "not_urgent"}],
                             platform=platform)
                user_data[sender_id]["state"] = "waiting_urgency"
            elif user_data[sender_id]["state"] == "waiting_urgency":
                urgency = message
                order_or_issue = user_data[sender_id].get("order_number", user_data[sender_id].get("issue", ""))
                send_message(sender_id, f"A team member will follow up soon on your {('order' if 'order_number' in user_data[sender_id] else 'issue')} ({urgency}). Anything else?",
                             quick_replies=[{"title": "Main Menu", "payload": "start"}],
                             platform=platform)
                user_data[sender_id].pop("state", None)
            elif user_data[sender_id]["state"] == "waiting_lead":
                parts = message.split("\n")
                lead_data = user_data[sender_id]["lead_data"]
                if len(parts) >= 1:
                    lead_data["name"] = parts[0].strip()
                if len(parts) >= 2:
                    lead_data["email"] = parts[1].strip()
                if len(parts) >= 3:
                    lead_data["phone"] = parts[2].strip() if parts[2].strip() else None
                if len(parts) >= 4:
                    lead_data["company"] = parts[3].strip() if parts[3].strip() else None
                send_message(sender_id, "Thanks for your info! We’ll reach out soon. Anything else?",
                             quick_replies=[{"title": "Main Menu", "payload": "start"}],
                             platform=platform)
                user_data[sender_id].pop("state", None)
        else:
            send_message(sender_id, "Sorry, I didn’t understand that. Try selecting an option or type 'start'.",
                         quick_replies=[{"title": "Main Menu", "payload": "start"}],
                         platform=platform)

# ✅ Send Messages (Multi-Platform Compatible)
def send_message(sender_id, text, quick_replies=None, platform="meta"):
    if platform == "meta":  # Facebook/Instagram/Threads
        url = f"https://graph.facebook.com/v17.0/me/messages?access_token={FB_PAGE_TOKEN}"
        payload = {
            "recipient": {"id": sender_id},
            "message": {"text": text}
        }

        if quick_replies:
            payload["message"]["quick_replies"] = [
                {"content_type": "text", "title": qr["title"], "payload": qr["payload"]} for qr in quick_replies
            ]

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        print("🔹 Meta API Response:", response.json())
    # elif platform == "wechat":  # WeChat (Comment out if not needed)
    #     url = f"https://api.wechat.com/cgi-bin/message/custom/send?access_token={get_wechat_access_token()}"
    #     payload = {
    #         "touser": sender_id,
    #         "msgtype": "text",
    #         "text": {"content": text}
    #     }
    #     if quick_replies:
    #         # WeChat doesn’t natively support quick replies; use buttons or menus
    #         payload["msgtype"] = "news"  # Example; adjust for buttons
    #         payload["news"] = {"articles": [{"title": qr["title"], "url": "https://your.link"} for qr in quick_replies]}
    #     headers = {"Content-Type": "application/json"}
    #     response = requests.post(url, json=payload, headers=headers)
    #     print("🔹 WeChat API Response:", response.json())

# ✅ Helper Function for WeChat (Comment out if not needed)
# def get_wechat_access_token():
#     url = f"https://api.wechat.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}"
#     response = requests.get(url)
#     return response.json()["access_token"]

# ✅ Run Flask Server
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)