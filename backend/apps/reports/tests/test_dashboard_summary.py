from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.expenses.models import FixedExpense, FixedExpensePayment, Income, VariableExpense
from apps.goals.models import SavingsGoal
from apps.household.models import RecurringTask, TaskOccurrence
from apps.purchases.models import Product
from apps.reports.services import get_dashboard_summary

DASHBOARD_URL = "/api/v1/dashboard-summary/"


def _today():
    return timezone.localdate()


# ---------------------------------------------------------------------------
# Service: get_dashboard_summary
# ---------------------------------------------------------------------------

class TestGetDashboardSummaryService:
    def test_retorna_claves_requeridas(self, db):
        result = get_dashboard_summary(today=_today())
        expected = {
            "month", "year", "finance_summary",
            "critical_products", "overdue_tasks", "upcoming_tasks",
            "lagging_goals", "anomalies", "anomalies_lookback_months",
        }
        assert expected <= set(result.keys())

    def test_finance_summary_contiene_claves_basicas(self, db):
        summary = get_dashboard_summary(today=_today())["finance_summary"]
        assert "total_income" in summary
        assert "remaining_balance" in summary
        assert "expense_percentage" in summary

    def test_sin_datos_retorna_listas_vacias(self, db):
        result = get_dashboard_summary(today=_today())
        assert result["critical_products"] == []
        assert result["overdue_tasks"] == []
        assert result["upcoming_tasks"] == []
        assert result["lagging_goals"] == []

    def test_detecta_tareas_vencidas(self, db):
        yesterday = _today() - timedelta(days=1)
        task = RecurringTask.objects.create(
            title="Limpiar baño",
            frequency_type="weekly",
            start_date=yesterday,
        )
        TaskOccurrence.objects.create(
            recurring_task=task,
            due_date=yesterday,
            status="pending",
        )
        result = get_dashboard_summary(today=_today())
        assert len(result["overdue_tasks"]) == 1
        assert result["overdue_tasks"][0]["title"] == "Limpiar baño"
        assert result["overdue_tasks"][0]["due_date"] == yesterday.isoformat()

    def test_no_incluye_tareas_completadas_en_vencidas(self, db):
        yesterday = _today() - timedelta(days=1)
        task = RecurringTask.objects.create(
            title="Tarea completada",
            frequency_type="weekly",
            start_date=yesterday,
        )
        TaskOccurrence.objects.create(
            recurring_task=task,
            due_date=yesterday,
            status="done",
        )
        result = get_dashboard_summary(today=_today())
        assert result["overdue_tasks"] == []

    def test_detecta_tareas_proximas_7_dias(self, db):
        in_3_days = _today() + timedelta(days=3)
        task = RecurringTask.objects.create(
            title="Pagar servicios",
            frequency_type="monthly",
            start_date=_today(),
        )
        TaskOccurrence.objects.create(
            recurring_task=task,
            due_date=in_3_days,
            status="pending",
        )
        result = get_dashboard_summary(today=_today())
        assert len(result["upcoming_tasks"]) == 1
        assert result["upcoming_tasks"][0]["title"] == "Pagar servicios"

    def test_no_incluye_tareas_mas_alla_de_7_dias(self, db):
        in_8_days = _today() + timedelta(days=8)
        task = RecurringTask.objects.create(
            title="Tarea lejana",
            frequency_type="monthly",
            start_date=_today(),
        )
        TaskOccurrence.objects.create(
            recurring_task=task,
            due_date=in_8_days,
            status="pending",
        )
        result = get_dashboard_summary(today=_today())
        assert result["upcoming_tasks"] == []

    def test_detecta_metas_con_progreso_bajo(self, db):
        SavingsGoal.objects.create(
            name="Fondo de emergencia",
            target_amount=Decimal("100000"),
            current_amount=Decimal("1000"),
        )
        result = get_dashboard_summary(today=_today())
        assert len(result["lagging_goals"]) == 1
        assert result["lagging_goals"][0]["name"] == "Fondo de emergencia"
        assert result["lagging_goals"][0]["progress_pct"] == 1.0

    def test_no_incluye_metas_con_progreso_suficiente(self, db):
        SavingsGoal.objects.create(
            name="Meta avanzada",
            target_amount=Decimal("10000"),
            current_amount=Decimal("5000"),
        )
        result = get_dashboard_summary(today=_today())
        assert result["lagging_goals"] == []

    def test_no_incluye_metas_inactivas(self, db):
        SavingsGoal.objects.create(
            name="Meta inactiva",
            target_amount=Decimal("10000"),
            current_amount=Decimal("0"),
            is_active=False,
        )
        result = get_dashboard_summary(today=_today())
        assert result["lagging_goals"] == []

    def test_critical_products_limitados_a_5(self, db):
        for i in range(7):
            Product.objects.create(
                name=f"Producto critico {i}",
                category="food",
                type="consumable",
                usage_frequency="high",
                stock=0,
                stock_min=5,
            )
        result = get_dashboard_summary(today=_today())
        assert len(result["critical_products"]) == 5

    def test_producto_critico_incluye_campos_requeridos(self, db):
        Product.objects.create(
            name="Jabon",
            category="cleaning",
            type="consumable",
            usage_frequency="high",
            stock=0,
            stock_min=2,
            unit="unidad",
        )
        result = get_dashboard_summary(today=_today())
        assert len(result["critical_products"]) == 1
        p = result["critical_products"][0]
        assert p["name"] == "Jabon"
        assert p["stock"] == 0.0
        assert p["stock_min"] == 2.0
        assert p["unit"] == "unidad"


# ---------------------------------------------------------------------------
# View: GET /api/v1/dashboard-summary/
# ---------------------------------------------------------------------------

class TestDashboardSummaryView:
    def test_retorna_200(self, api, db):
        response = api.get(DASHBOARD_URL)
        assert response.status_code == 200

    def test_retorna_estructura_completa(self, api, db):
        response = api.get(DASHBOARD_URL)
        assert response.status_code == 200
        data = response.data
        expected_keys = {
            "month", "year", "finance_summary",
            "critical_products", "overdue_tasks", "upcoming_tasks",
            "lagging_goals", "anomalies", "anomalies_lookback_months",
        }
        assert expected_keys <= set(data.keys())

    def test_listas_son_arrays(self, api, db):
        response = api.get(DASHBOARD_URL)
        data = response.data
        assert isinstance(data["critical_products"], list)
        assert isinstance(data["overdue_tasks"], list)
        assert isinstance(data["upcoming_tasks"], list)
        assert isinstance(data["lagging_goals"], list)
        assert isinstance(data["anomalies"], list)

    def test_finance_summary_contiene_total_income(self, api, db):
        today = _today()
        Income.objects.create(amount=Decimal("5000"), date=today)
        response = api.get(DASHBOARD_URL)
        assert response.status_code == 200
        assert response.data["finance_summary"]["total_income"] == 5000.0

    def test_tarea_vencida_aparece_en_respuesta(self, api, db):
        yesterday = _today() - timedelta(days=1)
        task = RecurringTask.objects.create(
            title="Rutina vencida",
            frequency_type="daily",
            start_date=yesterday,
        )
        TaskOccurrence.objects.create(
            recurring_task=task,
            due_date=yesterday,
            status="pending",
        )
        response = api.get(DASHBOARD_URL)
        assert response.status_code == 200
        titles = [t["title"] for t in response.data["overdue_tasks"]]
        assert "Rutina vencida" in titles

    def test_meta_con_progreso_bajo_aparece_en_respuesta(self, api, db):
        SavingsGoal.objects.create(
            name="Ahorro vacaciones",
            target_amount=Decimal("50000"),
            current_amount=Decimal("100"),
        )
        response = api.get(DASHBOARD_URL)
        assert response.status_code == 200
        names = [g["name"] for g in response.data["lagging_goals"]]
        assert "Ahorro vacaciones" in names
