from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.reports.services import (
    _add_one_month,
    _normalize_change_reason,
    _record_financial_event,
    _snapshot_fixed_expense,
    _snapshot_fixed_payment,
    _snapshot_income,
    _snapshot_variable_expense,
)

from .models import FixedExpense, FixedExpensePayment, Income, VariableExpense


def create_income_record(validated_data: dict[str, Any], change_reason: str = "") -> Income:
    payload = {
        "amount": validated_data["amount"],
        "source": validated_data.get("source", "").strip(),
        "notes": validated_data.get("notes", "").strip(),
        "date": validated_data.get("date") or timezone.localdate(),
    }
    reason = _normalize_change_reason(change_reason, default_reason="Alta manual de ingreso")

    with transaction.atomic():
        income = Income.objects.create(**payload)
        _record_financial_event(
            entity_type="income",
            action="created",
            entity_id=income.id,
            title=income.source or "Ingreso sin fuente",
            amount=income.amount,
            effective_date=income.date,
            reason=reason,
            current_data=_snapshot_income(income),
        )
        return income


def update_income_record(income: Income, validated_data: dict[str, Any], change_reason: str = "") -> Income:
    reason = _normalize_change_reason(change_reason, required=True)
    before = _snapshot_income(income)

    for field, value in validated_data.items():
        if field == "source":
            value = value.strip()
        if field == "notes":
            value = value.strip()
        setattr(income, field, value)

    with transaction.atomic():
        income.save()
        after = _snapshot_income(income)
        _record_financial_event(
            entity_type="income",
            action="updated",
            entity_id=income.id,
            title=income.source or "Ingreso sin fuente",
            amount=income.amount,
            effective_date=income.date,
            reason=reason,
            previous_data=before,
            current_data=after,
            metadata={"changed_fields": sorted(validated_data.keys())},
        )
        return income


def delete_income_record(income: Income, change_reason: str = "") -> None:
    reason = _normalize_change_reason(change_reason, required=True)
    before = _snapshot_income(income)
    entity_id = income.id

    with transaction.atomic():
        _record_financial_event(
            entity_type="income",
            action="deleted",
            entity_id=entity_id,
            title=income.source or "Ingreso sin fuente",
            amount=income.amount,
            effective_date=income.date,
            reason=reason,
            previous_data=before,
        )
        income.delete()


def create_variable_expense_record(validated_data: dict[str, Any], change_reason: str = "") -> VariableExpense:
    payload = {
        "amount": validated_data["amount"],
        "category": validated_data["category"],
        "budget_bucket": validated_data["budget_bucket"],
        "description": validated_data.get("description", "").strip(),
        "notes": validated_data.get("notes", "").strip(),
        "status": validated_data.get("status", VariableExpense.STATUS_PAID),
        "date": validated_data.get("date") or timezone.localdate(),
    }
    reason = _normalize_change_reason(change_reason, default_reason="Alta manual de gasto variable")

    with transaction.atomic():
        expense = VariableExpense.objects.create(**payload)
        _record_financial_event(
            entity_type="variable_expense",
            action="created",
            entity_id=expense.id,
            title=expense.description or expense.category,
            amount=expense.amount,
            effective_date=expense.date,
            reason=reason,
            current_data=_snapshot_variable_expense(expense),
        )
        return expense


def update_variable_expense_record(expense: VariableExpense, validated_data: dict[str, Any], change_reason: str = "") -> VariableExpense:
    reason = _normalize_change_reason(change_reason, required=True)
    before = _snapshot_variable_expense(expense)

    for field, value in validated_data.items():
        if field in {"description", "notes"}:
            value = value.strip()
        setattr(expense, field, value)

    with transaction.atomic():
        expense.save()
        after = _snapshot_variable_expense(expense)
        _record_financial_event(
            entity_type="variable_expense",
            action="updated",
            entity_id=expense.id,
            title=expense.description or expense.category,
            amount=expense.amount,
            effective_date=expense.date,
            reason=reason,
            previous_data=before,
            current_data=after,
            metadata={"changed_fields": sorted(validated_data.keys())},
        )
        return expense


def delete_variable_expense_record(expense: VariableExpense, change_reason: str = "") -> None:
    reason = _normalize_change_reason(change_reason, required=True)
    before = _snapshot_variable_expense(expense)
    entity_id = expense.id

    with transaction.atomic():
        _record_financial_event(
            entity_type="variable_expense",
            action="deleted",
            entity_id=entity_id,
            title=expense.description or expense.category,
            amount=expense.amount,
            effective_date=expense.date,
            reason=reason,
            previous_data=before,
        )
        expense.delete()


def create_fixed_expense_record(validated_data: dict[str, Any], change_reason: str = "") -> FixedExpense:
    payload = {
        "name": validated_data["name"].strip(),
        "category": validated_data["category"],
        "budget_bucket": validated_data["budget_bucket"],
        "monthly_amount": validated_data["monthly_amount"],
        "next_due_date": validated_data.get("next_due_date"),
        "is_active": validated_data.get("is_active", True),
    }
    reason = _normalize_change_reason(change_reason, default_reason="Alta manual de gasto fijo")

    with transaction.atomic():
        expense = FixedExpense.objects.create(**payload)
        event_date = expense.next_due_date or timezone.localdate()
        _record_financial_event(
            entity_type="fixed_expense",
            action="created",
            entity_id=expense.id,
            title=expense.name,
            amount=expense.monthly_amount,
            effective_date=event_date,
            reason=reason,
            current_data=_snapshot_fixed_expense(expense),
        )
        return expense


def update_fixed_expense_record(expense: FixedExpense, validated_data: dict[str, Any], change_reason: str = "") -> FixedExpense:
    reason = _normalize_change_reason(change_reason, required=True)
    before = _snapshot_fixed_expense(expense)

    for field, value in validated_data.items():
        if field == "name":
            value = value.strip()
        setattr(expense, field, value)

    with transaction.atomic():
        expense.save()
        event_date = expense.next_due_date or timezone.localdate()
        after = _snapshot_fixed_expense(expense)
        _record_financial_event(
            entity_type="fixed_expense",
            action="updated",
            entity_id=expense.id,
            title=expense.name,
            amount=expense.monthly_amount,
            effective_date=event_date,
            reason=reason,
            previous_data=before,
            current_data=after,
            metadata={"changed_fields": sorted(validated_data.keys())},
        )
        return expense


def delete_fixed_expense_record(expense: FixedExpense, change_reason: str = "") -> None:
    reason = _normalize_change_reason(change_reason, required=True)
    before = _snapshot_fixed_expense(expense)
    entity_id = expense.id
    event_date = expense.next_due_date or timezone.localdate()

    with transaction.atomic():
        _record_financial_event(
            entity_type="fixed_expense",
            action="deleted",
            entity_id=entity_id,
            title=expense.name,
            amount=expense.monthly_amount,
            effective_date=event_date,
            reason=reason,
            previous_data=before,
        )
        expense.delete()


def register_payment(fixed_expense_id: int, change_reason: str = "") -> dict[str, Any]:
    with transaction.atomic():
        fixed_expense = FixedExpense.objects.select_for_update().get(id=fixed_expense_id)

        today = timezone.localdate()
        payment_period = today.replace(day=1)
        payment_amount = fixed_expense.monthly_amount or 0
        reason = _normalize_change_reason(change_reason, default_reason="Pago mensual registrado")

        if FixedExpensePayment.objects.filter(fixed_expense=fixed_expense, date=payment_period).exists():
            raise ValueError("El pago de este mes ya fue registrado. Editalo explicitamente si necesitas corregirlo")

        payment = FixedExpensePayment.objects.create(
            fixed_expense=fixed_expense,
            date=payment_period,
            amount=payment_amount,
        )

        if fixed_expense.next_due_date:
            fixed_expense.next_due_date = _add_one_month(fixed_expense.next_due_date)
            fixed_expense.save(update_fields=["next_due_date", "updated_at"])

        _record_financial_event(
            entity_type="fixed_expense_payment",
            action="payment_recorded",
            entity_id=payment.id,
            title=fixed_expense.name,
            amount=payment.amount,
            effective_date=payment.date,
            reason=reason,
            current_data=_snapshot_fixed_payment(payment),
            metadata={
                "fixed_expense_id": fixed_expense.id,
                "next_due_date": fixed_expense.next_due_date,
            },
        )

        return {
            "fixed_expense": fixed_expense,
            "payment": payment,
        }