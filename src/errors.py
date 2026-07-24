from enum import Enum
from resources import Resource

class InsufficientInventory(Exception):
    def __init__(self, shortages: dict[Resource, int]):
        self.shortages = shortages

class InvalidAuctionParams(Exception):
    def __init__(self, bad_index: bool = False):
        self.bad_index = bad_index

class NonuniqueClientID(Exception):
    def __init__(self, overlap: set[int]):
        self.overlap = overlap

class Failure(Enum):
    ROOM_CODE_NOT_FOUND = "Room code not found"
    REQUIRES_OWNER = "Requires owner permissions"
    PLAYER_ID_NOT_FOUND = "Player not found"
    EMPTY_PLAYER_NAME = "Empty player name"
    GAME_IN_PROGRESS = "Game already in progress"
    NAME_TAKEN = "Name taken"
    WRONG_ROUND = "Wrong round"
    INSUFFICIENT_INVENTORY = "Insufficient inventory"