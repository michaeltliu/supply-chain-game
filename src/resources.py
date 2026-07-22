from enum import Enum

class RawMaterials(str, Enum):
    ALUMINUM = "aluminum"
    COPPER = "copper"
    CROPS = "crops"
    CRUDE_OIL = "crude oil"
    LITHIUM = "lithium"
    LIVESTOCK = "livestock"
    LUMBER = "lumber"
    SILICON = "silicon"
    STEEL = "steel"
    SULFUR = "sulfur"

class RefinedGoods(str, Enum):
    BATTERY = "battery"
    CHEMICALS = "chemicals"
    FERTILIZER = "fertilizer"
    GLASS = "glass"
    PETROLEUM = "petroleum"
    PLASTIC = "plastic"
    SEMICONDUCTOR = "semiconductor"
    TEXTILES = "textile"

class FinishedGoods(str, Enum):
    AIRCRAFT = "aircraft"
    APPAREL = "apparel"
    CAR = "car"
    CONSUMER_STAPLES = "consumer staples"
    DRUG = "drug"
    FOOD = "food"
    HOUSE = "house"
    POWER = "power"
    SMARTPHONE = "smartphone"

Resource = FinishedGoods | RefinedGoods | RawMaterials

FACTORY_NAMES: dict[Resource, str] = {
    RawMaterials.ALUMINUM: 'Aluminum Mine',
    RawMaterials.COPPER: 'Copper Mine',
    RawMaterials.CROPS: 'Farm',
    RawMaterials.CRUDE_OIL: 'Oil Rig',
    RawMaterials.LITHIUM: 'Lithium Mine',
    RawMaterials.LIVESTOCK: 'Farm',
    RawMaterials.LUMBER: 'Lumber Mill',
    RawMaterials.SILICON: 'Silica Mine',
    
}