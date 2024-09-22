import requests
import websocket
import threading
import json
import time

from . import VERSION

class Client:

    session: requests.Session
    ws : websocket.WebSocketApp

    ws_counter: int

    api_domain: str
    api_path: str
    login_processid: None|str
    logged_in: bool


    def __init__(self):
        self.session = requests.Session()
        self.ws = None
        self.ws_counter = 31

        self.api_domain = 'api.traderepublic.com'
        self.api_path = '/api'

        self.login_processid = None
        self.logged_in = False
        self.websocket_connected = False

        self.message_dict = {}

    def _json_api(self, *args):
        response = self._api(*args)
        return response.json()

    def _api(self, http_method: str, api_method: str, payload: dict={}):
        response = self.session.request(
            method = http_method,
            url = f'https://{self.api_domain}{self.api_path}{api_method}',
            json = payload
        )

        return response
    
    def login(self, phone_number: str, pin: int | str) -> bool:
        response = self._json_api('POST', '/v1/auth/web/login', {
            'phoneNumber': phone_number,
            'pin': str(pin)
        })

        if 'processId' in response:
            # success
            self.login_processid = response['processId']
            return True
        else:
            # Todo: raise error
            return False

    def auth(self, two_factor: int | str) -> bool:
        if not self.login_processid:
            # Todo: raise error
            return False

        response = self._api('POST', f'/v1/auth/web/login/{self.login_processid}/{two_factor}')
        self._websocket_start()
        
        for i in range(0,30):
            if self.websocket_connected:
                break
            time.sleep(1)

        if not self.websocket_connected:
            raise Exception('ws not connected')

        self.logged_in = True

        return True

    def _websocket_start(self):
        cookies = self.session.cookies.get_dict()
        self.ws = websocket.WebSocketApp(
                f'wss://{self.api_domain}/',
                cookie="; ".join(["%s=%s" %(i, j) for i, j in cookies.items()]),
                on_open=(self._websocket_on_open),
                on_close=(self._websocket_on_close),
                on_message=(self._websocket_on_message)
            )

        threading.Thread(target=self.ws.run_forever).start()

    def _websocket_on_open(self, wsapp: websocket.WebSocketApp):
        print(f'WS ! START')
        self._websocket_send('connect', None, {
            'locale': 'de',
            'platformId': 'webtrading',
            'platformVersion': 'python - 3.7',
            'clientId': 'github.com/MaximilianClemens/traderepublic',
            'clientVersion': VERSION
        })

    def _websocket_on_close(self, wsapp: websocket.WebSocketApp, close_status_code: int, close_msg: str):
        print(f'WS ! CLOSE, code: {close_status_code}, message: {close_msg}')
        self.websocket_connected = False
        self.logout(False)

        
    def _websocket_on_message(self, wsapp: websocket.WebSocketApp, message: str):
        print(f'WS > {message}')
        if message == 'connected':
            self.websocket_connected = True
        else:
            (id, data) = message.split(' ', 1)
            if id not in self.message_dict:
                self.message_dict[id] = []

            self.message_dict[id].append(data)


    def _websocket_send(self, function:str, number:int | None, message:str | dict | None = None):
        if not number:
            number = self.ws_counter
            self.ws_counter += 1

        send_array = [function, str(number)]
        if message:
            if(isinstance(message, dict)):
                message = json.dumps(message)
            send_array.append(message)
        
        send_message = " ".join(send_array)

        print(f'WS < {send_message}')
        self.ws.send(send_message)
        return str(number)
        
    def _websocket_send_sub(self, data:dict, end=True):
        # ToDo: make blocking optional, if we have a usecase for that
        id = self._websocket_send('sub', None, data)
        
        for i in range(0,30):
            time.sleep(1)
            if id in self.message_dict:
                break
        
        if id not in self.message_dict:
            raise Exception('send sub Timeout')

        time.sleep(1) #fixme
        response = []
        for message in self.message_dict[id]:
            s = message.split(' ', 1)
            if len(s) == 1:
                s.append(None)
            (mode, data) = s
            if mode == 'A':
                # Answer?
                if data:
                    response.append(json.loads(data))
            elif mode == 'C':
                # Close?
                end = True

        if end:
            self._websocket_send('unsub', id)

        return response


    def get_timeline_transactions(self):
        datas = self._websocket_send_sub({
            'type': 'timelineTransactions'
        })
        for data in datas:
            for item in data['items']:
                print(f'{item["id"]} {item["eventType"]} {item["title"]} {item["amount"]["value"]} {item["amount"]["currency"]}')

    def logout(self, close_socket:bool = True) -> bool:
        if not self.logged_in:
            return False
        
        response = self._api('POST', f'/v1/auth/web/logout')
        if close_socket:
            self.ws.close()

        self.logged_in = False
        return True