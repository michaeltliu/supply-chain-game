from enum import Enum

class Failure(Enum):
    ROOM_CODE_NOT_FOUND = "Room code not found"
    REQUIRES_OWNER = "Requires owner permissions"
    PLAYER_ID_NOT_FOUND = "Player not found"
    EMPTY_PLAYER_NAME = "Empty player name"
    GAME_IN_PROGRESS = "Game already in progress"