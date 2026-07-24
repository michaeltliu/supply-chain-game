from collections.abc import Iterable
from factory import Factory, FactoryResponse
from orderbook import Orderbook, OrderbookResponse, PlayerOrder
from pydantic import BaseModel, Field
from resources import Resource, BASE_FACTORY_COST, TOOLING_BUILD_COSTS
import math
import random

DEBT_TRANCHES = [
    (0, 10000, 0.0),
    (10000, 25000, 0.01),
    (25000, 100000, 0.02),
    (100000, float('inf'), 0.035),
]

class Game(BaseModel):
    round_num: int = 0
    players: dict[str, Player] = Field(default_factory=dict)
    orderbooks: dict[Resource, Orderbook] = Field(default_factory=dict)
    cpi: float | None = None
    interest_rate: float = 0
    open_auctions: list[Auction] = Field(default_factory=list)
    waiting_on: set[str] = Field(default_factory=set) # player names

    def start_game(self):
        self.interest_rate = random.gauss(5, 1.5)
        self.end_round()

    def get_player_auction_bids(self, player_id: str) -> list[int | None]:
        return [a.bids.get(player_id) for a in self.open_auctions]

    def submit_player_orderbook_order(
        self,
        player_id: str,
        resource: Resource,
        order: PlayerOrder
    ):
        self.orderbooks[resource].player_orders[player_id] = order

    def submit_player_auction_bids(self, player_id: str, bids: dict[int, int]):
        l = len(self.open_auctions)
        for auction_idx, bid in bids.items():
            if auction_idx < l:
                self.open_auctions[auction_idx].bids[player_id] = bid

    def end_round(self):
        # Resolve all resource orderbooks
        for res, book in self.orderbooks.items():
            resolved = book.resolve_player_orders()
            for player_id, (inv_delta, cash_delta) in resolved.items():
                p = self.players[player_id]
                p.inventory[res] += inv_delta
                p.cash += cash_delta

        # Resolve all open auctions
        for auction in self.open_auctions:
            winner_id, bid = auction.resolve_auction()
            if not winner_id:
                continue
            contract = auction.contract
            contract.payout = bid
            self.players[winner_id].contracts.append(contract)
        self.open_auctions.clear()

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
        # TODO: Add new contract auctions
        self.round_num += 1
        self.waiting_on = set(p.name for p in self.players.values())

    def convertToResponse(self, player_id: str) -> GameResponse:
        return GameResponse(
            round_num=self.round_num,
            player_self=self.players.get(player_id),
            player_others=list(
                p.convertToResponse() for pid, p in self.players.items()
                if pid != player_id),
            orderbooks={res: book.convertToResponse() for res, book in self.orderbooks.items()},
            cpi=self.cpi,
            interest_rate=self.interest_rate,
            open_auctions=[auction.convertToResponse() for auction in self.open_auctions],
            waiting_on=self.waiting_on
        )

class GameResponse(BaseModel):
    round_num: int
    player_self: Player | None
    player_others: list[PlayerResponse]
    orderbooks: dict[Resource, OrderbookResponse]
    cpi: float | None
    interest_rate: float
    open_auctions: list[AuctionResponse]
    waiting_on: set[str]

class Player(BaseModel):
    name: str
    cash: int = 1000
    contracts: list[Contract] = Field(default_factory=list)
    inventory: dict[Resource, int] = Field(default_factory=dict)
    factories: dict[int, Factory] = Field(default_factory=dict)
    resource_qual: dict[Resource, float] = Field(default_factory=dict)
    rnd: dict[Resource, int] = Field(default_factory=dict)
    tooling_inventory: dict[Resource, int] = Field(default_factory=dict)

    def _validate_and_consume_factory_resources(
        self,
        outputs: Iterable[Resource],
        additional_cost: dict[Resource, int] = {},
    ) -> dict:
        """Verifies that the player has enough resources/tooling inventory to
        build the requested tooling. Provide additional_cost if the base
        factory also needs to be built. Only consumes the resources if
        validation is successful."""

        cost = dict(additional_cost)
        output_counts: dict[Resource, int] = {}
        for output in outputs:
            output_counts[output] = output_counts.get(output, 0) + 1

        tooling_used: dict[Resource, int] = {}
        for output, count in output_counts.items():
            tooling_used[output] = min(
                count,
                self.tooling_inventory.get(output, 0),
            )
            tooling_to_build = count - tooling_used[output]
            for resource, quantity in TOOLING_BUILD_COSTS[output].items():
                cost[resource] = cost.get(resource, 0) + tooling_to_build * quantity

        shortages = {
            resource: shortage
            for resource, required in cost.items()
            if (shortage := required - self.inventory.get(resource, 0)) > 0
        }
        if shortages:
            return shortages

        for resource, required in cost.items():
            self.inventory[resource] -= required
        for output, quantity in tooling_used.items():
            self.tooling_inventory[output] -= quantity
        return {}

    def build_factories(self, factories: dict[int, Resource]) -> dict[Resource, int]:
        valid_builds = {
            k: v for k, v in factories.items()
            if k not in self.factories
        }

        cost: dict[Resource, int] = {
            res: qty * len(valid_builds)
            for res, qty in BASE_FACTORY_COST.items()
        }
        shortages = self._validate_and_consume_factory_resources(
            valid_builds.values(), cost
        )
        if shortages:
            return shortages

        for client_id, res in valid_builds.items():
            self.factories[client_id] = Factory(output=res, client_id=client_id)
        return {}

    def retool_factories(self, factories: dict[int, Resource]) -> dict[Resource, int]:
        valid_retools = {
            client_id: new_output
            for client_id, new_output in factories.items()
            if client_id in self.factories
            and self.factories[client_id].output != new_output
        }

        shortages = self._validate_and_consume_factory_resources(valid_retools.values())
        if shortages:
            return shortages

        for client_id, new_output in valid_retools.items():
            factory = self.factories[client_id]
            old_output = factory.output
            factory.output = new_output
            self.tooling_inventory[old_output] = self.tooling_inventory.get(old_output, 0) + 1
        return {}

    def resolve_production(self) -> dict[Resource, int]:
        """Runs all of a player's factories for one round, in the correct dependency order,
        updates self.inventory, and returns the net change."""
        factories = self.factories.values()
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
            contracts=[c.convertToResponse() for c in self.contracts],
            inventory_log_floor={res: int(math.log10(qty)) for res, qty in self.inventory.items()},
            factories=list(f.convertToResponse() for f in self.factories.values()),
            resource_qual=self.resource_qual
        )

class PlayerResponse(BaseModel):
    name: str
    cash_log_floor: int
    contracts: list[ContractResponse]
    inventory_log_floor: dict[Resource, int]
    factories: list[FactoryResponse] # TODO: mask some Factory information when structure is finalized
    resource_qual: dict[Resource, float]

class ContractResponse(BaseModel):
    resource: Resource
    counterparty: str
    completion_due_round: int
    total_size: int
    missing_penalty_per_unit: int
    payout: int = 0
    payout_schedule: list[tuple[int, float]]

class Contract(ContractResponse):
    size_completed: int = 0

    def convertToResponse(self) -> ContractResponse:
        return ContractResponse(**self.model_dump())

class AuctionResponse(BaseModel):
    contract: ContractResponse
    starting_price: int
    own_bid: int | None

class Auction(BaseModel):
    contract: Contract
    starting_price: int
    bids: dict[str, int] = Field(default_factory=dict)

    def resolve_auction(self) -> tuple[str, int]:
        # TODO: integrate players' resource quality into the decision?
        first_price = self.starting_price
        second_price = float('inf')
        winner_id = ""
        for player_id, bid in self.bids.items():
            if bid < first_price:
                second_price = first_price
                first_price = bid
                winner_id = player_id
            elif bid < second_price:
                second_price = bid
        return winner_id, second_price

    def convertToResponse(self, player_id) -> AuctionResponse:
        return AuctionResponse(
            contract=self.contract.convertToResponse(),
            starting_price=self.starting_price,
            own_bid=self.bids.get(player_id)
        )
