from __future__ import annotations

import json
import re
from typing import Optional, Type, Callable

from aiohttp.abc import Request
from aiohttp.web_response import Response
from maubot import Plugin
from maubot.handlers import web
from mautrix.types import RoomID, MessageType
from mautrix.util.config import ConfigUpdateHelper, BaseProxyConfig


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy_dict("endpoints")
        helper.copy('tokens')


class WebhookBot(Plugin):
    param_matcher: re.Pattern

    async def start(self) -> None:
        self.log.info('Starting webhook bot!')

        self.log.info('Loading config...')
        self.config.load_and_update()

        self.log.info('Compiling regex...')
        self.param_matcher = re.compile('\\${([^}]+)}')

        self.log.info('Initialised!')

    def validate_token(self, req: Request) -> bool:
        request_token = req.query['token']
        valid_tokens: list = self.config.get('tokens', [])
        return request_token in valid_tokens

    def get_endpoint(self, name) -> Optional[dict]:
        data: dict = self.config.get("endpoints", {})
        if name in data.keys():
            return data[name]
        else:
            return None

    def format_message(self, endpoint: dict, lookup: Callable[[str], any]) -> str:
        template = endpoint.get('template')

        params = self.param_matcher.findall(template)
        msg_content = template

        for param_name in params:
            replacement = lookup(param_name)
            if replacement is None:
                replacement = '(???)'
            msg_content = msg_content.replace(f'${{{param_name}}}', replacement)

        return msg_content

    @web.get("/get/{endpoint}")
    async def execute_get(self, req: Request) -> Response:
        endpoint_name = req.match_info["endpoint"]
        endpoint = self.get_endpoint(endpoint_name)
        self.log.info(f"Received webhook endpoint {endpoint_name}")

        if not self.validate_token(req):
            self.log.error(f'Endpoint {endpoint_name} called with invalid token!')
            return Response(status=403)

        if endpoint.get('methods') is None or 'GET' not in endpoint.get('methods'):
            self.log.error(f'Endpoint {endpoint_name} may not receive GET requests')
            return Response(status=403)

        if endpoint is None:
            self.log.error(f'Endpoint {endpoint_name} does not exist')
            return Response(status=404)

        def lookup(key: str) -> str:
            value = req.query.get(key)
            return value

        msg = self.format_message(endpoint, lookup)
        room = RoomID(endpoint.get('room_id'))

        try:
            await self.client.send_markdown(room, msg, allow_html=True,
                                            msgtype=MessageType.NOTICE if endpoint.get('notice') else MessageType.TEXT)
        except Exception as e:
            self.log.error(f'Failed to send message {msg}: {e}')
            return Response(status=500)

        return Response(status=404)

    @web.post("/post/{endpoint}")
    async def execute_post(self, req: Request) -> Response:
        data: str = await req.text()
        endpoint_name = req.match_info["endpoint"]
        self.log.info(f"Received webhook endpoint {endpoint_name}")
        endpoint = self.get_endpoint(endpoint_name)

        if not self.validate_token(req):
            self.log.error(f'Endpoint {endpoint_name} called with invalid token!')
            return Response(status=403)

        if endpoint.get('methods') is None or 'POST' not in endpoint.get('methods'):
            self.log.error(f'Endpoint {endpoint_name} may not receive POST requests')
            return Response(status=403)

        if endpoint is None:
            return Response(status=404)

        if endpoint.get('format') == 'JSON':
            data: dict = json.loads(data)

            def lookup_json(key: str):
                parts = key.split('.')
                pointer = data

                for part in parts:
                    if pointer is None:
                        return None
                    if '[' in part and ']' in part:
                        # array index assumed here!

                        try:
                            arr_parts = part.split('[')
                            pointer = pointer[arr_parts[0]]
                            arr_index = int(arr_parts[1].split(']')[0])
                            pointer = pointer[arr_index]
                        except (KeyError, IndexError):
                            self.log.error(f'Unknown or invalid key {part}')
                            return None
                    else:
                        try:
                            pointer = pointer[part]
                        except KeyError:
                            self.log.error(f'Unknown or invalid key {part}')
                            return None

                if pointer is not None and not isinstance(pointer, str):
                    pointer = str(pointer)
                return pointer

            msg = self.format_message(endpoint, lookup_json)
        else:
            msg = self.format_message(endpoint, lambda x: None)

        room = RoomID(endpoint.get('room_id'))

        try:
            msg = await self.client.send_markdown(room, msg, allow_html=True,
                                                  msgtype=MessageType.NOTICE if endpoint.get(
                                                      'notice') else MessageType.TEXT)
        except Exception as e:
            self.log.error(f'Failed to send message {msg}: {e}')
            return Response(status=500)

        return Response(status=200)

    @classmethod
    def get_config_class(cls) -> Type['BaseProxyConfig']:
        return Config
