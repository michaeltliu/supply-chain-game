from factory import Factory
from orderbook import Orderbook, OrderbookResponse, PlayerOrder
from pydantic import BaseModel, Field
from resources import Resource
import math
import random

DEBT_TRANCHES = [
    (0, 10000, 0.0),
    (10000, 25000, 0.01),
    (25000, 100000, 0.02),
    (100000, float('inf'), 0.035),
]

class Game(BaseModel):
    players: dict[str, Player] = Field(default_factory=dict)
    orderbooks: dict[Resource, Orderbook] = Field(default_factory=dict)
    cpi: float | None = None
    interest_rate: float = 0
    round_num: int = 0
    waiting_on: set[str] = Field(default_factory=set)

    def start_game(self):
        self.interest_rate = random.gauss(5, 1.5)
        self.end_round()

    def submit_player_orderbook_order(self, player_id: str, resource: Resource, order: PlayerOrder):
        self.orderbooks[resource].player_orders[player_id] = order

    def end_round(self):
        # Resolve all resource orderbooks
        for res, book in self.orderbooks.items():
            resolved = book.resolve_player_orders()
            for player_id, (inv_delta, cash_delta) in resolved.items():
                p = self.players[player_id]
                p.inventory[res] += inv_delta
                p.cash += cash_delta

        # Apply interest to all players' cash/debt
        for player in self.players.values():
            if player.cash >= 0:
                player.cash = round(player.cash * math.exp(self.interest_rate / 4))
            else:
                debt = -player.cash
                new_debt = 0
                for lower, upper, rate_add in DEBT_TRANCHES:
                    if debt > lower:
                        tranche_amount = min(debt, upper) - lower
                        r = self.interest_rate + rate_add
                        new_debt += tranche_amount * math.exp(r / 4)
                    else:
                        break
                player.cash = -round(new_debt)

        # TODO: Compute CPI
        # TODO: Fed decision
        # TODO: Add NPC order flow
        self.round_num += 1
        self.waiting_on = set(p.name for p in self.players)

    def convertToResponse(self, player_id: str) -> GameResponse:
        return GameResponse(
            player_self=self.players.get(player_id),
            player_others=list(
                p.convertToResponse() for pid, p in self.players.items()
                if pid != player_id),
            orderbooks={res: book.convertToResponse() for res, book in self.orderbooks.items()},
            cpi=self.cpi,
            interest_rate=self.interest_rate,
            round_num=self.round_num,
            waiting_on=self.waiting_on
        )

class GameResponse(BaseModel):
    player_self: Player | None
    player_others: list[PlayerResponse]
    orderbooks: dict[Resource, OrderbookResponse]
    cpi: float | None
    interest_rate: float
    round_num: int
    waiting_on: set[str]

class Player(BaseModel):
    name: str
    cash: int = 1000
    contracts: list[Contract] = Field(default_factory=list)
    inventory: dict[Resource, int] = Field(default_factory=dict)
    factories: list[Factory] = Field(default_factory=list)
    resource_qual: dict[Resource, float] = Field(default_factory=dict)
    rnd: dict[Resource, int] = Field(default_factory=dict)
    tooling_inventory: dict[Resource, int] = Field(default_factory=dict)

    def build_factory(self, resource: Resource):
        self.factories.append(self, resource)
        self.cash -= 200 # TODO: convert this to manual labor

    def resolve_production(self) -> dict[Resource, int]:
        """Runs all of a player's factories for one round, in the correct dependency order,
        updates self.inventory, and returns the net change."""
        factories = self.factories
        outputs = {f.output for f in factories} # outputs actually produced by player's factories

        dependents: dict[Resource, set[Resource]] = {o: set() for o in outputs}
        in_degree: dict[Resource, int] = {o: 0 for o in outputs}
        for f in factories:
            for ingredient in f.recipe().inputs:
                if ingredient in outputs and ingredient != f.output:
                    dependents[ingredient].add(f.output)
                    in_degree[f.output] += 1

        queue = [g for g, deg in in_degree.items() if deg == 0]
        order: list[Resource] = [] # topologically sorted ordering
        while queue:
            res = queue.pop(0)
            order.append(res)
            for nxt in dependents[res]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(order) != len(outputs):
            stuck = outputs - set(order)
            raise ValueError(f"Cycle detected in {self.name}'s factories: {stuck}")

        factories_by_output: dict[Resource, list[Factory]] = {o: [] for o in outputs}
        for f in factories:
            factories_by_output[f.output].append(f)

        net_change: dict[Resource, int] = dict()
        for res in order:
            for f in factories_by_output[res]:
                r = f.recipe()
                units = min(f.set_throughput, r.max_producible_count(self.inventory))
                if units <= 0:
                    continue
                for ing, req in r.inputs.items():
                    self.inventory[ing] -= req * units
                    net_change[ing] -= req * units
                self.inventory[res] += units
                net_change[res] += units

        return net_change

    def convertToResponse(self):
        return PlayerResponse(
            name=self.name,
            cash_log_floor=int(math.log10(self.cash)),
            contracts=self.contracts,
            inventory_log_floor={res: int(math.log10(qty)) for res, qty in self.inventory.items()},
            factories=self.factories
        )

class PlayerResponse(BaseModel):
    name: str
    cash_log_floor: int
    contracts: list[Contract]
    inventory_log_floor: dict[Resource, int]
    factories: list[Factory] # TODO: mask some Factory information when structure is finalized

class Contract(BaseModel):
    resource: Resource
    counterparty: str
    completion_due_round: int
    size: int
    total_payout: int
    payout_schedule: list[tuple[int, int]]
    missing_penalty_per_unit: int
    size_completed: int = 0