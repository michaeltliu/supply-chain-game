from enums import Failure
from fastapi import FastAPI, Header
from game import GameResponse
from pydantic import BaseModel
from resources import Resource
from room import Room
from typing import Optional
import redis_store
import uuid

app = FastAPI()

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

class PlayerTurnRequest(BaseModel):
    build_factories: dict[Resource, int]

class PlayerTurnResponse(BaseModel):
    success: bool
    failure_msg: Optional[Failure] = None

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
    return PlayerTurnResponse(success=True)