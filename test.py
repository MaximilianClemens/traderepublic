import os
from dotenv import load_dotenv
load_dotenv()

import traderepublic

client = traderepublic.Client()

if client.login(os.getenv('TR_NUMBER'), os.getenv('TR_PIN')):
    two_factor = input('2FA:')
    client.auth(two_factor)

if client.logged_in:
    for item in client.get_timeline_transactions():
        if item["eventType"] == 'TRADE_INVOICE':
            print(f'{item["timestamp"]} {item["id"]} {item["eventType"]} {item["title"]} {item["subtitle"]}')
            client.get_timeline_detail(item["id"])
    client.logout()