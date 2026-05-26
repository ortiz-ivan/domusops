import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Prefetch, Sum
from django.utils import timezone

from apps.configuration.models import (
    InventorySettings,
    get_budget_bucket_ratio_map,
    get_category_fallback_unit_cost,
    get_category_monthly_budget,
)
from apps.expenses.models import FixedExpense, FixedExpensePayment, Income, VariableExpense
from apps.purchases.models import Product, ProductRestock

from .models import FinancialEvent, MonthlyClose


def _normalize_change_reason(reason: Any, default_reason: str = "", required: bool = False) -> str:
    value = str(reason or "").strip()

    if required and not value:
        raise ValueError("Debes indicar el motivo del cambio")

    return value or default_reason


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def _to_json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, dict):
        return {key: _to_json_ready(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_to_json_ready(item) for item in value]

    return value


def _snapshot_income(income: Income) -> dict[str, Any]:
    return _to_json_ready({
        "id": income.id,
        "amount": income.amount,
        "source": income.source,
        "notes": income.notes,
        "date": income.date,
    })


def _snapshot_variable_expense(expense: VariableExpense) -> dict[str, Any]:
    return _to_json_ready({
        "id": expense.id,
        "amount": expense.amount,
        "category": expense.category,
        "budget_bucket": expense.budget_bucket,
        "description": expense.description,
        "notes": expense.notes,
        "date": expense.date,
    })


def _snapshot_fixed_expense(expense: FixedExpense) -> dict[str, Any]:
    return _to_json_ready({
        "id": expense.id,
        "name": expense.name,
        "category": expense.category,
        "budget_bucket": expense.budget_bucket,
        "monthly_amount": expense.monthly_amount,
        "next_due_date": expense.next_due_date,
        "is_active": expense.is_active,
    })


def _snapshot_fixed_payment(payment: FixedExpensePayment) -> dict[str, Any]:
    return _to_json_ready({
        "id": payment.id,
        "fixed_expense_id": payment.fixed_expense_id,
        "fixed_expense_name": payment.fixed_expense.name,
        "amount": payment.amount,
        "date": payment.date,
    })


def _snapshot_monthly_close(monthly_close: MonthlyClose) -> dict[str, Any]:
    return _to_json_ready({
        "id": monthly_close.id,
        "month": monthly_close.month,
        "year": monthly_close.year,
        "notes": monthly_close.notes,
        "summary_snapshot": monthly_close.summary_snapshot,
        "created_at": monthly_close.created_at,
    })


def _record_financial_event(
    *,
    entity_type: str,
    action: str,
    entity_id: int,
    title: str,
    amount: Decimal | float | int,
    effective_date: date | None,
    reason: str = "",
    previous_data: dict[str, Any] | None = None,
    current_data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> FinancialEvent:
    effective_date = effective_date or timezone.localdate()
    return FinancialEvent.objects.create(
        entity_type=entity_type,
        action=action,
        entity_id=entity_id,
        title=title,
        amount=amount,
        effective_date=effective_date,
        month=effective_date.month,
        year=effective_date.year,
        reason=reason,
        previous_data=_to_json_ready(previous_data or {}),
        current_data=_to_json_ready(current_data or {}),
        metadata=_to_json_ready(metadata or {}),
    )


def _add_one_month(target_date: date) -> date:
    year = target_date.year + (1 if target_date.month == 12 else 0)
    month = 1 if target_date.month == 12 else target_date.month + 1
    day = min(target_date.day, calendar.monthrange(year, month)[1])
    return target_date.replace(year=year, month=month, day=day)


def _get_next_month_period(month: int, year: int) -> tuple[int, int]:
    if month == 12:
        return 1, year + 1
    return month + 1, year


def _get_previous_month_period(month: int, year: int) -> tuple[int, int]:
    if month == 1:
        return 12, year - 1
    return month - 1, year


def _ensure_automatic_monthly_close(today: date | None = None) -> "MonthlyClose | None":
    reference_date = today or timezone.localdate()
    previous_month, previous_year = _get_previous_month_period(reference_date.month, reference_date.year)

    if MonthlyClose.objects.filter(month=previous_month, year=previous_year).exists():
        return None

    return create_monthly_close(
        previous_month,
        previous_year,
        notes="Cierre automatico de fin de mes",
        auto_generated=True,
    )


def get_active_financial_period() -> tuple[int, int]:
    _ensure_automatic_monthly_close()
    today = timezone.localdate()
    current_period = (today.year, today.month)
    latest_close = MonthlyClose.objects.order_by("-year", "-month", "-id").first()

    if latest_close is None:
        return today.month, today.year

    next_month, next_year = _get_next_month_period(latest_close.month, latest_close.year)
    next_open_period = (next_year, next_month)

    if next_open_period > current_period:
        return next_month, next_year

    return today.month, today.year


def get_active_financial_date() -> date:
    month, year = get_active_financial_period()
    today = timezone.localdate()

    if today.year == year and today.month == month:
        return today

    return date(year, month, 1)


def _compute_category_breakdown(month: int, year: int, settings_data: dict[str, Any]) -> list[dict[str, Any]]:
    categories_config = {
        item["value"]: item
        for item in settings_data.get("categories", [])
        if item.get("value")
    }

    breakdown = {}

    def get_or_create(category):
        if category not in breakdown:
            cfg = categories_config.get(category, {})
            breakdown[category] = {
                "category": category,
                "label": cfg.get("label", category),
                "budget_bucket": cfg.get("budget_bucket", "needs"),
                "budget": get_category_monthly_budget(settings_data, category),
                "actual": Decimal("0"),
                "variable_expense_total": Decimal("0"),
                "committed_variable_total": Decimal("0"),
                "fixed_payment_total": Decimal("0"),
                "product_restock_total": Decimal("0"),
            }
        return breakdown[category]

    for expense in VariableExpense.objects.filter(date__year=year, date__month=month):
        entry = get_or_create(expense.category or "other")
        amount = _to_decimal(expense.amount)
        if expense.status == VariableExpense.STATUS_COMMITTED:
            entry["committed_variable_total"] += amount
        else:
            entry["variable_expense_total"] += amount
        entry["actual"] += amount

    for payment in FixedExpensePayment.objects.filter(
        fixed_expense__is_active=True,
        date__year=year,
        date__month=month,
    ).select_related("fixed_expense"):
        entry = get_or_create(payment.fixed_expense.category or "other")
        amount = _to_decimal(payment.amount)
        entry["fixed_payment_total"] += amount
        entry["actual"] += amount

    for restock in ProductRestock.objects.filter(
        date__year=year,
        date__month=month,
        unit_cost__isnull=False,
    ).select_related("product"):
        entry = get_or_create(restock.product.category or "other")
        amount = _to_decimal(restock.unit_cost) * _to_decimal(restock.quantity)
        entry["product_restock_total"] += amount
        entry["actual"] += amount

    result = []
    for e in breakdown.values():
        actual = float(round(e["actual"], 2))
        budget = e["budget"]
        remaining = round(budget - actual, 2) if budget is not None else None
        result.append({
            "category": e["category"],
            "label": e["label"],
            "budget_bucket": e["budget_bucket"],
            "budget": budget,
            "actual": actual,
            "remaining": remaining,
            "variable_expense_total": float(round(e["variable_expense_total"], 2)),
            "committed_variable_total": float(round(e["committed_variable_total"], 2)),
            "fixed_payment_total": float(round(e["fixed_payment_total"], 2)),
            "product_restock_total": float(round(e["product_restock_total"], 2)),
        })
    return sorted(result, key=lambda x: x["actual"], reverse=True)


def _compute_monthly_projection(
    month: int, year: int, total_income: Decimal, today: date | None = None
) -> dict[str, Any]:
    today = today or timezone.localdate()
    is_current_month = today.year == year and today.month == month
    days_total = calendar.monthrange(year, month)[1]
    days_elapsed = today.day if is_current_month else days_total

    var_total = _to_decimal(
        VariableExpense.objects.filter(date__year=year, date__month=month, status=VariableExpense.STATUS_PAID)
        .aggregate(s=Sum("amount"))["s"]
    )
    fixed_total = _to_decimal(
        FixedExpensePayment.objects.filter(
            fixed_expense__is_active=True, date__year=year, date__month=month,
        ).aggregate(s=Sum("amount"))["s"]
    )
    restock_total = Decimal("0")
    for restock in ProductRestock.objects.filter(date__year=year, date__month=month, unit_cost__isnull=False):
        restock_total += _to_decimal(restock.unit_cost) * _to_decimal(restock.quantity)

    actual_spend = var_total + fixed_total + restock_total

    daily_rate = projected_month_end = projected_remaining = projected_expense_pct = None
    if days_elapsed > 0:
        daily_rate = actual_spend / Decimal(days_elapsed)
        projected_month_end = daily_rate * Decimal(days_total)
        projected_remaining = total_income - projected_month_end
        if total_income > 0:
            projected_expense_pct = (projected_month_end / total_income) * 100

    alerts = []
    if is_current_month:
        if total_income <= 0:
            alerts.append({
                "level": "warning",
                "code": "no_income",
                "message": "No hay ingresos registrados este mes.",
            })
        elif projected_month_end is not None:
            if projected_month_end > total_income:
                alerts.append({
                    "level": "danger",
                    "code": "budget_overrun",
                    "message": "Al ritmo actual cerrarás el mes en déficit.",
                })
            elif projected_expense_pct is not None and projected_expense_pct > Decimal("90"):
                alerts.append({
                    "level": "warning",
                    "code": "pace_high",
                    "message": f"Al ritmo actual gastarás el {float(projected_expense_pct):.0f}% de tus ingresos.",
                })

    return {
        "is_current_month": is_current_month,
        "days_elapsed": days_elapsed,
        "days_total": days_total,
        "actual_spend_so_far": float(round(actual_spend, 2)),
        "daily_rate": float(round(daily_rate, 2)) if daily_rate is not None else None,
        "projected_month_end": float(round(projected_month_end, 2)) if projected_month_end is not None else None,
        "projected_remaining": float(round(projected_remaining, 2)) if projected_remaining is not None else None,
        "projected_expense_pct": float(round(projected_expense_pct, 2)) if projected_expense_pct is not None else None,
        "alerts": alerts,
    }


def calculate_monthly_finance_summary(month: int, year: int) -> dict[str, Any]:
    settings_data = InventorySettings.get_solo().get_config()
    frequency_weight = settings_data.get("usage_frequency_weights", {})
    budget_target_ratio = get_budget_bucket_ratio_map(settings_data)

    products = Product.objects.filter(is_active=True)
    home_estimated_expenses = Decimal("0")
    fixed_estimated_expenses = Decimal("0")
    budget_actuals = {
        "needs": Decimal("0"),
        "wants": Decimal("0"),
        "savings": Decimal("0"),
    }

    for product in products:
        budget_bucket = product.budget_bucket or Product.get_budget_bucket_for_category(product.category)

        fallback_cost = _to_decimal(get_category_fallback_unit_cost(settings_data, product.category, 4))
        base_cost = _to_decimal(product.price) if product.price and product.price > 0 else fallback_cost
        frequency = _to_decimal(frequency_weight.get(product.usage_frequency, 1), default="1")
        projected_units = product.stock_min if product.type == "consumable" else Decimal("1")
        estimate = projected_units * base_cost * frequency
        home_estimated_expenses += estimate
        budget_actuals[budget_bucket] += estimate

    fixed_payments = FixedExpensePayment.objects.filter(
        fixed_expense__is_active=True,
        date__year=year,
        date__month=month,
    ).select_related("fixed_expense")

    paid_fixed_ids = set()
    for payment in fixed_payments:
        fixed_amount = _to_decimal(payment.amount)
        expense = payment.fixed_expense
        budget_bucket = expense.budget_bucket or FixedExpense.get_budget_bucket_for_category(expense.category)
        fixed_estimated_expenses += fixed_amount
        budget_actuals[budget_bucket] += fixed_amount
        paid_fixed_ids.add(expense.id)

    committed_fixed_expenses = Decimal("0")
    for fe in FixedExpense.objects.filter(is_active=True).exclude(id__in=paid_fixed_ids):
        amount = _to_decimal(fe.monthly_amount)
        bucket = fe.budget_bucket or FixedExpense.get_budget_bucket_for_category(fe.category)
        committed_fixed_expenses += amount
        budget_actuals[bucket] += amount

    paid_variable_expenses = Decimal("0")
    committed_variable_expenses = Decimal("0")
    variable_expenses = VariableExpense.objects.filter(date__year=year, date__month=month)

    for expense in variable_expenses:
        amount = _to_decimal(expense.amount)
        budget_bucket = expense.budget_bucket or VariableExpense.get_budget_bucket_for_category(expense.category)
        if expense.status == VariableExpense.STATUS_COMMITTED:
            committed_variable_expenses += amount
        else:
            paid_variable_expenses += amount
        budget_actuals[budget_bucket] += amount

    variable_month_expenses = paid_variable_expenses + committed_variable_expenses
    paid_expenses = fixed_estimated_expenses + paid_variable_expenses
    committed_expenses = committed_fixed_expenses + committed_variable_expenses

    estimated_expenses = home_estimated_expenses + fixed_estimated_expenses + variable_month_expenses

    month_income = (
        Income.objects.filter(date__year=year, date__month=month).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    total_income = _to_decimal(month_income)

    expense_percentage = None
    if total_income > 0:
        expense_percentage = (estimated_expenses / total_income) * 100

    budget_targets = {
        bucket: round(total_income * _to_decimal(ratio), 2)
        for bucket, ratio in budget_target_ratio.items()
    }
    budget_actuals["needs"] = round(budget_actuals["needs"], 2)
    budget_actuals["wants"] = round(budget_actuals["wants"], 2)
    budget_actuals["savings"] = round(
        max(total_income - budget_actuals["needs"] - budget_actuals["wants"], 0),
        2,
    )
    budget_variance = {
        bucket: round(budget_actuals[bucket] - budget_targets[bucket], 2)
        for bucket in budget_target_ratio
    }

    monthly_close = MonthlyClose.objects.filter(month=month, year=year).first()
    category_breakdown = _compute_category_breakdown(month, year, settings_data)
    projection = _compute_monthly_projection(month, year, total_income)

    return {
        "month": month,
        "year": year,
        "total_income": float(round(total_income, 2)),
        "home_estimated_expenses": float(round(home_estimated_expenses, 2)),
        "fixed_estimated_expenses": float(round(fixed_estimated_expenses, 2)),
        "variable_expenses": float(round(variable_month_expenses, 2)),
        "paid_expenses": float(round(paid_expenses, 2)),
        "committed_expenses": float(round(committed_expenses, 2)),
        "committed_fixed_expenses": float(round(committed_fixed_expenses, 2)),
        "paid_variable_expenses": float(round(paid_variable_expenses, 2)),
        "committed_variable_expenses": float(round(committed_variable_expenses, 2)),
        "estimated_expenses": float(round(estimated_expenses, 2)),
        "expense_percentage": float(round(expense_percentage, 2)) if expense_percentage is not None else None,
        "remaining_balance": float(round(total_income - estimated_expenses, 2)),
        "rule_50_30_20": {
            "targets": {bucket: float(value) for bucket, value in budget_targets.items()},
            "actuals": {bucket: float(value) for bucket, value in budget_actuals.items()},
            "variance": {bucket: float(value) for bucket, value in budget_variance.items()},
        },
        "category_breakdown": category_breakdown,
        "monthly_close": _snapshot_monthly_close(monthly_close) if monthly_close else None,
        "projection": projection,
    }


def create_monthly_close(
    month: int, year: int, notes: str = "", auto_generated: bool = False
) -> MonthlyClose:
    if month < 1 or month > 12:
        raise ValueError("El mes debe estar entre 1 y 12")

    if MonthlyClose.objects.filter(month=month, year=year).exists():
        raise ValueError("Ese mes ya fue cerrado")

    summary = calculate_monthly_finance_summary(month, year)
    close_date = timezone.datetime(year=year, month=month, day=1).date()
    default_reason = "Cierre automatico de fin de mes" if auto_generated else "Cierre mensual generado"
    reason = _normalize_change_reason(notes, default_reason=default_reason)

    with transaction.atomic():
        monthly_close = MonthlyClose.objects.create(
            month=month,
            year=year,
            notes=notes.strip(),
            summary_snapshot=summary,
        )
        _record_financial_event(
            entity_type="monthly_close",
            action="monthly_closed",
            entity_id=monthly_close.id,
            title=f"Cierre mensual {month:02d}/{year}",
            amount=summary["remaining_balance"],
            effective_date=close_date,
            reason=reason,
            current_data=_snapshot_monthly_close(monthly_close),
            metadata={
                "summary_snapshot": summary,
                "auto_generated": auto_generated,
            },
        )
        return monthly_close


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

def _get_historical_category_averages(
    current_month: int, current_year: int, lookback_months: int = 3
) -> tuple[dict[str, float], int]:
    """
    Returns (averages_dict, actual_lookback_count) where averages_dict maps
    category → average spend computed only over months where the category had
    non-zero spend (requires at least 2 such months to avoid single-sample noise).
    """
    closes = MonthlyClose.objects.order_by("-year", "-month")
    target_closes = []
    for close in closes:
        if (close.year, close.month) < (current_year, current_month):
            target_closes.append(close)
            if len(target_closes) >= lookback_months:
                break

    if not target_closes:
        return {}, 0

    category_totals: dict[str, float] = {}
    category_counts: dict[str, int] = {}

    for close in target_closes:
        for item in close.summary_snapshot.get("category_breakdown", []):
            cat = item.get("category")
            actual = float(item.get("actual", 0))
            if cat and actual > 0:
                category_totals[cat] = category_totals.get(cat, 0) + actual
                category_counts[cat] = category_counts.get(cat, 0) + 1

    averages = {
        cat: total / category_counts[cat]
        for cat, total in category_totals.items()
        if category_counts.get(cat, 0) >= 2
    }
    return averages, len(target_closes)


def _detect_category_spikes(
    current_breakdown: list[dict[str, Any]],
    historical_avgs: dict[str, float],
    settings_data: dict[str, Any],
    lookback_count: int,
    spike_warning_pct: float = 50.0,
    spike_danger_pct: float = 100.0,
    min_historical_amount: float = 500.0,
) -> list[dict[str, Any]]:
    category_labels = {
        item["value"]: item.get("label", item["value"])
        for item in settings_data.get("categories", [])
    }
    anomalies = []
    for item in current_breakdown:
        cat = item["category"]
        current_amount = float(item["actual"])
        historical_avg = historical_avgs.get(cat)

        if historical_avg is None or historical_avg < min_historical_amount:
            continue
        if current_amount <= 0:
            continue

        deviation_pct = ((current_amount - historical_avg) / historical_avg) * 100

        if deviation_pct >= spike_danger_pct:
            level = "danger"
        elif deviation_pct >= spike_warning_pct:
            level = "warning"
        else:
            continue

        cat_label = category_labels.get(cat, cat)
        anomalies.append({
            "type": "category_spike",
            "level": level,
            "title": f"{cat_label}: gasto un {deviation_pct:.0f}% por encima del promedio",
            "description": f"Este mes: {current_amount:,.0f} | Promedio ({lookback_count} mes{'es' if lookback_count != 1 else ''}): {historical_avg:,.0f}",
            "category": cat,
            "category_label": cat_label,
            "current_amount": round(current_amount, 2),
            "reference_amount": round(historical_avg, 2),
            "deviation_pct": round(deviation_pct, 1),
            "product_id": None,
            "product_name": None,
            "days_since_last_restock": None,
            "avg_restock_interval_days": None,
        })
    return anomalies


def _detect_restock_anomalies(
    today: date | None = None,
    fast_threshold: float = 0.5,
    slow_threshold: float = 2.0,
    min_restocks: int = 3,
    min_avg_interval_days: float = 5.0,
) -> list[dict[str, Any]]:
    today = today or timezone.localdate()
    anomalies = []

    products = Product.objects.filter(is_active=True, type="consumable").prefetch_related(
        Prefetch(
            "restocks",
            queryset=ProductRestock.objects.order_by("date"),
            to_attr="restocks_prefetched",
        )
    )
    for product in products:
        restock_dates = [r.date for r in product.restocks_prefetched]
        if len(restock_dates) < min_restocks:
            continue

        intervals = [
            (restock_dates[i + 1] - restock_dates[i]).days
            for i in range(len(restock_dates) - 1)
        ]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval < min_avg_interval_days:
            continue

        days_since_last = (today - restock_dates[-1]).days

        if days_since_last < avg_interval * fast_threshold:
            deviation_pct = round(((days_since_last / avg_interval) - 1) * 100, 1)
            anomalies.append({
                "type": "fast_restock",
                "level": "info",
                "title": f"{product.name}: reposicion mas frecuente que lo habitual",
                "description": f"Repuesto hace {days_since_last} días (promedio: {round(avg_interval)} días)",
                "category": None,
                "category_label": None,
                "current_amount": None,
                "reference_amount": None,
                "deviation_pct": deviation_pct,
                "product_id": product.id,
                "product_name": product.name,
                "days_since_last_restock": days_since_last,
                "avg_restock_interval_days": round(avg_interval, 1),
            })
        elif days_since_last > avg_interval * slow_threshold:
            deviation_pct = round(((days_since_last / avg_interval) - 1) * 100, 1)
            anomalies.append({
                "type": "slow_restock",
                "level": "warning",
                "title": f"{product.name}: sin reposición por más tiempo que lo habitual",
                "description": f"Sin reponer hace {days_since_last} días (promedio: {round(avg_interval)} días)",
                "category": None,
                "category_label": None,
                "current_amount": None,
                "reference_amount": None,
                "deviation_pct": deviation_pct,
                "product_id": product.id,
                "product_name": product.name,
                "days_since_last_restock": days_since_last,
                "avg_restock_interval_days": round(avg_interval, 1),
            })
    return anomalies


def detect_financial_anomalies(month: int, year: int, today: date | None = None) -> dict[str, Any]:
    settings_data = InventorySettings.get_solo().get_config()
    current_breakdown = _compute_category_breakdown(month, year, settings_data)
    historical_avgs, lookback_count = _get_historical_category_averages(month, year)

    anomalies = []

    if lookback_count >= 1:
        anomalies += _detect_category_spikes(
            current_breakdown, historical_avgs, settings_data, lookback_count,
        )

    anomalies += _detect_restock_anomalies(today=today or timezone.localdate())

    level_order = {"danger": 0, "warning": 1, "info": 2}
    anomalies.sort(key=lambda a: level_order.get(a["level"], 9))

    return {
        "month": month,
        "year": year,
        "lookback_months": lookback_count,
        "anomalies": anomalies,
    }


def get_dashboard_summary(today: date | None = None) -> dict[str, Any]:
    from datetime import timedelta

    from apps.goals.models import SavingsGoal
    from apps.goals.services import get_goal_progress
    from apps.household.models import TaskOccurrence

    today = today or timezone.localdate()
    month, year = get_active_financial_period()
    settings_data = InventorySettings.get_solo().get_config()

    finance_summary = calculate_monthly_finance_summary(month, year)

    critical_ratio = float(settings_data.get("thresholds", {}).get("critical_stock_ratio", 1))
    critical_frequencies = settings_data.get("alerts", {}).get("critical_frequencies", ["high"])

    critical_products = []
    for p in Product.objects.filter(is_active=True).order_by("name"):
        if (
            p.stock <= float(p.stock_min or 0) * critical_ratio
            and p.usage_frequency in critical_frequencies
        ):
            critical_products.append({
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "stock": float(p.stock),
                "stock_min": float(p.stock_min or 0),
                "unit": p.unit or "",
            })
            if len(critical_products) >= 5:
                break

    overdue_qs = (
        TaskOccurrence.objects
        .filter(status="pending", due_date__lt=today)
        .select_related("recurring_task")
        .order_by("due_date")
    )
    overdue_tasks = [
        {
            "id": o.id,
            "title": o.recurring_task.title,
            "due_date": o.due_date.isoformat(),
            "priority": o.recurring_task.priority,
            "category": o.recurring_task.category,
        }
        for o in overdue_qs
    ]

    upcoming_qs = (
        TaskOccurrence.objects
        .filter(status="pending", due_date__gte=today, due_date__lte=today + timedelta(days=7))
        .select_related("recurring_task")
        .order_by("due_date")
    )
    upcoming_tasks = [
        {
            "id": o.id,
            "title": o.recurring_task.title,
            "due_date": o.due_date.isoformat(),
            "priority": o.recurring_task.priority,
            "category": o.recurring_task.category,
        }
        for o in upcoming_qs
    ]

    lagging_goals = []
    for goal in SavingsGoal.objects.filter(is_active=True):
        progress = get_goal_progress(goal)
        if progress["progress_pct"] < 20:
            lagging_goals.append({
                "id": goal.id,
                "name": goal.name,
                "goal_type": goal.goal_type,
                "target_amount": float(goal.target_amount),
                "current_amount": float(goal.current_amount),
                "progress_pct": progress["progress_pct"],
                "days_left": progress["days_left"],
            })

    anomalies_data = detect_financial_anomalies(month, year, today=today)

    return {
        "month": month,
        "year": year,
        "finance_summary": finance_summary,
        "critical_products": critical_products,
        "overdue_tasks": overdue_tasks,
        "upcoming_tasks": upcoming_tasks,
        "lagging_goals": lagging_goals,
        "anomalies": anomalies_data["anomalies"],
        "anomalies_lookback_months": anomalies_data["lookback_months"],
    }
