"""
Tests para el management command 'purgar_historial'.

Los tests que verifican el límite exacto del corte asumen que hoy es ≈ mayo 2026
(fecha hardcodeada en el proyecto). Los tests de purga general usan 2020, que
siempre estará fuera del período de retención de 24 meses.
"""
from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.reports.management.commands.purgar_historial import _subtract_months
from apps.reports.models import FinancialEvent, MonthlyClose

# today ≈ 2026-05-20
_TODAY_YEAR = 2026
_TODAY_MONTH = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(month, year, entity_type="variable_expense", action="created"):
    return FinancialEvent.objects.create(
        entity_type=entity_type,
        action=action,
        entity_id=1,
        title="Test",
        month=month,
        year=year,
        effective_date=date(year, month, 1),
    )


def _make_close(month, year):
    return MonthlyClose.objects.create(month=month, year=year)


def _run(**kwargs):
    out = StringIO()
    call_command("purgar_historial", stdout=out, **kwargs)
    return out.getvalue()


# ---------------------------------------------------------------------------
# _subtract_months (helper puro, sin DB)
# ---------------------------------------------------------------------------

class TestSubtractMonths:
    def test_resta_anios_completos(self):
        assert _subtract_months(2026, 5, 24) == (2024, 5)

    def test_resta_meses_simples(self):
        assert _subtract_months(2026, 5, 3) == (2026, 2)

    def test_desbordamiento_mes(self):
        assert _subtract_months(2026, 2, 3) == (2025, 11)

    def test_un_mes(self):
        assert _subtract_months(2026, 5, 1) == (2026, 4)

    def test_enero_menos_uno(self):
        assert _subtract_months(2026, 1, 1) == (2025, 12)

    def test_doce_meses(self):
        assert _subtract_months(2026, 5, 12) == (2025, 5)

    def test_trece_meses(self):
        assert _subtract_months(2026, 5, 13) == (2025, 4)


# ---------------------------------------------------------------------------
# Command behaviour
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPurgarHistorial:

    def test_sin_eventos_informa(self):
        out = _run()
        assert "No hay eventos" in out

    def test_meses_cero_lanza_error(self):
        with pytest.raises((CommandError, SystemExit)):
            _run(meses=0)

    def test_meses_negativo_lanza_error(self):
        with pytest.raises((CommandError, SystemExit)):
            _run(meses=-5)

    # --- dry-run ---

    def test_dry_run_no_elimina(self):
        _make_event(1, 2020)
        _run(dry_run=True)
        assert FinancialEvent.objects.count() == 1

    def test_dry_run_indica_en_salida(self):
        _make_event(1, 2020)
        out = _run(dry_run=True)
        assert "Dry run" in out or "DRY RUN" in out

    def test_dry_run_muestra_total(self):
        _make_event(1, 2020)
        _make_event(2, 2020)
        out = _run(dry_run=True)
        assert "2" in out

    # --- purga real ---

    def test_purga_eventos_antiguos(self):
        _make_event(1, 2020)
        _make_close(1, 2020)
        _run(meses=24)
        assert FinancialEvent.objects.count() == 0

    def test_conserva_eventos_recientes(self):
        old = _make_event(1, 2020)
        recent = _make_event(_TODAY_MONTH, _TODAY_YEAR)
        _make_close(1, 2020)
        _run(meses=24)
        assert not FinancialEvent.objects.filter(id=old.id).exists()
        assert FinancialEvent.objects.filter(id=recent.id).exists()

    def test_informa_total_eliminados(self):
        _make_event(1, 2020)
        _make_event(2, 2020)
        _make_close(1, 2020)
        _make_close(2, 2020)
        out = _run(meses=24)
        assert "2" in out

    # --- límite exacto del corte (asume hoy ≈ mayo 2026) ---

    def test_conserva_mes_exacto_del_corte(self):
        # Con --meses 24 y hoy = mayo 2026, corte = mayo 2024.
        # Mayo 2024 debe conservarse; abril 2024 debe purgarse.
        at_cutoff = _make_event(5, 2024)
        before_cutoff = _make_event(4, 2024)
        _make_close(4, 2024)
        _run(meses=24)
        assert FinancialEvent.objects.filter(id=at_cutoff.id).exists()
        assert not FinancialEvent.objects.filter(id=before_cutoff.id).exists()

    def test_meses_parametro_personalizado(self):
        # Con --meses 1 y hoy = mayo 2026, corte = abril 2026.
        # Marzo 2026 → purgado; abril 2026 → conservado.
        old = _make_event(3, 2026)
        _make_close(3, 2026)
        kept = _make_event(4, 2026)
        _run(meses=1)
        assert not FinancialEvent.objects.filter(id=old.id).exists()
        assert FinancialEvent.objects.filter(id=kept.id).exists()

    # --- advertencias sobre cierres faltantes ---

    def test_avisa_mes_sin_cierre(self):
        _make_event(1, 2020)  # Sin MonthlyClose
        out = _run(dry_run=True)
        assert "Advertencia" in out
        assert "01/2020" in out

    def test_no_avisa_cuando_cierre_existe(self):
        _make_event(1, 2020)
        _make_close(1, 2020)
        out = _run(dry_run=True)
        assert "Advertencia" not in out

    def test_avisa_solo_meses_sin_cierre(self):
        _make_event(1, 2020)  # Sin cierre → advertencia
        _make_event(2, 2020)
        _make_close(2, 2020)  # Con cierre → sin advertencia
        out = _run(dry_run=True)
        assert "01/2020" in out
        assert "02/2020" not in out

    # --- breakdown por tipo ---

    def test_breakdown_muestra_entity_types(self):
        _make_event(1, 2020, entity_type="income", action="created")
        _make_event(1, 2020, entity_type="variable_expense", action="deleted")
        _make_close(1, 2020)
        out = _run(dry_run=True)
        assert "income" in out
        assert "variable_expense" in out

    def test_multiples_meses_purgados(self):
        for month in range(1, 4):
            _make_event(month, 2020)
            _make_close(month, 2020)
        recent = _make_event(_TODAY_MONTH, _TODAY_YEAR)
        _run(meses=24)
        assert FinancialEvent.objects.count() == 1
        assert FinancialEvent.objects.filter(id=recent.id).exists()
