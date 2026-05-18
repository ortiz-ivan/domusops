import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.configuration.models import InventorySettings
from apps.expenses.models import FixedExpense, FixedExpensePayment, Income, VariableExpense
from apps.goals.models import SavingsGoal
from apps.household.models import RecurringTask, TaskOccurrence
from apps.purchases.models import Product, ProductConsumption, ProductRestock
from apps.reports.models import FinancialEvent, MonthlyClose


class _Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def _dump(model):
    return list(model.objects.order_by("pk").values())


class Command(BaseCommand):
    help = "Exporta todos los datos del hogar a un archivo JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=None,
            help="Ruta del archivo de salida (por defecto: backup_YYYYMMDD_HHMMSS.json).",
        )
        parser.add_argument(
            "--sin-eventos",
            action="store_true",
            help="Omite el historial de eventos financieros (puede ser voluminoso).",
        )

    def handle(self, *args, **options):
        ts = timezone.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(options["output"] or f"backup_{ts}.json")

        financial_events = [] if options["sin_eventos"] else _dump(FinancialEvent)

        data = {
            "version": 1,
            "exported_at": timezone.now().isoformat(),
            "configuration": {
                "settings": InventorySettings.get_solo().config,
            },
            "purchases": {
                "products": _dump(Product),
                "consumptions": _dump(ProductConsumption),
                "restocks": _dump(ProductRestock),
            },
            "expenses": {
                "fixed_expenses": _dump(FixedExpense),
                "fixed_expense_payments": _dump(FixedExpensePayment),
                "incomes": _dump(Income),
                "variable_expenses": _dump(VariableExpense),
            },
            "reports": {
                "monthly_closes": _dump(MonthlyClose),
                "financial_events": financial_events,
            },
            "household": {
                "recurring_tasks": _dump(RecurringTask),
                "task_occurrences": _dump(TaskOccurrence),
            },
            "goals": {
                "savings_goals": _dump(SavingsGoal),
            },
        }

        output_path.write_text(
            json.dumps(data, cls=_Encoder, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        totals = [
            ("productos",            len(data["purchases"]["products"])),
            ("consumos",             len(data["purchases"]["consumptions"])),
            ("reposiciones",         len(data["purchases"]["restocks"])),
            ("gastos fijos",         len(data["expenses"]["fixed_expenses"])),
            ("pagos fijos",          len(data["expenses"]["fixed_expense_payments"])),
            ("ingresos",             len(data["expenses"]["incomes"])),
            ("gastos variables",     len(data["expenses"]["variable_expenses"])),
            ("cierres mensuales",    len(data["reports"]["monthly_closes"])),
            ("eventos financieros",  len(data["reports"]["financial_events"])),
            ("tareas recurrentes",   len(data["household"]["recurring_tasks"])),
            ("ocurrencias",          len(data["household"]["task_occurrences"])),
            ("metas",                len(data["goals"]["savings_goals"])),
        ]

        self.stdout.write(self.style.SUCCESS(f"\nExportado: {output_path.resolve()}"))
        for label, count in totals:
            self.stdout.write(f"  {label}: {count}")
