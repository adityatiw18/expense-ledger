from decimal import Decimal

from sqlalchemy.orm import Session

from .balance_service import get_balances


def calculate_settlements(
    balances: dict[int, Decimal]
):
    users = [
        (user_id, balance)
        for user_id, balance in balances.items()
        if balance != 0
    ]

    ids = [user_id for user_id, _ in users]
    amounts = [balance for _, balance in users]

    best = None

    def backtrack(start, payments):
        nonlocal best

        while (
            start < len(amounts)
            and amounts[start] == 0
        ):
            start += 1

        if start == len(amounts):
            if (
                best is None
                or len(payments) < len(best)
            ):
                best = payments.copy()

            return

        if (
            best is not None
            and len(payments) >= len(best)
        ):
            return

        for i in range(start + 1, len(amounts)):

            if amounts[i] == 0:
                continue

            if amounts[start] * amounts[i] >= 0:
                continue

            original_start = amounts[start]
            original_i = amounts[i]

            payment_amount = min(
                abs(original_start),
                abs(original_i)
            )

            if original_start < 0:
                payment = (
                    ids[start],
                    ids[i],
                    payment_amount
                )
            else:
                payment = (
                    ids[i],
                    ids[start],
                    payment_amount
                )

            if abs(original_start) <= abs(original_i):
                amounts[i] += original_start
                amounts[start] = Decimal("0")
            else:
                amounts[start] += original_i
                amounts[i] = Decimal("0")

            payments.append(payment)

            backtrack(
                start,
                payments
            )

            payments.pop()

            amounts[start] = original_start
            amounts[i] = original_i

            if original_start + original_i == 0:
                break

    backtrack(0, [])

    return best if best is not None else []


def get_group_settlements(
    db: Session,
    group_id: int
):
    balances = get_balances(
        db,
        group_id
    )

    return calculate_settlements(balances)