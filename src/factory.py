from pydantic import BaseModel
from resources import Recipe, Resource, RECIPES

class FactoryResponse(BaseModel):
    output: Resource

class Factory(FactoryResponse):
    client_id: int
    recipe_index: int = 0
    max_throughput: int = 0
    set_throughput: int = 0

    def recipe(self) -> Recipe:
        return RECIPES[self.output][self.recipe_index]

    def set_recipe_index(self, index: int):
        self.recipe_index = max(0, min(index, len(RECIPES[self.output]) - 1))
        return self.recipe_index

    def update_set_throughput(self, val: int):
        self.set_throughput = max(0, min(val, self.max_throughput))
        return self.set_throughput

    def convertToResponse(self):
        return FactoryResponse(output=self.output)