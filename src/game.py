from orderbook import Orderbook
from pydantic import BaseModel, Field
from recipe import Recipe, RECIPES
from resources import Resource
from sortedcontainers import SortedDict

class Game(BaseModel):
    players: dict[str, Player] = Field(default_factory=dict)
    orderbook: dict[Resource, Orderbook] = Field(default_factory=dict)
    round_num: int = 0
    waiting_on: set[str] = Field(default_factory=set)

    def end_round(self):
        self.round_num += 1

class Player(BaseModel):
    name: str
    cash: int = 1000
    inventory: dict[Resource, int] = Field(default_factory=dict)
    factories: list[Factory] = Field(default_factory=list)

    def build_factory(self, resource: Resource):
        self.factories.append(self, resource)
        self.cash -= 100

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

class Factory(BaseModel):
    output: Resource
    recipe_index: int = 0
    max_throughput: int = 0
    set_throughput: int = 0

    def recipe(self) -> Recipe:
        return RECIPES[self.output][self.recipe_index]

    def set_recipe_index(self, index: int):
        self.recipe_index = max(0, min(index, len(RECIPES[self.output]) - 1))

    def update_set_throughput(self, val: int):
        self.set_throughput = max(0, min(val, self.max_throughput))
