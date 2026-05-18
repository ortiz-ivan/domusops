import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.expenses.models import FixedExpense, FixedExpensePayment, Income, VariableExpense
from apps.goals.models import SavingsGoal
from apps.household.models import RecurringTask, TaskOccurrence
from apps.purchases.models import Product, ProductConsumption, ProductRestock
from apps.reports.models import MonthlyClose


class TestSeedDatos:
    def test_crea_datos_en_db_vacia(self, db):
        call_command("seed_datos")
        assert Product.objects.count() > 0

    def test_falla_si_ya_hay_datos(self, db):
        Product.objects.create(name="Preexistente", category="food")
        with pytest.raises(CommandError, match="Ya existen datos"):
            call_command("seed_datos")

    def test_forzar_borra_y_recrea(self, db):
        Product.objects.create(name="Preexistente", category="food")
        call_command("seed_datos", forzar=True)
        assert not Product.objects.filter(name="Preexistente").exists()
        assert Product.objects.count() > 0

    def test_crea_exactamente_7_productos(self, db):
        call_command("seed_datos")
        assert Product.objects.count() == 7

    def test_crea_exactamente_5_gastos_fijos(self, db):
        call_command("seed_datos")
        assert FixedExpense.objects.count() == 5

    def test_crea_3_meses_cerrados(self, db):
        call_command("seed_datos")
        assert MonthlyClose.objects.count() == 3

    def test_mes_actual_no_tiene_cierre(self, db):
        from django.utils import timezone
        today = timezone.localdate()
        call_command("seed_datos")
        assert not MonthlyClose.objects.filter(month=today.month, year=today.year).exists()

    def test_crea_ingresos_para_4_meses(self, db):
        call_command("seed_datos")
        # 1 ingreso por mes × 4 meses (3 cerrados + actual)
        assert Income.objects.count() == 4

    def test_todos_los_meses_tienen_pagos_fijos(self, db):
        call_command("seed_datos")
        # 5 gastos fijos × 4 meses
        assert FixedExpensePayment.objects.count() == 20

    def test_reposiciones_minimas_para_deteccion_anomalias(self, db):
        """Cada producto tiene ≥3 reposiciones (requisito de detect_financial_anomalies)."""
        call_command("seed_datos")
        for product in Product.objects.all():
            assert product.restocks.count() >= 3, (
                f"{product.name} tiene solo {product.restocks.count()} reposiciones"
            )

    def test_mes_anomalia_tiene_gasto_maintenance_elevado(self, db):
        from apps.inventory.management.commands.seed_datos import _mes
        from decimal import Decimal
        call_command("seed_datos")
        y, m = _mes(1)
        mantenimiento = VariableExpense.objects.filter(
            category="maintenance", date__year=y, date__month=m
        )
        assert mantenimiento.exists()
        assert mantenimiento.first().amount >= Decimal("300000")

    def test_crea_metas(self, db):
        call_command("seed_datos")
        assert SavingsGoal.objects.count() == 3

    def test_crea_tareas_recurrentes(self, db):
        call_command("seed_datos")
        assert RecurringTask.objects.count() == 5

    def test_crea_ocurrencias_de_tareas(self, db):
        call_command("seed_datos")
        assert TaskOccurrence.objects.count() > 0

    def test_ocurrencias_historicas_estan_completadas(self, db):
        from apps.inventory.management.commands.seed_datos import _mes
        call_command("seed_datos")
        y, m = _mes(2)
        ocurrencias = TaskOccurrence.objects.filter(due_date__year=y, due_date__month=m)
        assert ocurrencias.exists()
        assert all(o.status == "done" for o in ocurrencias)

    def test_configura_presupuesto_por_categoria(self, db):
        from apps.configuration.models import InventorySettings, get_category_monthly_budget
        call_command("seed_datos")
        config = InventorySettings.get_solo().get_config()
        assert get_category_monthly_budget(config, "food") is not None
        assert get_category_monthly_budget(config, "mobility") is not None

    def test_cierres_tienen_snapshot(self, db):
        call_command("seed_datos")
        for close in MonthlyClose.objects.all():
            assert isinstance(close.summary_snapshot, dict)
            assert len(close.summary_snapshot) > 0

    def test_deteccion_anomalias_encuentra_algo(self, db):
        """Con los datos del seed, detect_financial_anomalies debe encontrar al menos una anomalía."""
        from apps.inventory.management.commands.seed_datos import _mes
        from apps.reports.services import detect_financial_anomalies
        call_command("seed_datos")
        y, m = _mes(1)
        anomalias = detect_financial_anomalies(m, y)
        assert len(anomalias) > 0, "El seed debería generar al menos una anomalía detectable"
