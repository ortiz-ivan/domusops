import json
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.configuration.models import InventorySettings
from apps.expenses.models import FixedExpense, FixedExpensePayment, Income, VariableExpense
from apps.goals.models import SavingsGoal
from apps.household.models import RecurringTask, TaskOccurrence
from apps.purchases.models import Product, ProductConsumption, ProductRestock
from apps.reports.models import FinancialEvent, MonthlyClose


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def datos(db):
    """Conjunto mínimo de datos que cubre todas las relaciones FK."""
    product = Product.objects.create(
        name="Arroz", category="food", stock=Decimal("5"), stock_min=Decimal("2"),
        unit="kg", price=Decimal("5500"),
    )
    fixed = FixedExpense.objects.create(
        name="Alquiler", category="home", monthly_amount=Decimal("500000"),
    )
    FixedExpensePayment.objects.create(
        fixed_expense=fixed, amount=Decimal("500000"), date="2026-05-01",
    )
    ProductConsumption.objects.create(product=product, quantity=Decimal("1"))
    ProductRestock.objects.create(product=product, quantity=Decimal("3"), unit_cost=Decimal("5000"))
    Income.objects.create(amount=Decimal("1000000"), source="Salario")
    VariableExpense.objects.create(amount=Decimal("50000"), category="mobility")
    MonthlyClose.objects.create(month=4, year=2026, notes="Cierre abril")
    SavingsGoal.objects.create(
        name="Fondo emergencia", goal_type="savings", target_amount=Decimal("2000000"),
    )
    task = RecurringTask.objects.create(title="Limpiar baño", frequency_type="weekly", interval=1)
    TaskOccurrence.objects.create(recurring_task=task, due_date="2026-05-15", status="done")
    return {"product": product, "fixed": fixed, "task": task}


def _exportar(tmp_path, **kwargs):
    output = tmp_path / "backup.json"
    call_command("exportar_datos", output=str(output), **kwargs)
    return output


def _borrar_datos():
    """Elimina todos los registros de negocio en orden seguro."""
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


# ---------------------------------------------------------------------------
# exportar_datos
# ---------------------------------------------------------------------------

class TestExportarDatos:
    def test_crea_archivo_json(self, datos, tmp_path):
        output = _exportar(tmp_path)
        assert output.exists()

    def test_version_en_archivo(self, datos, tmp_path):
        data = json.loads(_exportar(tmp_path).read_text("utf-8"))
        assert data["version"] == 1
        assert "exported_at" in data

    def test_contiene_todos_los_modelos(self, datos, tmp_path):
        data = json.loads(_exportar(tmp_path).read_text("utf-8"))
        assert len(data["purchases"]["products"]) == 1
        assert len(data["purchases"]["consumptions"]) == 1
        assert len(data["purchases"]["restocks"]) == 1
        assert len(data["expenses"]["fixed_expenses"]) == 1
        assert len(data["expenses"]["fixed_expense_payments"]) == 1
        assert len(data["expenses"]["incomes"]) == 1
        assert len(data["expenses"]["variable_expenses"]) == 1
        assert len(data["reports"]["monthly_closes"]) == 1
        assert len(data["goals"]["savings_goals"]) == 1
        assert len(data["household"]["recurring_tasks"]) == 1
        assert len(data["household"]["task_occurrences"]) == 1

    def test_decimal_serializado_como_string(self, datos, tmp_path):
        data = json.loads(_exportar(tmp_path).read_text("utf-8"))
        product = data["purchases"]["products"][0]
        assert isinstance(product["price"], str)
        assert product["price"] == "5500.00"

    def test_sin_eventos_omite_historial(self, datos, tmp_path):
        data = json.loads(_exportar(tmp_path, sin_eventos=True).read_text("utf-8"))
        assert data["reports"]["financial_events"] == []

    def test_exporta_configuracion(self, datos, tmp_path):
        data = json.loads(_exportar(tmp_path).read_text("utf-8"))
        assert "settings" in data["configuration"]
        assert "categories" in data["configuration"]["settings"]


# ---------------------------------------------------------------------------
# importar_datos — modo reemplazar
# ---------------------------------------------------------------------------

class TestImportarReemplazar:
    def test_restaura_todos_los_modelos(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)
        _borrar_datos()

        call_command("importar_datos", str(backup))

        assert Product.objects.count() == 1
        assert ProductConsumption.objects.count() == 1
        assert ProductRestock.objects.count() == 1
        assert FixedExpense.objects.count() == 1
        assert FixedExpensePayment.objects.count() == 1
        assert Income.objects.count() == 1
        assert VariableExpense.objects.count() == 1
        assert MonthlyClose.objects.count() == 1
        assert SavingsGoal.objects.count() == 1
        assert RecurringTask.objects.count() == 1
        assert TaskOccurrence.objects.count() == 1

    def test_preserva_pks(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)
        pk_producto = datos["product"].pk
        pk_tarea = datos["task"].pk

        call_command("importar_datos", str(backup))

        assert Product.objects.filter(pk=pk_producto).exists()
        assert RecurringTask.objects.filter(pk=pk_tarea).exists()

    def test_preserva_valores_decimal(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)
        stock_original = datos["product"].stock

        call_command("importar_datos", str(backup))

        assert Product.objects.get(name="Arroz").stock == stock_original

    def test_preserva_relacion_fk_tarea_ocurrencia(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)

        call_command("importar_datos", str(backup))

        task = RecurringTask.objects.get(title="Limpiar baño")
        occ = TaskOccurrence.objects.get(recurring_task=task)
        assert occ.status == "done"

    def test_borra_datos_previos_antes_de_restaurar(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)
        # Crear un producto extra que NO está en el backup
        Product.objects.create(name="Extra", category="food")

        call_command("importar_datos", str(backup))

        assert Product.objects.count() == 1
        assert not Product.objects.filter(name="Extra").exists()

    def test_restaura_configuracion(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)
        # Modificar la configuración
        settings = InventorySettings.get_solo()
        original_config = settings.config.copy()
        settings.config["currency"] = {"code": "USD"}
        settings.save()

        call_command("importar_datos", str(backup))

        assert InventorySettings.get_solo().config["currency"] == original_config["currency"]

    def test_secuencia_pk_avanza_correctamente(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)
        call_command("importar_datos", str(backup))

        # Crear un nuevo registro: no debe fallar por conflicto de PK
        new_product = Product.objects.create(name="Nuevo", category="food")
        assert new_product.pk > datos["product"].pk


# ---------------------------------------------------------------------------
# importar_datos — modo fusionar
# ---------------------------------------------------------------------------

class TestImportarFusionar:
    def test_no_duplica_registros_existentes(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)

        call_command("importar_datos", str(backup), modo="fusionar")

        assert Product.objects.count() == 1
        assert Income.objects.count() == 1

    def test_inserta_registros_nuevos(self, datos, tmp_path):
        backup = _exportar(tmp_path, sin_eventos=True)
        # Borrar solo el producto para que sea "nuevo" al fusionar
        ProductConsumption.objects.all().delete()
        ProductRestock.objects.all().delete()
        RecurringTask.objects.all().delete()
        Product.objects.filter(name="Arroz").delete()

        call_command("importar_datos", str(backup), modo="fusionar")

        assert Product.objects.filter(name="Arroz").exists()


# ---------------------------------------------------------------------------
# importar_datos — errores
# ---------------------------------------------------------------------------

class TestImportarErrores:
    def test_archivo_inexistente_lanza_error(self, db, tmp_path):
        with pytest.raises(CommandError, match="no encontrado"):
            call_command("importar_datos", str(tmp_path / "no_existe.json"))

    def test_json_invalido_lanza_error(self, db, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("esto no es json", encoding="utf-8")
        with pytest.raises(CommandError, match="JSON inválido"):
            call_command("importar_datos", str(bad))

    def test_version_incompatible_lanza_error(self, db, tmp_path):
        bad = tmp_path / "v99.json"
        bad.write_text(json.dumps({"version": 99}), encoding="utf-8")
        with pytest.raises(CommandError, match="no soportada"):
            call_command("importar_datos", str(bad))
