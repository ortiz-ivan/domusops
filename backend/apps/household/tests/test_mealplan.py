import pytest

from apps.household.models import MealPlan

MEALS_BASE = "/api/v1/meal-plans/"


@pytest.fixture
def meal(db):
    return MealPlan.objects.create(date="2026-05-19", meal_time="lunch", name="Pasta")


# ---------------------------------------------------------------------------
# Lista y filtros por rango de fechas
# ---------------------------------------------------------------------------

class TestMealPlanList:
    def test_lista_vacia(self, api):
        response = api.get(MEALS_BASE)
        assert response.status_code == 200
        assert response.data["results"] == []

    def test_lista_comidas(self, api, meal):
        response = api.get(MEALS_BASE)
        assert len(response.data["results"]) == 1

    def test_filtra_desde_fecha(self, api):
        MealPlan.objects.create(date="2026-05-18", meal_time="lunch", name="Antes")
        MealPlan.objects.create(date="2026-05-19", meal_time="lunch", name="Hoy")
        response = api.get(MEALS_BASE, {"from": "2026-05-19"})
        names = [r["name"] for r in response.data["results"]]
        assert "Hoy" in names
        assert "Antes" not in names

    def test_filtra_hasta_fecha(self, api):
        MealPlan.objects.create(date="2026-05-19", meal_time="lunch", name="Hoy")
        MealPlan.objects.create(date="2026-05-26", meal_time="lunch", name="Despues")
        response = api.get(MEALS_BASE, {"to": "2026-05-25"})
        names = [r["name"] for r in response.data["results"]]
        assert "Hoy" in names
        assert "Despues" not in names

    def test_filtra_rango_completo(self, api):
        MealPlan.objects.create(date="2026-05-18", meal_time="lunch", name="Antes")
        MealPlan.objects.create(date="2026-05-19", meal_time="lunch", name="Lunes")
        MealPlan.objects.create(date="2026-05-25", meal_time="lunch", name="Domingo")
        MealPlan.objects.create(date="2026-05-26", meal_time="lunch", name="Despues")
        response = api.get(MEALS_BASE, {"from": "2026-05-19", "to": "2026-05-25"})
        names = [r["name"] for r in response.data["results"]]
        assert "Lunes" in names
        assert "Domingo" in names
        assert "Antes" not in names
        assert "Despues" not in names


# ---------------------------------------------------------------------------
# Creación
# ---------------------------------------------------------------------------

class TestMealPlanCreate:
    def test_crea_comida(self, api):
        payload = {"date": "2026-05-20", "meal_time": "dinner", "name": "Pollo asado"}
        response = api.post(MEALS_BASE, payload, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Pollo asado"

    def test_crea_con_notas(self, api):
        payload = {"date": "2026-05-20", "meal_time": "lunch", "name": "Pasta", "notes": "Con ajo y aceite."}
        response = api.post(MEALS_BASE, payload, format="json")
        assert response.status_code == 201
        assert response.data["notes"] == "Con ajo y aceite."

    def test_unicidad_fecha_hora(self, api, meal):
        response = api.post(MEALS_BASE, {"date": "2026-05-19", "meal_time": "lunch", "name": "Pizza"}, format="json")
        assert response.status_code == 400

    def test_name_requerido(self, api):
        response = api.post(MEALS_BASE, {"date": "2026-05-20", "meal_time": "lunch"}, format="json")
        assert response.status_code == 400

    def test_date_requerido(self, api):
        response = api.post(MEALS_BASE, {"meal_time": "lunch", "name": "Test"}, format="json")
        assert response.status_code == 400

    def test_meal_time_invalido(self, api):
        response = api.post(MEALS_BASE, {"date": "2026-05-20", "meal_time": "brunch", "name": "Test"}, format="json")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Actualización y eliminación
# ---------------------------------------------------------------------------

class TestMealPlanUpdate:
    def test_actualiza_nombre(self, api, meal):
        response = api.patch(f"{MEALS_BASE}{meal.id}/", {"name": "Pizza margherita"}, format="json")
        assert response.status_code == 200
        assert response.data["name"] == "Pizza margherita"

    def test_actualiza_notas(self, api, meal):
        response = api.patch(f"{MEALS_BASE}{meal.id}/", {"notes": "Sin sal."}, format="json")
        assert response.status_code == 200
        assert response.data["notes"] == "Sin sal."

    def test_elimina_comida(self, api, meal):
        response = api.delete(f"{MEALS_BASE}{meal.id}/")
        assert response.status_code == 204
        assert not MealPlan.objects.filter(id=meal.id).exists()

    def test_detalle_comida(self, api, meal):
        response = api.get(f"{MEALS_BASE}{meal.id}/")
        assert response.status_code == 200
        assert response.data["meal_time"] == "lunch"

    def test_not_found(self, api):
        response = api.get(f"{MEALS_BASE}9999/")
        assert response.status_code == 404
