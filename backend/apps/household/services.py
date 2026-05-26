import calendar
from collections import defaultdict
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.configuration.models import InventorySettings

from .models import RecurringTask, TaskOccurrence


DEFAULT_SYNC_WINDOW_DAYS = 120


def _days_until(target_date: date | None, today: date) -> int | None:
    if not target_date:
        return None
    return (target_date - today).days


def build_task_linked_context(
    task: RecurringTask, settings_data: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    integration_kind = task.integration_kind or RecurringTask.INTEGRATION_NONE
    if integration_kind == RecurringTask.INTEGRATION_NONE:
        return None

    today = timezone.localdate()

    if integration_kind == RecurringTask.INTEGRATION_FIXED_EXPENSE:
        expense = task.linked_fixed_expense
        if expense is None:
            return {
                "kind": integration_kind,
                "kind_label": "Gasto fijo",
                "status": "missing",
                "tone": "warning",
                "entity_name": "Gasto no disponible",
                "summary": "La referencia al gasto fijo ya no existe.",
                "detail": "Revisa la integracion de esta tarea para recuperar el contexto financiero.",
            }

        prefetched = getattr(expense, "_current_month_payments", None)
        if prefetched is not None:
            is_paid_this_month = bool(prefetched)
        else:
            is_paid_this_month = expense.payments.filter(date__year=today.year, date__month=today.month).exists()
        due_delta = _days_until(expense.next_due_date, today)

        if is_paid_this_month:
            status = "paid"
            tone = "success"
            summary = "El gasto ya fue pagado este mes."
        elif due_delta is not None and due_delta < 0:
            status = "overdue"
            tone = "danger"
            summary = "El gasto sigue pendiente y ya esta vencido."
        elif due_delta is not None and due_delta <= 7:
            status = "due_soon"
            tone = "warning"
            summary = "El gasto vence pronto y conviene anticiparlo."
        else:
            status = "planned"
            tone = "info"
            summary = "El gasto esta vinculado para seguimiento operativo."

        detail = f"{expense.category} | {expense.monthly_amount} por mes"
        if expense.next_due_date:
            detail = f"{detail} | Proximo vencimiento: {expense.next_due_date}"

        return {
            "kind": integration_kind,
            "kind_label": "Gasto fijo",
            "status": status,
            "tone": tone,
            "entity_id": expense.id,
            "entity_name": expense.name,
            "summary": summary,
            "detail": detail,
            "reference_date": expense.next_due_date,
            "days_delta": due_delta,
            "payment_status": "paid" if is_paid_this_month else "pending",
        }

    product = task.linked_product
    kind_label = "Reposicion de producto" if integration_kind == RecurringTask.INTEGRATION_PRODUCT_RESTOCK else "Revision de vencimiento"
    if product is None:
        return {
            "kind": integration_kind,
            "kind_label": kind_label,
            "status": "missing",
            "tone": "warning",
            "entity_name": "Producto no disponible",
            "summary": "La referencia al producto ya no existe.",
            "detail": "Revisa la integracion de esta tarea para recuperar el contexto de inventario.",
        }

    if integration_kind == RecurringTask.INTEGRATION_PRODUCT_RESTOCK:
        low_stock = product.stock <= product.stock_min
        if product.stock <= 0:
            status = "out_of_stock"
            tone = "danger"
            summary = "El producto esta agotado."
        elif low_stock:
            status = "low_stock"
            tone = "warning"
            summary = "El producto ya esta por debajo del minimo."
        else:
            status = "ok"
            tone = "success"
            summary = "El stock esta controlado por ahora."

        return {
            "kind": integration_kind,
            "kind_label": kind_label,
            "status": status,
            "tone": tone,
            "entity_id": product.id,
            "entity_name": product.name,
            "summary": summary,
            "detail": f"Stock actual: {product.stock} {product.unit} | Minimo: {product.stock_min} {product.unit}",
            "reference_date": product.last_purchase,
            "days_delta": None,
            "low_stock": low_stock,
        }

    if settings_data is None:
        settings_data = InventorySettings.get_solo().get_config()
    expiring_soon_days = int(settings_data.get("alerts", {}).get("expiring_soon_days", 14) or 14)
    due_delta = _days_until(product.next_due_date, today)

    if product.next_due_date is None:
        status = "missing_date"
        tone = "warning"
        summary = "El producto no tiene fecha objetivo para revisar vencimiento."
    elif due_delta < 0:
        status = "expired"
        tone = "danger"
        summary = "El producto ya esta vencido o supero la fecha objetivo."
    elif due_delta <= expiring_soon_days:
        status = "expiring_soon"
        tone = "warning"
        summary = "El producto entra en la ventana de vencimiento proximo."
    else:
        status = "ok"
        tone = "success"
        summary = "Todavia no entra en la ventana de atencion por vencimiento."

    return {
        "kind": integration_kind,
        "kind_label": kind_label,
        "status": status,
        "tone": tone,
        "entity_id": product.id,
        "entity_name": product.name,
        "summary": summary,
        "detail": (
            f"Categoria: {product.category} | Fecha objetivo: {product.next_due_date or 'sin fecha'} | "
            f"Ventana: {expiring_soon_days} dias"
        ),
        "reference_date": product.next_due_date,
        "days_delta": due_delta,
        "expiring_soon_days": expiring_soon_days,
    }


def _month_date(year: int, month: int, day_of_month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return RecurringTask._meta.get_field("start_date").to_python(f"{year:04d}-{month:02d}-{min(day_of_month, last_day):02d}")


def _add_months(base_date: date, months: int, day_of_month: int) -> date:
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    return _month_date(year, month, day_of_month)


def _normalize_task_payload(validated_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": validated_data["title"].strip(),
        "category": validated_data.get("category", "general").strip() or "general",
        "area": validated_data.get("area", "home_admin").strip() or "home_admin",
        "priority": validated_data.get("priority", "medium"),
        "estimated_minutes": validated_data.get("estimated_minutes", 15),
        "frequency_type": validated_data["frequency_type"],
        "interval": validated_data.get("interval", 1),
        "weekday": validated_data.get("weekday"),
        "day_of_month": validated_data.get("day_of_month"),
        "start_date": validated_data.get("start_date", timezone.localdate()),
        "notes": validated_data.get("notes", "").strip(),
        "is_active": validated_data.get("is_active", True),
    }


def _get_sync_window_bounds(
    start_date: date | None = None, horizon_days: int = DEFAULT_SYNC_WINDOW_DAYS
) -> tuple[date, date]:
    today = timezone.localdate()
    date_from = min(start_date or today, today)
    date_to = today + timedelta(days=horizon_days)
    return date_from, date_to


def _iter_due_dates(task: RecurringTask, date_from: date, date_to: date) -> Iterator[date]:
    if not task.is_active or date_to < date_from:
        return

    current_due_date = calculate_first_due_date(
        task.start_date,
        task.frequency_type,
        weekday=task.weekday,
        day_of_month=task.day_of_month,
        interval=task.interval,
    )

    while current_due_date < date_from:
        current_due_date = calculate_next_due_date(task, current_due_date)

    while current_due_date <= date_to:
        yield current_due_date
        current_due_date = calculate_next_due_date(task, current_due_date)


def calculate_first_due_date(
    start_date: date,
    frequency_type: str,
    weekday: int | None = None,
    day_of_month: int | None = None,
    interval: int = 1,
) -> date:
    if frequency_type == RecurringTask.FREQUENCY_DAILY:
        return start_date

    if frequency_type == RecurringTask.FREQUENCY_WEEKLY:
        effective_weekday = weekday if weekday is not None else start_date.weekday()
        delta = (int(effective_weekday) - start_date.weekday()) % 7
        return start_date + timedelta(days=delta)

    effective_day = day_of_month if day_of_month is not None else start_date.day
    candidate = _month_date(start_date.year, start_date.month, int(effective_day))
    if candidate < start_date:
        candidate = _add_months(candidate, 1, int(effective_day))
    return candidate


def calculate_next_due_date(task: RecurringTask, current_due_date: date) -> date:
    if task.frequency_type == RecurringTask.FREQUENCY_DAILY:
        return current_due_date + timedelta(days=int(task.interval))

    if task.frequency_type == RecurringTask.FREQUENCY_WEEKLY:
        return current_due_date + timedelta(days=7 * int(task.interval))

    effective_day = task.day_of_month if task.day_of_month is not None else current_due_date.day
    return _add_months(current_due_date, int(task.interval), int(effective_day))


def sync_task_occurrences(
    task: RecurringTask, date_from: date | None = None, date_to: date | None = None
) -> None:
    if date_from is None or date_to is None:
        date_from, date_to = _get_sync_window_bounds(task.start_date)

    if date_to < date_from:
        raise ValueError("La fecha final no puede ser menor que la inicial.")

    desired_due_dates = set(_iter_due_dates(task, date_from, date_to)) if task.is_active else set()
    existing_occurrences = task.occurrences.filter(due_date__gte=date_from, due_date__lte=date_to)
    existing_by_due_date = {occurrence.due_date: occurrence for occurrence in existing_occurrences}

    for due_date in desired_due_dates:
        if due_date not in existing_by_due_date:
            TaskOccurrence.objects.create(
                recurring_task=task,
                due_date=due_date,
                status=TaskOccurrence.STATUS_PENDING,
            )

    for due_date, occurrence in existing_by_due_date.items():
        if due_date in desired_due_dates:
            continue
        if occurrence.status == TaskOccurrence.STATUS_PENDING:
            occurrence.delete()

    refresh_next_due_date(task)


def refresh_next_due_date(task: RecurringTask) -> None:
    next_pending = task.occurrences.filter(status=TaskOccurrence.STATUS_PENDING).order_by("due_date").first()
    next_due_date = next_pending.due_date if next_pending else None

    if task.next_due_date != next_due_date:
        task.next_due_date = next_due_date
        task.save(update_fields=["next_due_date", "updated_at"])


def create_recurring_task_record(validated_data: dict[str, Any]) -> RecurringTask:
    payload = _normalize_task_payload(validated_data)

    with transaction.atomic():
        task = RecurringTask.objects.create(**payload, next_due_date=None)
        sync_task_occurrences(task)

        return task


def update_recurring_task_record(task: RecurringTask, validated_data: dict[str, Any]) -> RecurringTask:
    original_start_date = task.start_date

    for field, value in validated_data.items():
        if field in {"title", "category", "area", "notes"} and isinstance(value, str):
            value = value.strip()
        setattr(task, field, value)

    if not task.category:
        task.category = "general"
    if not task.area:
        task.area = "home_admin"

    if task.estimated_minutes is None:
        task.estimated_minutes = 15

    with transaction.atomic():
        task.next_due_date = None
        task.save()
        sync_window_start = min(original_start_date, task.start_date, timezone.localdate())
        sync_window_end = timezone.localdate() + timedelta(days=DEFAULT_SYNC_WINDOW_DAYS)
        sync_task_occurrences(task, sync_window_start, sync_window_end)

        return task


def ensure_occurrences_for_range(date_from: date, date_to: date) -> None:
    if date_to < date_from:
        raise ValueError("La fecha final no puede ser menor que la inicial.")

    active_tasks = RecurringTask.objects.filter(is_active=True)

    for task in active_tasks:
        sync_task_occurrences(task, date_from, date_to)


def _ensure_follow_up_occurrence(task: RecurringTask, occurrence: TaskOccurrence) -> None:
    sync_task_occurrences(task)


def _completed_late(occurrence: TaskOccurrence) -> bool:
    if not occurrence.completed_at:
        return False
    return occurrence.completed_at.date() > occurrence.due_date


def _serialize_task_compliance_item(
    task: RecurringTask, stats: dict[str, Any], settings_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    overdue_count = stats["overdue_count"]
    skipped_count = stats["skipped_count"]
    late_completion_count = stats["late_completion_count"]
    postponement_score = overdue_count + skipped_count + late_completion_count

    return {
        "recurring_task_id": task.id,
        "title": task.title,
        "category": task.category,
        "area": task.area,
        "priority": task.priority,
        "estimated_minutes": int(task.estimated_minutes or 0),
        "integration_kind": task.integration_kind,
        "linked_context": build_task_linked_context(task, settings_data),
        "overdue_count": overdue_count,
        "skipped_count": skipped_count,
        "late_completion_count": late_completion_count,
        "postponement_score": postponement_score,
    }


def build_household_insights(
    date_from: date, date_to: date, filters: dict[str, Any] | None = None
) -> dict[str, Any]:
    if date_to < date_from:
        raise ValueError("La fecha final no puede ser menor que la inicial.")

    filters = filters or {}
    ensure_occurrences_for_range(date_from, date_to)

    from apps.expenses.models import FixedExpensePayment
    _today = timezone.localdate()
    _month_payments_qs = FixedExpensePayment.objects.filter(
        date__year=_today.year, date__month=_today.month
    )

    occurrences = TaskOccurrence.objects.select_related(
        "recurring_task",
        "recurring_task__linked_fixed_expense",
        "recurring_task__linked_product",
    ).prefetch_related(
        Prefetch(
            "recurring_task__linked_fixed_expense__payments",
            queryset=_month_payments_qs,
            to_attr="_current_month_payments",
        )
    ).filter(
        recurring_task__is_active=True,
        due_date__gte=date_from,
        due_date__lte=date_to,
    )

    if filters.get("category"):
        occurrences = occurrences.filter(recurring_task__category=filters["category"])
    if filters.get("area"):
        occurrences = occurrences.filter(recurring_task__area=filters["area"])
    if filters.get("priority"):
        occurrences = occurrences.filter(recurring_task__priority=filters["priority"])

    occurrences = list(occurrences.order_by("due_date", "id"))
    today = timezone.localdate()
    settings_data = InventorySettings.get_solo().get_config()

    task_stats = defaultdict(lambda: {"task": None, "overdue_count": 0, "skipped_count": 0, "late_completion_count": 0})
    week_stats = defaultdict(lambda: {"total_due": 0, "completed": 0, "skipped": 0, "overdue_open": 0, "estimated_minutes": 0})

    for occurrence in occurrences:
        task = occurrence.recurring_task
        week_start = occurrence.due_date - timedelta(days=occurrence.due_date.weekday())
        current_week = week_stats[week_start]
        current_week["total_due"] += 1
        current_week["estimated_minutes"] += int(task.estimated_minutes or 0)

        task_entry = task_stats[task.id]
        task_entry["task"] = task

        if occurrence.status == TaskOccurrence.STATUS_DONE:
            current_week["completed"] += 1
            if _completed_late(occurrence):
                task_entry["late_completion_count"] += 1
        elif occurrence.status == TaskOccurrence.STATUS_SKIPPED:
            current_week["skipped"] += 1
            task_entry["skipped_count"] += 1

        if occurrence.status == TaskOccurrence.STATUS_PENDING and occurrence.due_date < today:
            current_week["overdue_open"] += 1
            task_entry["overdue_count"] += 1

    weekly_completion = []
    total_weekly_minutes = 0

    current_week_start = date_from - timedelta(days=date_from.weekday())
    last_week_start = date_to - timedelta(days=date_to.weekday())
    while current_week_start <= last_week_start:
        stats = week_stats[current_week_start]
        total_due = stats["total_due"]
        completion_rate = round((stats["completed"] / total_due) * 100, 2) if total_due else 0
        weekly_completion.append({
            "week_start": current_week_start,
            "week_end": current_week_start + timedelta(days=6),
            "total_due": total_due,
            "completed": stats["completed"],
            "skipped": stats["skipped"],
            "overdue_open": stats["overdue_open"],
            "completion_rate": completion_rate,
            "estimated_minutes": stats["estimated_minutes"],
        })
        total_weekly_minutes += stats["estimated_minutes"]
        current_week_start += timedelta(days=7)

    task_items = [
        _serialize_task_compliance_item(entry["task"], entry, settings_data)
        for entry in task_stats.values()
        if entry["task"] is not None
    ]
    task_items.sort(key=lambda item: (-item["postponement_score"], -item["overdue_count"], item["title"]))

    recurring_overdue_tasks = [
        item for item in task_items
        if item["overdue_count"] >= 2 or (item["overdue_count"] >= 1 and item["priority"] in {"high", "critical"})
    ]

    return {
        "window_start": date_from,
        "window_end": date_to,
        "weekly_completion": weekly_completion,
        "most_postponed_tasks": task_items[:5],
        "recurring_overdue_tasks": recurring_overdue_tasks[:5],
        "weekly_estimated_minutes": round(total_weekly_minutes / max(len(weekly_completion), 1)),
        "overdue_tasks_count": sum(1 for item in task_items if item["overdue_count"] > 0),
    }


def complete_task_occurrence(occurrence: TaskOccurrence, completion_notes: str = "") -> TaskOccurrence:
    with transaction.atomic():
        locked_occurrence = TaskOccurrence.objects.select_for_update().select_related("recurring_task").get(id=occurrence.id)

        if locked_occurrence.status == TaskOccurrence.STATUS_DONE:
            raise ValueError("La tarea ya fue marcada como hecha.")

        locked_occurrence.status = TaskOccurrence.STATUS_DONE
        locked_occurrence.completed_at = timezone.now()
        locked_occurrence.completion_notes = str(completion_notes or "").strip()
        locked_occurrence.save(update_fields=["status", "completed_at", "completion_notes"])

        if locked_occurrence.recurring_task.is_active:
            _ensure_follow_up_occurrence(locked_occurrence.recurring_task, locked_occurrence)

        refresh_next_due_date(locked_occurrence.recurring_task)
        return locked_occurrence


def skip_task_occurrence(occurrence: TaskOccurrence, completion_notes: str = "") -> TaskOccurrence:
    with transaction.atomic():
        locked_occurrence = TaskOccurrence.objects.select_for_update().select_related("recurring_task").get(id=occurrence.id)

        if locked_occurrence.status == TaskOccurrence.STATUS_SKIPPED:
            raise ValueError("La tarea ya fue omitida.")

        locked_occurrence.status = TaskOccurrence.STATUS_SKIPPED
        locked_occurrence.completed_at = timezone.now()
        locked_occurrence.completion_notes = str(completion_notes or "").strip()
        locked_occurrence.save(update_fields=["status", "completed_at", "completion_notes"])

        if locked_occurrence.recurring_task.is_active:
            _ensure_follow_up_occurrence(locked_occurrence.recurring_task, locked_occurrence)

        refresh_next_due_date(locked_occurrence.recurring_task)
        return locked_occurrence


def reopen_task_occurrence(occurrence: TaskOccurrence) -> TaskOccurrence:
    with transaction.atomic():
        locked_occurrence = TaskOccurrence.objects.select_for_update().select_related("recurring_task").get(id=occurrence.id)

        if locked_occurrence.status == TaskOccurrence.STATUS_PENDING:
            raise ValueError("La tarea ya esta pendiente.")

        locked_occurrence.status = TaskOccurrence.STATUS_PENDING
        locked_occurrence.completed_at = None
        locked_occurrence.completion_notes = ""
        locked_occurrence.save(update_fields=["status", "completed_at", "completion_notes"])

        refresh_next_due_date(locked_occurrence.recurring_task)
        return locked_occurrence
