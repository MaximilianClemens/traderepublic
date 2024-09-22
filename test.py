import os
from dotenv import load_dotenv
load_dotenv()

import traderepublic

client = traderepublic.Client()

if client.login(os.getenv('TR_NUMBER'), os.getenv('TR_PIN')):
    two_factor = input('2FA:')
    client.auth(two_factor)

if client.logged_in:
    print(client.get_timeline_transactions())
    client.logout()