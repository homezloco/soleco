from typing import Optional, TypeVar

T = TypeVar('T')

class ResponseHandler:
    def __init__(self, response_manager: Optional['SolanaResponseManager'] = None):
        self.response_manager = response_manager

class SolanaResponseManager:
    pass
