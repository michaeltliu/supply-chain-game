from pydantic import BaseModel, ConfigDict
from resources import Resource
from sortedcontainers import SortedDict

class Orderbook(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    resource: Resource
    bids: SortedDict[int, int] # price -> volume
    asks: SortedDict[int, int] # price -> volume
    player_orders: dict[str, PlayerOrder]

    def resolve_player_orders(self) -> dict[str, tuple[int, int]]:
        """Resolve player orders and return inventory and cash deltas by player.

        Each result is ``(inventory_delta, cash_delta)``. Bids therefore
        produce positive inventory and negative cash, while asks produce the
        opposite. Orders at each price level are filled pro rata; indivisible
        remainder units go to the players with the largest fractional
        remainders, with player id used as a deterministic tie-breaker.
        """
        resolved: dict[str, tuple[int, int]] = {}

        def resolve_side(is_bid: bool) -> None:
            book = self.asks if is_bid else self.bids
            prices = list(book.keys())
            if not is_bid:
                prices.reverse()

            for price in prices:
                available = book[price]
                if available <= 0:
                    continue

                eligible = [
                    (player_id, order)
                    for player_id, order in self.player_orders.items()
                    if order.is_bid == is_bid
                    and order.max_volume > 0
                    and (
                        order.limit_price >= price if is_bid else
                        order.limit_price <= price
                    )
                ]
                if not eligible:
                    break

                requested = sum(order.max_volume for _, order in eligible)
                fill_volume = min(available, requested)

                if requested <= available:
                    allocations = {
                        player_id: order.max_volume
                        for player_id, order in eligible
                    }
                else:
                    allocations = {}
                    remainders: list[tuple[int, str]] = []
                    allocated = 0
                    for player_id, order in eligible:
                        numerator = order.max_volume * fill_volume
                        allocation, remainder = divmod(numerator, requested)
                        allocations[player_id] = allocation
                        allocated += allocation
                        remainders.append((remainder, player_id))

                    for _, player_id in sorted(
                        remainders, key=lambda item: (-item[0], item[1])
                    )[:fill_volume - allocated]:
                        allocations[player_id] += 1

                for player_id, order in eligible:
                    volume = allocations[player_id]
                    if volume == 0:
                        continue
                    order.max_volume -= volume
                    inventory_delta = volume if is_bid else -volume
                    cash_delta = -volume * price if is_bid else volume * price
                    old_inventory, old_cash = resolved.get(player_id, (0, 0))
                    resolved[player_id] = (
                        old_inventory + inventory_delta,
                        old_cash + cash_delta,
                    )

                remaining = available - fill_volume
                if remaining:
                    book[price] = remaining
                else:
                    del book[price]

        resolve_side(is_bid=True)
        resolve_side(is_bid=False)
        self.player_orders.clear()
        return resolved

class PlayerOrder(BaseModel):
    is_bid: bool
    limit_price: int
    max_volume: int