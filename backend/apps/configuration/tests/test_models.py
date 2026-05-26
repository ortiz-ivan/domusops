import pytest

from apps.configuration.models import (
    DEFAULT_INVENTORY_SETTINGS,
    InventorySettings,
    clone_default_inventory_settings,
    get_budget_bucket_ratio_map,
    get_category_budget_bucket,
    get_category_fallback_unit_cost,
    get_category_settings,
    get_category_type,
    merge_inventory_settings,
)


# ---------------------------------------------------------------------------
# InventorySettings singleton
# ---------------------------------------------------------------------------

class TestInventorySettingsSingleton:
    def test_get_solo_crea_con_pk_1(self, db):
        instance = InventorySettings.get_solo()
        assert instance.pk == 1

    def test_get_solo_no_duplica_el_registro(self, db):
        InventorySettings.get_solo()
        InventorySettings.get_solo()
        assert InventorySettings.objects.count() == 1

    def test_get_config_retorna_settings_mergeados(self, db):
        instance = InventorySettings.get_solo()
        config = instance.get_config()
        assert "categories" in config
        assert "budget_buckets" in config
        assert "usage_frequency_weights" in config

    def test_get_config_contiene_categorias_por_defecto(self, db):
        instance = InventorySettings.get_solo()
        config = instance.get_config()
        valores = [c["value"] for c in config["categories"]]
        assert "food" in valores
        assert "cleaning" in valores


class TestInventorySettingsDomainMethods:
    def test_get_financial_config_retorna_claves_correctas(self, db):
        instance = InventorySettings.get_solo()
        financial = instance.get_financial_config()
        assert set(financial.keys()) == {"budget_buckets", "currency", "monthly_close_day"}

    def test_get_financial_config_budget_buckets_es_lista(self, db):
        instance = InventorySettings.get_solo()
        financial = instance.get_financial_config()
        assert isinstance(financial["budget_buckets"], list)
        assert len(financial["budget_buckets"]) > 0

    def test_get_financial_config_currency_tiene_code(self, db):
        instance = InventorySettings.get_solo()
        financial = instance.get_financial_config()
        assert "code" in financial["currency"]

    def test_get_financial_config_monthly_close_day_es_entero(self, db):
        instance = InventorySettings.get_solo()
        financial = instance.get_financial_config()
        assert isinstance(financial["monthly_close_day"], int)

    def test_get_alert_config_retorna_claves_correctas(self, db):
        instance = InventorySettings.get_solo()
        alert = instance.get_alert_config()
        assert set(alert.keys()) == {"alerts", "thresholds"}

    def test_get_alert_config_alerts_tiene_expiring_soon_days(self, db):
        instance = InventorySettings.get_solo()
        alert = instance.get_alert_config()
        assert "expiring_soon_days" in alert["alerts"]

    def test_get_alert_config_thresholds_tiene_critical_stock_ratio(self, db):
        instance = InventorySettings.get_solo()
        alert = instance.get_alert_config()
        assert "critical_stock_ratio" in alert["thresholds"]

    def test_get_inventory_config_retorna_claves_correctas(self, db):
        instance = InventorySettings.get_solo()
        inventory = instance.get_inventory_config()
        assert set(inventory.keys()) == {"categories", "units", "usage_frequency_weights"}

    def test_get_inventory_config_categories_es_lista(self, db):
        instance = InventorySettings.get_solo()
        inventory = instance.get_inventory_config()
        assert isinstance(inventory["categories"], list)
        assert len(inventory["categories"]) > 0

    def test_get_inventory_config_units_es_lista(self, db):
        instance = InventorySettings.get_solo()
        inventory = instance.get_inventory_config()
        assert isinstance(inventory["units"], list)

    def test_get_inventory_config_usage_frequency_weights_tiene_high_medium_low(self, db):
        instance = InventorySettings.get_solo()
        inventory = instance.get_inventory_config()
        weights = inventory["usage_frequency_weights"]
        assert set(weights.keys()) >= {"high", "medium", "low"}

    def test_domain_methods_son_subconjunto_de_get_config(self, db):
        instance = InventorySettings.get_solo()
        full = instance.get_config()
        financial = instance.get_financial_config()
        alert = instance.get_alert_config()
        inventory = instance.get_inventory_config()
        assert financial["budget_buckets"] == full["budget_buckets"]
        assert alert["alerts"] == full["alerts"]
        assert inventory["categories"] == full["categories"]


# ---------------------------------------------------------------------------
# merge_inventory_settings
# ---------------------------------------------------------------------------

class TestMergeInventorySettings:
    def test_config_vacia_usa_defaults(self):
        merged = merge_inventory_settings({})
        assert "categories" in merged
        assert len(merged["categories"]) > 0

    def test_config_none_usa_defaults(self):
        merged = merge_inventory_settings(None)
        assert merged == DEFAULT_INVENTORY_SETTINGS

    def test_lista_se_reemplaza_completamente(self):
        override = {"categories": [{"value": "custom", "label": "Custom"}]}
        merged = merge_inventory_settings(override)
        assert len(merged["categories"]) == 1
        assert merged["categories"][0]["value"] == "custom"

    def test_dict_se_mergea_superficialmente(self):
        override = {"usage_frequency_weights": {"high": 2.0}}
        merged = merge_inventory_settings(override)
        assert merged["usage_frequency_weights"]["high"] == 2.0

    def test_no_modifica_defaults_originales(self):
        override = {"categories": []}
        merge_inventory_settings(override)
        assert len(DEFAULT_INVENTORY_SETTINGS["categories"]) > 0

    def test_clave_no_presente_no_altera_default(self):
        merged = merge_inventory_settings({"currency": {"code": "USD"}})
        assert merged["currency"]["code"] == "USD"
        assert "categories" in merged


# ---------------------------------------------------------------------------
# Helpers de categoría
# ---------------------------------------------------------------------------

class TestGetCategorySettings:
    def test_retorna_categoria_correcta(self):
        settings = clone_default_inventory_settings()
        result = get_category_settings(settings, "food")
        assert result is not None
        assert result["value"] == "food"
        assert result["label"] == "Alimentos"

    def test_retorna_none_para_categoria_desconocida(self):
        settings = clone_default_inventory_settings()
        assert get_category_settings(settings, "inexistente") is None


class TestGetCategoryType:
    def test_consumable_para_food(self):
        settings = clone_default_inventory_settings()
        assert get_category_type(settings, "food") == "consumable"

    def test_service_para_home(self):
        settings = clone_default_inventory_settings()
        assert get_category_type(settings, "home") == "service"

    def test_subscription_para_subscription(self):
        settings = clone_default_inventory_settings()
        assert get_category_type(settings, "subscription") == "subscription"

    def test_fallback_para_categoria_desconocida(self):
        settings = clone_default_inventory_settings()
        assert get_category_type(settings, "desconocida", "asset") == "asset"

    def test_fallback_por_defecto_es_consumable(self):
        settings = clone_default_inventory_settings()
        assert get_category_type(settings, "desconocida") == "consumable"


class TestGetCategoryBudgetBucket:
    def test_needs_para_food(self):
        settings = clone_default_inventory_settings()
        assert get_category_budget_bucket(settings, "food") == "needs"

    def test_wants_para_subscription(self):
        settings = clone_default_inventory_settings()
        assert get_category_budget_bucket(settings, "subscription") == "wants"

    def test_fallback_por_defecto_es_needs(self):
        settings = clone_default_inventory_settings()
        assert get_category_budget_bucket(settings, "desconocida") == "needs"

    def test_fallback_personalizable(self):
        settings = clone_default_inventory_settings()
        assert get_category_budget_bucket(settings, "desconocida", "savings") == "savings"


class TestGetCategoryFallbackUnitCost:
    def test_retorna_costo_correcto_para_food(self):
        settings = clone_default_inventory_settings()
        assert get_category_fallback_unit_cost(settings, "food") == pytest.approx(4.8)

    def test_retorna_costo_correcto_para_cleaning(self):
        settings = clone_default_inventory_settings()
        assert get_category_fallback_unit_cost(settings, "cleaning") == pytest.approx(6.2)

    def test_usa_fallback_para_categoria_desconocida(self):
        settings = clone_default_inventory_settings()
        assert get_category_fallback_unit_cost(settings, "desconocida", 99.9) == pytest.approx(99.9)

    def test_fallback_por_defecto_es_4(self):
        settings = clone_default_inventory_settings()
        assert get_category_fallback_unit_cost(settings, "desconocida") == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# Ratios de budget buckets
# ---------------------------------------------------------------------------

class TestGetBudgetBucketRatioMap:
    def test_ratios_correctos(self):
        settings = clone_default_inventory_settings()
        ratios = get_budget_bucket_ratio_map(settings)
        assert ratios["needs"] == pytest.approx(0.5)
        assert ratios["wants"] == pytest.approx(0.3)
        assert ratios["savings"] == pytest.approx(0.2)

    def test_ratios_suman_uno(self):
        settings = clone_default_inventory_settings()
        ratios = get_budget_bucket_ratio_map(settings)
        assert sum(ratios.values()) == pytest.approx(1.0)

    def test_retorna_los_tres_buckets(self):
        settings = clone_default_inventory_settings()
        ratios = get_budget_bucket_ratio_map(settings)
        assert set(ratios.keys()) == {"needs", "wants", "savings"}
