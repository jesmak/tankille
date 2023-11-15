import logging
from typing import Optional

import requests
from requests import ConnectTimeout, RequestException

from .const import USER_AGENT, API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class TankilleException(Exception):
    """Base exception for Tankille"""


class TankilleSession:
    _device: str
    _username: str
    _password: str
    _timeout: int
    _refreshToken: str
    _accessToken: str
    _location: str
    _language: str
    _distance: int

    def __init__(self, language: str, device: str, username: str, password: str, lat: float, lon: float, distance: int, timeout=20):
        self._device = device
        self._username = username
        self._password = password
        self._location = f"{lon:.4f}%2C{lat:.4f}"
        self._language = language
        self._distance = distance
        self._timeout = timeout

    def authenticate(self) -> None:
        try:
            session = requests.Session()

            response = session.post(
                url=f"{API_BASE_URL}/auth/login",
                headers={
                    "user-agent": USER_AGENT,
                    "content-type": "application/json; charset=UTF-8",
                    "accept-language": self._language
                },
                timeout=self._timeout,
                data=f"{{\"device\": \"{self._device}\",\"email\":\"{self._username}\",\"password\":\"{self._password}\"}}"
            )

            self._refreshToken = response.json()["refreshToken"]

            print(response.json())

            response = session.post(
                url=f"{API_BASE_URL}/auth/refresh",
                headers={
                    "user-agent": USER_AGENT,
                    "content-type": "application/json; charset=UTF-8",
                    "accept-language": self._language
                },
                timeout=self._timeout,
                data=f"{{\"token\": \"{self._refreshToken}\"}}"
            )

            self._accessToken = response.json()["accessToken"]

            print(response.json())

        except ConnectTimeout as exception:
            raise TankilleException("Timeout error") from exception

        except RequestException as exception:
            raise TankilleException(f"Communication error {exception}") from exception

    def call_api(self, reauthenticated=False) -> Optional[dict]:
        try:
            response = requests.get(
                url=f"{API_BASE_URL}/stations?location={self._location}&distance={self._distance}",
                headers={
                    "user-agent": USER_AGENT,
                    "content-type": "application/json; charset=UTF-8",
                    "accept-language": self._language,
                    "x-access-token": self._accessToken
                },
                timeout=self._timeout,
            )

            if response.status_code == 401 and reauthenticated is False:
                self.authenticate()
                return self.call_api(True)  # avoid reauthentication loops by using the reauthenticated flag

            elif response.status_code != 200:
                raise TankilleException(f"{response.status_code} is not valid")

            else:
                result = response.json() if response else {}
                return result

        except ConnectTimeout as exception:
            raise TankilleException("Timeout error") from exception

        except RequestException as exception:
            raise TankilleException(f"Communication error {exception}") from exception
