from game import Game, Player
from pydantic import BaseModel, Field

class Room(BaseModel):
    owner_id: str
    join_code: str
    game: Game = Field(default_factory=Game)

    def add_player(self, player_id: str, name: str) -> Room:
        self.game.players[player_id] = Player(name=name)
        return self