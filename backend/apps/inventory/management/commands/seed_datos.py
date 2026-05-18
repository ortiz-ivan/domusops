"""
Crea datos de ejemplo realistas (hogar paraguayo, moneda PYG).
Genera 3 meses cerrados + el mes en curso parcial para que funcionen
proyecciones, detección de anomalías, presupuesto por categoría y reportes.
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.configuration.models import InventorySettings
from apps.expenses.models import FixedExpense, FixedExpensePayment, Income, VariableExpense
from apps.goals.models import SavingsGoal
from apps.household.models import RecurringTask, TaskOccurrence
from apps.purchases.models import Product, ProductConsumption, ProductRestock
from apps.reports.models import MonthlyClose
from apps.reports.services import create_monthly_close


def _mes(n_atras=0):
    """Devuelve (year, month) para N meses atrás desde hoy."""
    today = timezone.localdate()
    m = today.month - n_atras
    y = today.year
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def _d(year, month, day):
    """date() capando el día en 28 para evitar desbordamiento de mes."""
    return date(year, month, min(day, 28))


# ---------------------------------------------------------------------------
# Catálogos de datos
# ---------------------------------------------------------------------------

_PRODUCTOS = [
    dict(name="Arroz",            category="food",     unit="kg",      stock=Decimal("4.5"), stock_min=Decimal("2"),   price=Decimal("5500"),  usage_frequency="high"),
    dict(name="Aceite girasol",   category="food",     unit="l",       stock=Decimal("1"),   stock_min=Decimal("1"),   price=Decimal("12000"), usage_frequency="medium"),
    dict(name="Yerba mate",       category="food",     unit="kg",      stock=Decimal("0.5"), stock_min=Decimal("1"),   price=Decimal("18000"), usage_frequency="high"),
    dict(name="Jabón de ropa",    category="cleaning", unit="kg",      stock=Decimal("1.5"), stock_min=Decimal("1"),   price=Decimal("8500"),  usage_frequency="medium"),
    dict(name="Detergente",       category="cleaning", unit="l",       stock=Decimal("0.8"), stock_min=Decimal("0.5"), price=Decimal("11000"), usage_frequency="medium"),
    dict(name="Papel higiénico",  category="hygiene",  unit="paquete", stock=Decimal("3"),   stock_min=Decimal("2"),   price=Decimal("28000"), usage_frequency="high"),
    dict(name="Shampoo",          category="hygiene",  unit="unidad",  stock=Decimal("1"),   stock_min=Decimal("1"),   price=Decimal("22000"), usage_frequency="medium"),
]

_GASTOS_FIJOS = [
    dict(name="Alquiler",           category="home",         monthly_amount=Decimal("1500000"), budget_bucket="needs"),
    dict(name="ANDE electricidad",  category="services",     monthly_amount=Decimal("185000"),  budget_bucket="needs"),
    dict(name="ESSAP agua",         category="services",     monthly_amount=Decimal("48000"),   budget_bucket="needs"),
    dict(name="TIGO internet",      category="services",     monthly_amount=Decimal("120000"),  budget_bucket="needs"),
    dict(name="Netflix",            category="subscription", monthly_amount=Decimal("35000"),   budget_bucket="wants"),
]

# Gastos variables por mes: lista de (descripción, categoría, monto, bucket, estado)
_GASTOS_VARIABLES_NORMALES = [
    ("Supermercado quincena 1",  "food",        Decimal("250000"), "needs",   "paid"),
    ("Supermercado quincena 2",  "food",        Decimal("210000"), "needs",   "paid"),
    ("Carnicería",               "food",        Decimal("180000"), "needs",   "paid"),
    ("Transporte",               "mobility",    Decimal("120000"), "needs",   "paid"),
    ("Almuerzo trabajo",         "food",        Decimal("80000"),  "needs",   "paid"),
    ("Farmacia",                 "hygiene",     Decimal("45000"),  "needs",   "paid"),
    ("Salida cine/resto",        "leisure",     Decimal("70000"),  "wants",   "paid"),
]

# Mes -1: anomalía en "maintenance" para activar detección
_GASTOS_VARIABLES_ANOMALIA = [
    ("Supermercado quincena 1",  "food",        Decimal("255000"), "needs",   "paid"),
    ("Supermercado quincena 2",  "food",        Decimal("215000"), "needs",   "paid"),
    ("Carnicería",               "food",        Decimal("185000"), "needs",   "paid"),
    ("Transporte",               "mobility",    Decimal("125000"), "needs",   "paid"),
    ("Almuerzo trabajo",         "food",        Decimal("80000"),  "needs",   "paid"),
    ("Farmacia",                 "hygiene",     Decimal("45000"),  "needs",   "paid"),
    ("Reparación electrodomést", "maintenance", Decimal("380000"), "needs",   "paid"),  # ← anomalía
    ("Salida cine/resto",        "leisure",     Decimal("75000"),  "wants",   "paid"),
]

# Mes actual: solo primeros gastos (mes parcial)
_GASTOS_VARIABLES_PARCIALES = [
    ("Supermercado",             "food",        Decimal("265000"), "needs",   "paid"),
    ("Transporte",               "mobility",    Decimal("60000"),  "needs",   "paid"),
    ("Farmacia",                 "hygiene",     Decimal("45000"),  "needs",   "committed"),
]

_METAS = [
    dict(name="Fondo de emergencia",  goal_type="savings",      target_amount=Decimal("5000000"), current_amount=Decimal("1500000"), notes="3 meses de gastos fijos"),
    dict(name="Vacaciones 2027",      goal_type="big_purchase",  target_amount=Decimal("3000000"), current_amount=Decimal("250000"),  target_date=date(2027, 1, 1)),
    dict(name="Deuda tarjeta",        goal_type="debt",          target_amount=Decimal("800000"),  current_amount=Decimal("500000"),  notes="Saldo pendiente"),
]

_TAREAS = [
    dict(title="Limpieza general del hogar", category="cleaning",  area="living_room",  frequency_type="weekly",  interval=1, priority="high",   estimated_minutes=90),
    dict(title="Limpiar baño",               category="cleaning",  area="bathroom",     frequency_type="weekly",  interval=1, priority="medium", estimated_minutes=30),
    dict(title="Pago de servicios",          category="payments",  area="home_admin",   frequency_type="monthly", interval=1, priority="high",   estimated_minutes=20),
    dict(title="Compras del mes",            category="shopping",  area="home_admin",   frequency_type="monthly", interval=1, priority="high",   estimated_minutes=60),
    dict(title="Lavar ropa",                 category="routine",   area="laundry",      frequency_type="weekly",  interval=1, priority="medium", estimated_minutes=40),
]


class Command(BaseCommand):
    help = "Crea datos de ejemplo realistas. Genera 3 meses cerrados + mes actual parcial."

    def add_arguments(self, parser):
        parser.add_argument(
            "--forzar",
            action="store_true",
            help="Borra todos los datos existentes antes de crear el seed.",
        )

    def handle(self, *args, **options):
        if not options["forzar"] and self._hay_datos():
            raise CommandError(
                "Ya existen datos en la base de datos.\n"
                "Usa --forzar para borrar todo y crear datos de ejemplo."
            )

        with transaction.atomic():
            if options["forzar"]:
                self._borrar_todo()

            self._configurar_presupuestos()
            products = self._crear_productos()
            fixed = self._crear_gastos_fijos()
            self._crear_metas()
            tasks = self._crear_tareas(fixed)

            # 3 meses históricos cerrados
            for n in range(3, 0, -1):
                y, m = _mes(n)
                gastos = _GASTOS_VARIABLES_ANOMALIA if n == 1 else _GASTOS_VARIABLES_NORMALES
                self._crear_mes(y, m, products, fixed, gastos, cerrar=True)

            # Mes actual parcial
            y, m = _mes(0)
            self._crear_mes(y, m, products, fixed, _GASTOS_VARIABLES_PARCIALES, cerrar=False)

            self._crear_ocurrencias_tareas(tasks)

        self._imprimir_resumen()

    # ------------------------------------------------------------------
    # Helpers de alto nivel
    # ------------------------------------------------------------------

    def _hay_datos(self):
        return Product.objects.exists() or Income.objects.exists()

    def _borrar_todo(self):
        TaskOccurrence.objects.all().delete()
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

    def _configurar_presupuestos(self):
        settings = InventorySettings.get_solo()
        config = settings.config
        budgets = {
            "food":        600000,
            "cleaning":    90000,
            "hygiene":     90000,
            "mobility":    150000,
            "leisure":     100000,
            "maintenance": 200000,
        }
        for cat in config.get("categories", []):
            if cat["value"] in budgets:
                cat["monthly_budget"] = budgets[cat["value"]]
        settings.config = config
        settings.save()

    def _crear_productos(self):
        products = {}
        for data in _PRODUCTOS:
            p = Product.objects.create(**data)
            products[p.name] = p
        return products

    def _crear_gastos_fijos(self):
        fixed = {}
        for data in _GASTOS_FIJOS:
            f = FixedExpense.objects.create(**data)
            fixed[f.name] = f
        return fixed

    def _crear_metas(self):
        for data in _METAS:
            SavingsGoal.objects.create(**data)

    def _crear_tareas(self, fixed):
        tasks = {}
        for data in _TAREAS:
            t = RecurringTask.objects.create(
                **data,
                start_date=_d(*_mes(3), 1),
            )
            tasks[t.title] = t
        # Vincular tarea de pagos con gasto fijo "Alquiler"
        pago_task = tasks.get("Pago de servicios")
        if pago_task and "Alquiler" in fixed:
            pago_task.integration_kind = RecurringTask.INTEGRATION_FIXED_EXPENSE
            pago_task.linked_fixed_expense = fixed["Alquiler"]
            pago_task.save(update_fields=["integration_kind", "linked_fixed_expense"])
        return tasks

    # ------------------------------------------------------------------
    # Datos mensuales
    # ------------------------------------------------------------------

    def _crear_mes(self, year, month, products, fixed, gastos_variables, cerrar):
        # Ingreso del mes
        Income.objects.create(
            amount=Decimal("3500000"),
            source="Salario",
            date=_d(year, month, 5),
        )

        # Gastos variables
        for desc, cat, monto, bucket, estado in gastos_variables:
            VariableExpense.objects.create(
                amount=monto,
                category=cat,
                budget_bucket=bucket,
                description=desc,
                status=estado,
                date=_d(year, month, 15),
            )

        # Pagos de gastos fijos
        for f in fixed.values():
            FixedExpensePayment.objects.create(
                fixed_expense=f,
                amount=f.monthly_amount,
                date=_d(year, month, 5),
            )

        # Reposiciones y consumos de productos
        for name, product in products.items():
            ProductRestock.objects.create(
                product=product,
                quantity=Decimal("3"),
                unit_cost=product.price,
                date=_d(year, month, 3),
            )
            ProductConsumption.objects.create(
                product=product,
                quantity=Decimal("2"),
                date=_d(year, month, 20),
            )

        if cerrar:
            create_monthly_close(month, year, notes="Cierre generado por seed_datos")

    def _crear_ocurrencias_tareas(self, tasks):
        today = timezone.localdate()

        for n in range(3, 0, -1):
            y, m = _mes(n)
            for task in tasks.values():
                due = _d(y, m, 10 if task.frequency_type == "monthly" else 7)
                TaskOccurrence.objects.get_or_create(
                    recurring_task=task,
                    due_date=due,
                    defaults={"status": "done", "completed_at": timezone.now()},
                )

        # Mes actual: pendientes
        y, m = _mes(0)
        for task in tasks.values():
            due = _d(y, m, 10 if task.frequency_type == "monthly" else 7)
            if due <= today:
                TaskOccurrence.objects.get_or_create(
                    recurring_task=task,
                    due_date=due,
                    defaults={"status": "pending"},
                )

    def _imprimir_resumen(self):
        y0, m0 = _mes(3)
        y1, m1 = _mes(0)
        self.stdout.write(self.style.SUCCESS("\nSeed completado:"))
        self.stdout.write(f"  Productos:              {Product.objects.count()}")
        self.stdout.write(f"  Gastos fijos:           {FixedExpense.objects.count()}")
        self.stdout.write(f"  Meses cerrados:         {MonthlyClose.objects.count()}  ({m0:02d}/{y0} → {_mes(1)[1]:02d}/{_mes(1)[0]})")
        self.stdout.write(f"  Mes actual:             {m1:02d}/{y1}  (parcial, sin cerrar)")
        self.stdout.write(f"  Ingresos:               {Income.objects.count()}")
        self.stdout.write(f"  Gastos variables:       {VariableExpense.objects.count()}")
        self.stdout.write(f"  Tareas recurrentes:     {RecurringTask.objects.count()}")
        self.stdout.write(f"  Ocurrencias de tareas:  {TaskOccurrence.objects.count()}")
        self.stdout.write(f"  Metas:                  {SavingsGoal.objects.count()}")
        self.stdout.write(f"  Reposiciones:           {ProductRestock.objects.count()}")
        self.stdout.write("")
        self.stdout.write("  El mes anterior tiene un gasto de 'maintenance' elevado → activa detección de anomalías.")
        self.stdout.write("  Presupuesto por categoría configurado en food / mobility / leisure / maintenance.")
