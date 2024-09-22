import requests
import websocket
import threading
import json

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

        print(response)

        if 'processId' in response:
            # success
            self.login_processid = response['processId']
            return True
        else:
            # Todo: raise error
            return False

    def auth(self, two_factor: int | str) -> bool:
        print('auth')
        if not self.login_processid:
            # Todo: raise error
            return False

        response = self._api('POST', f'/v1/auth/web/login/{self.login_processid}/{two_factor}')
        print(response)
        self._websocket_start()

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
        
    def _websocket_on_message(self, wsapp: websocket.WebSocketApp, message: str):
        print(f'WS > {message}')

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
        

    def logout(self) -> bool:
        if not self.logged_in:
            return False
        
        response = self._api('POST', f'/v1/auth/web/logout')
        print(response)
        print(response.text)
        self.ws.close()

        self.logged_in = False
        return True