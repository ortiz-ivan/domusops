from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Product, ProductConsumption, ProductRestock


def _validate_consumable(product: Product) -> None:
    if product.type != "consumable":
        raise ValueError("Esta acción solo aplica a productos consumibles")


def consume_product(product_id: int, quantity: Decimal = Decimal("1")) -> dict[str, Any]:
    with transaction.atomic():
        product = Product.objects.select_for_update().get(id=product_id)

        _validate_consumable(product)

        if quantity <= Decimal("0"):
            raise ValueError("La cantidad debe ser mayor a 0")

        if product.stock < quantity:
            raise ValueError("Stock insuficiente")

        product.stock -= quantity
        product.save()

        ProductConsumption.objects.create(
            product=product,
            quantity=quantity,
            date=timezone.localdate(),
        )

        return {
            "product": product,
            "low_stock": product.stock <= product.stock_min,
        }


def restock_product(product_id: int, quantity: Decimal = Decimal("1")) -> dict[str, Any]:
    with transaction.atomic():
        product = Product.objects.select_for_update().get(id=product_id)

        _validate_consumable(product)

        if quantity <= Decimal("0"):
            raise ValueError("La cantidad debe ser mayor a 0")

        product.stock += quantity
        product.last_purchase = timezone.localdate()
        product.save()

        unit_cost = Decimal(str(product.price)) if product.price and product.price > 0 else None
        ProductRestock.objects.create(
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
            date=timezone.localdate(),
        )

        return {
            "product": product,
        }


def mark_product_out_of_stock(product_id: int) -> dict[str, Any]:
    with transaction.atomic():
        product = Product.objects.select_for_update().get(id=product_id)

        _validate_consumable(product)

        previous_stock = product.stock
        product.stock = Decimal("0")
        product.save()

        if previous_stock > 0:
            ProductConsumption.objects.create(
                product=product,
                quantity=previous_stock,
                date=timezone.localdate(),
            )

        return {
            "product": product,
            "low_stock": True,
        }


def get_product_stats(product_id: int, days: int = 90) -> dict[str, Any]:
    product = Product.objects.get(id=product_id)
    today = timezone.localdate()
    date_from = today - timedelta(days=days - 1)

    consumption_qs = ProductConsumption.objects.filter(product=product, date__gte=date_from)
    restock_qs = ProductRestock.objects.filter(product=product, date__gte=date_from)

    total_consumed = consumption_qs.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    total_restocked = restock_qs.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    consumption_count = consumption_qs.count()
    restock_count = restock_qs.count()

    avg_daily_consumption = total_consumed / days if total_consumed > 0 else Decimal("0")
    avg_monthly_consumption = avg_daily_consumption * 30

    estimated_days_remaining = None
    if avg_daily_consumption > 0:
        estimated_days_remaining = int(product.stock / avg_daily_consumption)

    estimated_monthly_cost = None
    if avg_monthly_consumption > 0 and product.price and product.price > 0:
        estimated_monthly_cost = float(round(avg_monthly_consumption * Decimal(str(product.price)), 2))

    avg_restock_interval_days = None
    if restock_count >= 2:
        restock_dates = list(
            ProductRestock.objects.filter(product=product)
            .order_by("date")
            .values_list("date", flat=True)
        )
        intervals = [(restock_dates[i + 1] - restock_dates[i]).days for i in range(len(restock_dates) - 1)]
        avg_restock_interval_days = round(sum(intervals) / len(intervals), 1)

    return {
        "product_id": product_id,
        "period_days": days,
        "date_from": date_from,
        "date_to": today,
        "total_consumed": float(round(total_consumed, 3)),
        "total_restocked": float(round(total_restocked, 3)),
        "consumption_count": consumption_count,
        "restock_count": restock_count,
        "avg_daily_consumption": float(round(avg_daily_consumption, 4)),
        "avg_monthly_consumption": float(round(avg_monthly_consumption, 3)),
        "estimated_days_remaining": estimated_days_remaining,
        "estimated_monthly_cost": estimated_monthly_cost,
        "avg_restock_interval_days": avg_restock_interval_days,
        "current_stock": float(product.stock),
        "unit": product.unit,
    }
