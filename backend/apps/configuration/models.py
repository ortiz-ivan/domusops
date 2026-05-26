from copy import deepcopy

from django.db import models


DEFAULT_INVENTORY_SETTINGS = {
    "categories": [
        {
            "value": "food",
            "label": "Alimentos",
            "scope": "inventory",
            "type": "consumable",
            "budget_bucket": "needs",
            "fallback_unit_cost": 4.8,
            "monthly_budget": None,
        },
        {
            "value": "cleaning",
            "label": "Limpieza",
            "scope": "inventory",
            "type": "consumable",
            "budget_bucket": "needs",
            "fallback_unit_cost": 6.2,
            "monthly_budget": None,
        },
        {
            "value": "hygiene",
            "label": "Higiene",
            "scope": "inventory",
            "type": "consumable",
            "budget_bucket": "needs",
            "fallback_unit_cost": 5.1,
            "monthly_budget": None,
        },
        {
            "value": "assets",
            "label": "Activos",
            "scope": "inventory",
            "type": "asset",
            "budget_bucket": "needs",
            "fallback_unit_cost": 11.6,
            "monthly_budget": None,
        },
        {
            "value": "home",
            "label": "Hogar",
            "scope": "fixed_expense",
            "type": "service",
            "budget_bucket": "needs",
            "fallback_unit_cost": 7.4,
            "monthly_budget": None,
        },
        {
            "value": "services",
            "label": "Servicios",
            "scope": "fixed_expense",
            "type": "service",
            "budget_bucket": "needs",
            "fallback_unit_cost": 12,
            "monthly_budget": None,
        },
        {
            "value": "subscription",
            "label": "Suscripciones",
            "scope": "fixed_expense",
            "type": "subscription",
            "budget_bucket": "wants",
            "fallback_unit_cost": 9.5,
            "monthly_budget": None,
        },
        {
            "value": "mobility",
            "label": "Movilidad",
            "scope": "variable_expense",
            "type": "service",
            "budget_bucket": "needs",
            "fallback_unit_cost": 8.1,
            "monthly_budget": None,
        },
        {
            "value": "maintenance",
            "label": "Mantenimiento",
            "scope": "variable_expense",
            "type": "service",
            "budget_bucket": "needs",
            "fallback_unit_cost": 10.5,
            "monthly_budget": None,
        },
        {
            "value": "leisure",
            "label": "Ocio",
            "scope": "variable_expense",
            "type": "service",
            "budget_bucket": "wants",
            "fallback_unit_cost": 7.9,
            "monthly_budget": None,
        },
    ],
    "units": [
        {"value": "unidad", "label": "Unidad"},
        {"value": "kg", "label": "Kilogramo"},
        {"value": "g", "label": "Gramo"},
        {"value": "l", "label": "Litro"},
        {"value": "ml", "label": "Mililitro"},
        {"value": "paquete", "label": "Paquete"},
        {"value": "caja", "label": "Caja"},
        {"value": "botella", "label": "Botella"},
    ],
    "budget_buckets": [
        {"value": "needs", "label": "Necesidades", "target_ratio": 0.5},
        {"value": "wants", "label": "Deseos", "target_ratio": 0.3},
        {"value": "savings", "label": "Ahorro / deuda", "target_ratio": 0.2},
    ],
    "usage_frequency_weights": {
        "high": 1.5,
        "medium": 1,
        "low": 0.65,
    },
    "thresholds": {
        "default_stock_min": 1,
        "low_stock_ratio": 1,
        "critical_stock_ratio": 1,
        "purchase_suggestion_stock_ratio": 1,
    },
    "currency": {
        "code": "PYG",
        "locale": "es-PY",
        "maximum_fraction_digits": 0,
    },
    "monthly_close_day": 25,
    "alerts": {
        "expiring_soon_days": 14,
        "purchase_stale_days": 21,
        "critical_frequencies": ["high"],
    },
    "household_task_categories": [
        {"value": "cleaning", "label": "Limpieza"},
        {"value": "maintenance", "label": "Mantenimiento"},
        {"value": "payments", "label": "Pagos y vencimientos"},
        {"value": "shopping", "label": "Compras"},
        {"value": "routine", "label": "Rutina general"},
    ],
    "household_task_areas": [
        {"value": "kitchen", "label": "Cocina"},
        {"value": "bathroom", "label": "Baño"},
        {"value": "laundry", "label": "Lavanderia"},
        {"value": "bedroom", "label": "Dormitorio"},
        {"value": "living_room", "label": "Sala / espacios comunes"},
        {"value": "home_admin", "label": "Administracion del hogar"},
    ],
    "household_task_priorities": [
        {"value": "low", "label": "Baja"},
        {"value": "medium", "label": "Media"},
        {"value": "high", "label": "Alta"},
        {"value": "critical", "label": "Critica"},
    ],
}


def clone_default_inventory_settings():
    return deepcopy(DEFAULT_INVENTORY_SETTINGS)


def merge_inventory_settings(config):
    merged = clone_default_inventory_settings()
    source = config or {}

    for key, default_value in merged.items():
        if key not in source:
            continue

        incoming_value = source[key]
        if isinstance(default_value, dict) and isinstance(incoming_value, dict):
            merged[key] = {
                **default_value,
                **incoming_value,
            }
        else:
            merged[key] = incoming_value

    return merged


def get_category_settings(settings_data, category):
    for item in settings_data.get("categories", []):
        if item.get("value") == category:
            return item
    return None


def get_scope_categories(settings_data, scope):
    return [
        item for item in settings_data.get("categories", [])
        if item.get("scope") == scope
    ]


def get_category_type(settings_data, category, fallback="consumable"):
    category_settings = get_category_settings(settings_data, category)
    return (category_settings or {}).get("type") or fallback


def get_category_budget_bucket(settings_data, category, fallback="needs"):
    category_settings = get_category_settings(settings_data, category)
    return (category_settings or {}).get("budget_bucket") or fallback


def get_category_fallback_unit_cost(settings_data, category, fallback=4):
    category_settings = get_category_settings(settings_data, category)
    value = (category_settings or {}).get("fallback_unit_cost")
    return float(value if value is not None else fallback)


def get_category_monthly_budget(settings_data, category):
    category_settings = get_category_settings(settings_data, category)
    value = (category_settings or {}).get("monthly_budget")
    if value is None:
        return None
    try:
        v = float(value)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def get_budget_bucket_ratio_map(settings_data):
    buckets = settings_data.get("budget_buckets", [])
    return {
        item.get("value"): float(item.get("target_ratio") or 0)
        for item in buckets
        if item.get("value")
    }


def get_budget_bucket_values(settings_data):
    return [
        item.get("value")
        for item in settings_data.get("budget_buckets", [])
        if item.get("value")
    ]


def get_household_option_values(settings_data, key):
    return [
        item.get("value")
        for item in settings_data.get(key, [])
        if item.get("value")
    ]


class InventorySettings(models.Model):
    config = models.JSONField(default=clone_default_inventory_settings)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_inventorysettings"
        verbose_name = "Configuracion de inventario"
        verbose_name_plural = "Configuracion de inventario"

    @classmethod
    def get_solo(cls):
        instance, _ = cls.objects.get_or_create(pk=1, defaults={"config": clone_default_inventory_settings()})
        return instance

    def get_config(self):
        return merge_inventory_settings(self.config)

    def get_financial_config(self) -> dict:
        config = self.get_config()
        return {
            "budget_buckets": config["budget_buckets"],
            "currency": config["currency"],
            "monthly_close_day": config["monthly_close_day"],
        }

    def get_alert_config(self) -> dict:
        config = self.get_config()
        return {
            "alerts": config["alerts"],
            "thresholds": config["thresholds"],
        }

    def get_inventory_config(self) -> dict:
        config = self.get_config()
        return {
            "categories": config["categories"],
            "units": config["units"],
            "usage_frequency_weights": config["usage_frequency_weights"],
        }

    def __str__(self):
        return "Configuracion de inventario"