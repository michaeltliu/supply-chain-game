from enum import Enum
from pydantic import BaseModel

class Labor(str, Enum):
    MANUAL = "manual"
    CORPORATE = "corporate"

class RawMaterials(str, Enum):
    ALUMINUM = "aluminum"
    COAL = "coal"
    COPPER = "copper"
    CROPS = "crops"
    CRUDE_OIL = "crude oil"
    IRON = "iron"
    LITHIUM = "lithium"
    LIVESTOCK = "livestock"
    LUMBER = "lumber"
    SILICON = "silicon"
    SULFUR = "sulfur"

class RefinedGoods(str, Enum):
    BATTERY = "battery"
    CHEMICALS = "chemicals"
    FERTILIZER = "fertilizer"
    GLASS = "glass"
    PETROLEUM = "petroleum"
    PLASTIC = "plastic"
    SEMICONDUCTOR = "semiconductor"
    STEEL = "steel"
    TEXTILES = "textiles"
    WIRING = "wiring"

class FinishedGoods(str, Enum):
    AI = "AI"
    AIRCRAFT = "aircraft"
    APPAREL = "apparel"
    CAR = "car"
    CONSUMER_STAPLES = "consumer staples"
    DRUG = "drug"
    FOOD = "food"
    HOUSE = "house"
    POWER = "power" # TODO: consider balancing power, each fuel type needs different plant
    SMARTPHONE = "smartphone"

Resource = FinishedGoods | RefinedGoods | RawMaterials | Labor


class Recipe(BaseModel):
    inputs: dict[Resource, int]
    label: str = ""

    def max_producible_count(self, res_available: dict[Resource, int]) -> int:
        return min(res_available.get(res, 0) // req for res, req in self.inputs.items())

RECIPES: dict[Resource, list[Recipe]] = {
    # Raw Materials
    RawMaterials.CROPS: [
        Recipe(inputs={Labor.MANUAL: 1, RefinedGoods.FERTILIZER: 1})
    ],
    RawMaterials.LIVESTOCK: [
        Recipe(inputs={Labor.MANUAL: 1, RawMaterials.CROPS: 1})
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
        Recipe(inputs={RawMaterials.SILICON: 1, RefinedGoods.WIRING: 1})
    ],
    RefinedGoods.STEEL: [
        Recipe(inputs={RawMaterials.COAL: 1, RawMaterials.IRON: 1, RawMaterials.SULFUR: 1})
    ],
    RefinedGoods.TEXTILES: [
        Recipe(inputs={RawMaterials.CROPS: 2}, label="Cotton"),
        Recipe(inputs={RawMaterials.LIVESTOCK: 1}, label="Wool")
    ],
    RefinedGoods.WIRING: [
        Recipe(inputs={RawMaterials.COPPER: 1})
    ],

    # Finished Goods
    FinishedGoods.AI: [
        Recipe(inputs={RefinedGoods.SEMICONDUCTOR: 1})
    ],
    FinishedGoods.AIRCRAFT: [
        Recipe(inputs={RawMaterials.ALUMINUM: 4, RefinedGoods.STEEL: 2, RefinedGoods.GLASS: 1, RefinedGoods.SEMICONDUCTOR: 1})
    ],
    FinishedGoods.APPAREL: [
        Recipe(inputs={RefinedGoods.TEXTILES: 1})
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
        Recipe(inputs={RawMaterials.LUMBER: 2, RefinedGoods.GLASS: 1, RefinedGoods.STEEL: 1, RefinedGoods.TEXTILES: 1, RefinedGoods.WIRING: 1})
    ],
    FinishedGoods.POWER: [
        Recipe(inputs={RawMaterials.COAL: 2}, label="Coal"),
        Recipe(inputs={RawMaterials.CROPS: 3}, label="Ethanol"),
        Recipe(inputs={RefinedGoods.PETROLEUM: 1}, label="Petroleum")
    ],
    FinishedGoods.SMARTPHONE: [
        Recipe(inputs={RawMaterials.ALUMINUM: 1, RefinedGoods.BATTERY: 1, RefinedGoods.SEMICONDUCTOR: 1})
    ]
}

RESOURCE_RND_COSTS: dict[Resource, tuple[int]] = {
    RawMaterials.ALUMINUM: (60, 30),
    RawMaterials.COAL: (40, 20),
    RawMaterials.COPPER: (60, 30),
    RawMaterials.CROPS: (40, 20),
    RawMaterials.CRUDE_OIL: (60, 30),
    RawMaterials.IRON: (40, 20),
    RawMaterials.LITHIUM: (60, 30),
    RawMaterials.LIVESTOCK: (40, 20),
    RawMaterials.LUMBER: (40, 20),
    RawMaterials.SILICON: (60, 30),
    RawMaterials.SULFUR: (60, 30),
    RefinedGoods.BATTERY: (350, 250),
    RefinedGoods.CHEMICALS: (300, 200),
    RefinedGoods.FERTILIZER: (100, 50),
    RefinedGoods.GLASS: (100, 50),
    RefinedGoods.PETROLEUM: (250, 100),
    RefinedGoods.PLASTIC: (350, 150),
    RefinedGoods.SEMICONDUCTOR: (1000, 750),
    RefinedGoods.STEEL: (100, 50),
    RefinedGoods.TEXTILES: (60, 30),
    RefinedGoods.WIRING: (100, 50),
    FinishedGoods.AI: (10000, 5000),
    FinishedGoods.AIRCRAFT: (7500, 2500),
    FinishedGoods.APPAREL: (750, 500),
    FinishedGoods.CAR: (4000, 2000),
    FinishedGoods.CONSUMER_STAPLES: (1000, 250),
    FinishedGoods.DRUG: (5000, 4000),
    FinishedGoods.FOOD: (750, 250),
    FinishedGoods.HOUSE: (1000, 250),
    FinishedGoods.POWER: (2500, 1000),
    FinishedGoods.SMARTPHONE: (5000, 2500)
}