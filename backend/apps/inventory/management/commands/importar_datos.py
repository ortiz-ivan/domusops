import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.configuration.models import InventorySettings
from apps.expenses.models import FixedExpense, FixedExpensePayment, Income, VariableExpense
from apps.goals.models import SavingsGoal
from apps.household.models import RecurringTask, TaskOccurrence
from apps.purchases.models import Product, ProductConsumption, ProductRestock
from apps.reports.models import FinancialEvent, MonthlyClose

EXPORT_VERSION = 1

# Campos gestionados automáticamente por Django (auto_now / auto_now_add).
# bulk_create los sobreescribiría con la hora actual, así que los excluimos
# del import; los valores originales se pierden pero los datos de negocio no.
_SKIP = {"created_at", "updated_at"}

# Campos Decimal por modelo: vienen como strings en JSON y deben convertirse.
_DECIMAL: dict[type, set[str]] = {
    Product:             {"stock", "stock_min", "price"},
    FixedExpense:        {"monthly_amount"},
    FixedExpensePayment: {"amount"},
    Income:              {"amount"},
    VariableExpense:     {"amount"},
    ProductConsumption:  {"quantity"},
    ProductRestock:      {"quantity", "unit_cost"},
    FinancialEvent:      {"amount"},
    SavingsGoal:         {"target_amount", "current_amount"},
}


def _reset_sequence(model):
    """Avanza la secuencia de PK hasta el MAX(id) actual (necesario tras bulk_create con PKs explícitas)."""
    table = model._meta.db_table
    pk_col = model._meta.pk.column
    with connection.cursor() as cur:
        cur.execute(f"SELECT MAX({pk_col}) FROM {table}")
        max_id = cur.fetchone()[0]
        if max_id is not None:
            cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), %s, true)",
                [max_id],
            )


def _insert(model, rows, ignore_conflicts=False):
    if not rows:
        return 0
    decimal_fields = _DECIMAL.get(model, set())
    objs = []
    for row in rows:
        cleaned = {k: v for k, v in row.items() if k not in _SKIP}
        for f in decimal_fields:
            if cleaned.get(f) is not None:
                cleaned[f] = Decimal(str(cleaned[f]))
        objs.append(model(**cleaned))
    model.objects.bulk_create(objs, ignore_conflicts=ignore_conflicts)
    _reset_sequence(model)
    return len(objs)


class Command(BaseCommand):
    help = "Importa datos desde un archivo JSON generado por exportar_datos."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta del archivo de backup JSON.")
        parser.add_argument(
            "--modo",
            choices=["reemplazar", "fusionar"],
            default="reemplazar",
            help=(
                "'reemplazar' (por defecto): borra todo y restaura desde el backup. "
                "'fusionar': inserta solo registros que no existan (por PK)."
            ),
        )

    def handle(self, *args, **options):
        path = Path(options["archivo"])
        if not path.exists():
            raise CommandError(f"Archivo no encontrado: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON inválido: {e}")

        version = data.get("version")
        if version != EXPORT_VERSION:
            raise CommandError(
                f"Versión de backup '{version}' no soportada (esperada: {EXPORT_VERSION})."
            )

        modo = options["modo"]
        self.stdout.write(f"Importando {path.name}  (modo={modo}) ...")

        with transaction.atomic():
            if modo == "reemplazar":
                self._borrar_todo()
            self._restaurar(data, ignore_conflicts=(modo == "fusionar"))

        self.stdout.write(self.style.SUCCESS("Importación completada."))

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _borrar_todo(self):
        # Orden inverso a las FK para evitar violaciones de integridad.
        TaskOccurrence.objects.all().delete()
        FinancialEvent.objects.all().delete()
        MonthlyClose.objects.all().delete()
        ProductConsumption.objects.all().delete()
        ProductRestock.objects.all().delete()
        FixedExpensePayment.objects.all().delete()
        RecurringTask.objects.all().delete()
        VariableExpense.objects.all().delete()
        Income.objects.all().delete()
        FixedExpense.objects.all().delete()
        Product.objects.all().delete()
        SavingsGoal.objects.all().delete()
        InventorySettings.objects.all().delete()
        self.stdout.write("  Datos anteriores eliminados.")

    def _restaurar(self, data, ignore_conflicts):
        cfg = data.get("configuration", {})
        settings_config = cfg.get("settings")
        if settings_config is not None:
            InventorySettings.objects.update_or_create(
                pk=1, defaults={"config": settings_config}
            )

        p = data.get("purchases", {})
        e = data.get("expenses", {})
        r = data.get("reports", {})
        h = data.get("household", {})
        g = data.get("goals", {})

        # Orden de inserción respeta FK (padres antes que hijos).
        steps = [
            (Product,             p.get("products", [])),
            (FixedExpense,        e.get("fixed_expenses", [])),
            (SavingsGoal,         g.get("savings_goals", [])),
            (RecurringTask,       h.get("recurring_tasks", [])),
            (Income,              e.get("incomes", [])),
            (VariableExpense,     e.get("variable_expenses", [])),
            (FixedExpensePayment, e.get("fixed_expense_payments", [])),
            (ProductConsumption,  p.get("consumptions", [])),
            (ProductRestock,      p.get("restocks", [])),
            (MonthlyClose,        r.get("monthly_closes", [])),
            (FinancialEvent,      r.get("financial_events", [])),
            (TaskOccurrence,      h.get("task_occurrences", [])),
        ]

        labels = {
            Product: "productos",
            FixedExpense: "gastos fijos",
            SavingsGoal: "metas",
            RecurringTask: "tareas recurrentes",
            Income: "ingresos",
            VariableExpense: "gastos variables",
            FixedExpensePayment: "pagos fijos",
            ProductConsumption: "consumos",
            ProductRestock: "reposiciones",
            MonthlyClose: "cierres mensuales",
            FinancialEvent: "eventos financieros",
            TaskOccurrence: "ocurrencias",
        }

        for model, rows in steps:
            count = _insert(model, rows, ignore_conflicts)
            self.stdout.write(f"  {labels[model]}: {count}")
