from pydantic import BaseModel
from resources import FinishedGoods, RawMaterials, RefinedGoods, Resource

class Recipe(BaseModel):
    inputs: dict[Resource, int]
    label: str = ""

    def max_producible_count(self, res_available: dict[Resource, int]) -> int:
        return min(res_available.get(res, 0) // req for res, req in self.inputs.items())

RECIPES: dict[Resource, list[Recipe]] = {
    # Raw Materials
    RawMaterials.CROPS: [
        Recipe(inputs={RefinedGoods.FERTILIZER: 1})
    ],
    RawMaterials.LIVESTOCK: [
        Recipe(inputs={RawMaterials.CROPS: 1})
    ],

    # Refined Goods
    RefinedGoods.BATTERY: [
        Recipe(inputs={RawMaterials.COPPER: 1, RawMaterials.LITHIUM: 1})
    ],
    RefinedGoods.CHEMICALS: [
        Recipe(inputs={RawMaterials.CRUDE_OIL: 1, RawMaterials.SULFUR: 1})
    ],
    RefinedGoods.FERTILIZER: [
        Recipe(inputs={RawMaterials.SULFUR: 1})
    ],
    RefinedGoods.GLASS: [
        Recipe(inputs={RawMaterials.SILICON: 1})
    ],
    RefinedGoods.PETROLEUM: [
        Recipe(inputs={RawMaterials.CRUDE_OIL: 1})
    ],
    RefinedGoods.PLASTIC: [
        Recipe(inputs={RawMaterials.CRUDE_OIL: 1})
    ],
    RefinedGoods.SEMICONDUCTOR: [
        Recipe(inputs={RawMaterials.COPPER: 1, RawMaterials.SILICON: 1})
    ],
    RefinedGoods.TEXTILES: [
        Recipe(inputs={RawMaterials.CROPS: 2}, label="Cotton"),
        Recipe(inputs={RawMaterials.LIVESTOCK: 1}, label="Wool")
    ],

    # Finished Goods
    FinishedGoods.AIRCRAFT: [
        Recipe(inputs={RawMaterials.ALUMINUM: 4, RawMaterials.STEEL: 3, RefinedGoods.GLASS: 1, RefinedGoods.SEMICONDUCTOR: 1})
    ],
    FinishedGoods.APPAREL: [
        Recipe(inputs={RefinedGoods.PLASTIC: 1, RefinedGoods.TEXTILES: 1})
    ],
    FinishedGoods.CAR: [
        Recipe(inputs={RawMaterials.ALUMINUM: 1, RefinedGoods.BATTERY: 1, RefinedGoods.CHEMICALS: 1, RefinedGoods.GLASS: 1, RefinedGoods.PLASTIC: 1})
    ],
    FinishedGoods.CONSUMER_STAPLES: [
        Recipe(inputs={RefinedGoods.PLASTIC: 2}, label="Home storage"),
        Recipe(inputs={RefinedGoods.CHEMICALS: 1, RefinedGoods.PLASTIC: 1}, label="Detergent"),
        Recipe(inputs={RawMaterials.LUMBER: 1, RefinedGoods.CHEMICALS: 1}, label="Paper")
    ],
    FinishedGoods.DRUG: [
        Recipe(inputs={RefinedGoods.CHEMICALS: 1, RefinedGoods.TEXTILES: 1})
    ],
    FinishedGoods.FOOD: [
        Recipe(inputs={RawMaterials.CROPS: 3}, label="Corn"),
        Recipe(inputs={RawMaterials.LIVESTOCK: 2}, label="Mutton"),
        Recipe(inputs={RawMaterials.CROPS: 1, RawMaterials.LIVESTOCK: 1}, label="Combo meal")
    ],
    FinishedGoods.HOUSE: [
        Recipe(inputs={RawMaterials.COPPER: 1, RawMaterials.LUMBER: 2, RawMaterials.STEEL: 1, RefinedGoods.GLASS: 1, RefinedGoods.TEXTILES: 1})
    ],
    FinishedGoods.POWER: [
        Recipe(inputs={RawMaterials.CROPS: 3}, label="Biomass"),
        Recipe(inputs={RefinedGoods.PETROLEUM: 1}, label="Petroleum")
    ],
    FinishedGoods.SMARTPHONE: [
        Recipe(inputs={RawMaterials.ALUMINUM: 1, RefinedGoods.BATTERY: 1, RefinedGoods.SEMICONDUCTOR: 1})
    ]
}