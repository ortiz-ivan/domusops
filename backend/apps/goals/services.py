from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from .models import SavingsGoal


def add_contribution(goal_id: int, amount: Decimal) -> SavingsGoal:
    with transaction.atomic():
        goal = SavingsGoal.objects.select_for_update().get(id=goal_id)

        if not goal.is_active:
            raise ValueError("No se puede aportar a una meta inactiva")

        if amount <= Decimal("0"):
            raise ValueError("El aporte debe ser mayor a 0")

        goal.current_amount += amount
        goal.save()

        return goal


def get_goal_progress(goal: SavingsGoal) -> dict[str, Any]:
    remaining = max(goal.target_amount - goal.current_amount, Decimal("0"))

    if goal.target_amount > 0:
        pct = min(float(goal.current_amount / goal.target_amount * 100), 100.0)
    else:
        pct = 0.0

    days_left = None
    daily_required = None
    monthly_required = None

    if goal.target_date:
        today = timezone.localdate()
        days_left = (goal.target_date - today).days

        if days_left > 0 and remaining > 0:
            daily_required = round(remaining / Decimal(days_left), 2)
            monthly_required = round(daily_required * Decimal("30.4375"), 2)

    return {
        "progress_pct": round(pct, 1),
        "remaining": remaining,
        "days_left": days_left,
        "is_completed": goal.current_amount >= goal.target_amount,
        "daily_required": daily_required,
        "monthly_required": monthly_required,
    }
