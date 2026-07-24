from errors import (
    Failure,
    InsufficientInventory,
    InvalidAuctionParams,
    NonuniqueClientID
)
from fastapi import FastAPI, Header, Request
from game import GameResponse, Player
from pydantic import BaseModel, Field
from resources import Resource
from room import Room
from typing import Annotated, Optional
import redis_store
import uuid

app = FastAPI()

@app.exception_handler(InsufficientInventory)
async def insufficient_inventory_handler(_request: Request, exc: InsufficientInventory):
    return {
        'success': False,
        'failure_msg': 'INSUFFICIENT_INVENTORY',
        'shortages': exc.shortages
    }

@app.exception_handler(InvalidAuctionParams)
async def invalid_auction_params_handler(_request: Request, exc: InvalidAuctionParams):
    return {
        'success': False,
        'failure_msg': 'INVALID_AUCTION_PARAMS',
        'bad_index': exc.bad_index,
    }

@app.exception_handler(NonuniqueClientID)
async def nonunique_client_id_handler(_request: Request, exc: NonuniqueClientID):
    return {
        'success': False,
        'failure_msg': 'NONUNIQUE_CLIENT_ID',
        'overlap': exc.overlap
    }

class CreateRoomRequest(BaseModel):
    player_name: str

@app.post("/create-room")
async def create_room(request: CreateRoomRequest):
    if not request.player_name:
        return {'success': False, 'failure_msg': Failure.EMPTY_PLAYER_NAME}
    owner_id = str(uuid.uuid4())
    room = await redis_store.create_room_with_unique_code(
        lambda code: Room(owner_id=owner_id, join_code=code).add_player(
            owner_id, request.player_name
        )
    )
    return {'success': True, 'room_code': room.join_code, 'player_id': owner_id}

class JoinRoomRequest(BaseModel):
    player_name: str

@app.post("/join-room/{room_code}")
async def join_room(room_code: str, request: JoinRoomRequest):
    if not request.player_name:
        return {'success': False, 'failure_msg': Failure.EMPTY_PLAYER_NAME}
    async with redis_store.room_lock(room_code):
        room = await redis_store.load_room(room_code)
        if room is None:
            return {'success': False, 'failure_msg': Failure.ROOM_CODE_NOT_FOUND}
        if request.player_name.strip() in {m.name.strip() for m in room.game.players.values()}:
            return {'success': False, 'failure_msg': Failure.NAME_TAKEN}
        if room.game.round_num > 0:
            return {'success': False, 'failure_msg': Failure.GAME_IN_PROGRESS}
        player_id = str(uuid.uuid4())
        room.add_player(player_id, request.player_name)
        await redis_store.save_room(room)
    return {'success': True, 'player_id': player_id}

@app.post("/rooms/{room_code}/start-game")
async def start_game(room_code: str, x_player_id: str = Header(...)):
    async with redis_store.room_lock(room_code):
        room = await redis_store.load_room(room_code)
        if room is None:
            return {'success': False, 'failure_msg': Failure.ROOM_CODE_NOT_FOUND}
        if room.owner_id != x_player_id:
            return {'success': False, 'failure_msg': Failure.REQUIRES_OWNER}
        if room.game.round_num > 0:
            return {'success': False, 'failure_msg': Failure.GAME_IN_PROGRESS}
        room.game.start_game()
        await redis_store.save_room(room)
    return {'success': True}

@app.get("/rooms/{room_code}/waiting-poll")
async def room_waiting_poll(room_code: str):
    async with redis_store.room_lock(room_code):
        room = await redis_store.load_room(room_code)
        if room is None:
            return {'success': False, 'failure_msg': Failure.ROOM_CODE_NOT_FOUND}
        return {
            'success': True,
            'round_num': room.game.round_num,
            'waiting_on': room.game.waiting_on
        }

class RoomStateResponse(BaseModel):
    success: bool
    failure_msg: Optional[Failure] = None
    game: GameResponse

@app.get("/rooms/{room_code}/state")
async def room_state(room_code: str, x_player_id: str = Header(...)):
    async with redis_store.room_lock(room_code):
        room = await redis_store.load_room(room_code)
        if room is None:
            return RoomStateResponse(success=False, failure_msg=Failure.ROOM_CODE_NOT_FOUND)
        return RoomStateResponse(
            success=True,
            game=room.game.convertToResponse(x_player_id)
        )

ClientID = Annotated[int, Field(ge=0, lt=2**31)]
NonNegativeInt = Annotated[int, Field(ge=0)]

class PlayerTurnRequest(BaseModel):
    round_num: int = Field(gt=0)
    build_factories: dict[ClientID, Resource] = Field(default_factory=dict)
    retool_factories: dict[ClientID, Resource] = Field(default_factory=dict)
    rnd: dict[Resource, int] = Field(default_factory=dict)
    auction_bids: dict[NonNegativeInt, NonNegativeInt] = Field(default_factory=dict)

class PlayerTurnResponse(BaseModel):
    success: bool
    failure_msg: Optional[Failure] = None
    new_player_data: Player
    auction_bids: list[int] = Field(default_factory=list)
    build_shortages: dict[Resource, int] = Field(default_factory=dict)
    retool_shortages: dict[Resource, int] = Field(default_factory=dict)

@app.post("/rooms/{room_code}/player-turn", response_model=PlayerTurnResponse)
async def player_turn(
    room_code: str,
    request: PlayerTurnRequest,
    x_player_id: str = Header(...)
) -> PlayerTurnResponse:
    async with redis_store.room_lock(room_code):
        room = await redis_store.load_room(room_code)
        if room is None:
            return PlayerTurnResponse(success=False, failure_msg=Failure.ROOM_CODE_NOT_FOUND)
        if x_player_id not in room.game.players:
            return PlayerTurnResponse(success=False, failure_msg=Failure.PLAYER_ID_NOT_FOUND)
        if request.round_num != room.game.round_num:
            return PlayerTurnResponse(success=False, failure_msg=Failure.WRONG_ROUND)

        player = room.game.players[x_player_id]
        build_shortages = player.build_factories(request.build_factories)
        if build_shortages:
            return PlayerTurnResponse(
                success=False,
                failure_msg=Failure.INSUFFICIENT_INVENTORY,
                new_player_data=player,
                build_shortages=build_shortages
            )
        retool_shortages = player.retool_factories(request.retool_factories)
        if retool_shortages:
            return PlayerTurnResponse(
                success=False,
                failure_msg=Failure.INSUFFICIENT_INVENTORY,
                new_player_data=player,
                retool_shortages=retool_shortages
            )
        room.game.submit_player_auction_bids(request.auction_bids)
        return PlayerTurnResponse(
            success=True,
            new_player_data=player,
            auction_bids=room.game.get_player_auction_bids(x_player_id)
        )