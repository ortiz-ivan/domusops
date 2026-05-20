from rest_framework import serializers

from apps.configuration.models import InventorySettings
from apps.configuration.serializers import validate_household_option

from .models import Document, MealPlan, RecurringTask, TaskOccurrence
from .services import build_task_linked_context


class RecurringTaskSerializer(serializers.ModelSerializer):
    linked_context = serializers.SerializerMethodField()

    class Meta:
        model = RecurringTask
        fields = [
            "id",
            "title",
            "category",
            "area",
            "priority",
            "estimated_minutes",
            "integration_kind",
            "linked_fixed_expense",
            "linked_product",
            "linked_context",
            "frequency_type",
            "interval",
            "weekday",
            "day_of_month",
            "start_date",
            "next_due_date",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "next_due_date", "created_at", "updated_at"]

    def validate(self, attrs):
        settings_data = InventorySettings.get_solo().get_config()
        frequency_type = attrs.get("frequency_type")
        if frequency_type is None and self.instance is not None:
            frequency_type = self.instance.frequency_type

        interval = attrs.get("interval")
        if interval is None and self.instance is not None:
            interval = self.instance.interval

        weekday = attrs.get("weekday")
        if weekday is None and self.instance is not None:
            weekday = self.instance.weekday

        day_of_month = attrs.get("day_of_month")
        if day_of_month is None and self.instance is not None:
            day_of_month = self.instance.day_of_month

        if interval is not None and interval < 1:
            raise serializers.ValidationError({"interval": "El intervalo debe ser mayor o igual a 1."})

        estimated_minutes = attrs.get("estimated_minutes")
        if estimated_minutes is None and self.instance is not None:
            estimated_minutes = self.instance.estimated_minutes
        if estimated_minutes is not None and int(estimated_minutes) < 0:
            raise serializers.ValidationError({"estimated_minutes": "El tiempo estimado no puede ser negativo."})

        integration_kind = attrs.get("integration_kind")
        if integration_kind is None and self.instance is not None:
            integration_kind = self.instance.integration_kind
        integration_kind = integration_kind or RecurringTask.INTEGRATION_NONE

        linked_fixed_expense = attrs.get("linked_fixed_expense")
        if linked_fixed_expense is None and self.instance is not None:
            linked_fixed_expense = self.instance.linked_fixed_expense

        linked_product = attrs.get("linked_product")
        if linked_product is None and self.instance is not None:
            linked_product = self.instance.linked_product

        if integration_kind == RecurringTask.INTEGRATION_NONE:
            attrs["linked_fixed_expense"] = None
            attrs["linked_product"] = None
        elif integration_kind == RecurringTask.INTEGRATION_FIXED_EXPENSE:
            if linked_fixed_expense is None:
                raise serializers.ValidationError({"linked_fixed_expense": "Debes seleccionar un gasto fijo para esta integracion."})
            attrs["linked_product"] = None
        elif integration_kind in {RecurringTask.INTEGRATION_PRODUCT_RESTOCK, RecurringTask.INTEGRATION_PRODUCT_EXPIRY}:
            if linked_product is None:
                raise serializers.ValidationError({"linked_product": "Debes seleccionar un producto para esta integracion."})
            attrs["linked_fixed_expense"] = None
        else:
            raise serializers.ValidationError({"integration_kind": "Tipo de integracion no soportado."})

        validate_household_option(settings_data, attrs, "category", "household_task_categories", self.instance)
        validate_household_option(settings_data, attrs, "area", "household_task_areas", self.instance)
        validate_household_option(settings_data, attrs, "priority", "household_task_priorities", self.instance)

        if frequency_type == RecurringTask.FREQUENCY_DAILY:
            attrs["weekday"] = None
            attrs["day_of_month"] = None
            return attrs

        if frequency_type == RecurringTask.FREQUENCY_WEEKLY:
            if weekday is None:
                raise serializers.ValidationError({"weekday": "Debes indicar el dia de la semana para tareas semanales."})
            if not 0 <= int(weekday) <= 6:
                raise serializers.ValidationError({"weekday": "El dia de la semana debe estar entre 0 y 6."})
            attrs["day_of_month"] = None

        if frequency_type == RecurringTask.FREQUENCY_MONTHLY:
            if day_of_month is None:
                raise serializers.ValidationError({"day_of_month": "Debes indicar el dia del mes para tareas mensuales."})
            if not 1 <= int(day_of_month) <= 31:
                raise serializers.ValidationError({"day_of_month": "El dia del mes debe estar entre 1 y 31."})
            attrs["weekday"] = None

        return attrs

    def get_linked_context(self, obj):
        return build_task_linked_context(obj)


class TaskOccurrenceSerializer(serializers.ModelSerializer):
    recurring_task_title = serializers.CharField(source="recurring_task.title", read_only=True)
    recurring_task_category = serializers.CharField(source="recurring_task.category", read_only=True)
    recurring_task_area = serializers.CharField(source="recurring_task.area", read_only=True)
    recurring_task_priority = serializers.CharField(source="recurring_task.priority", read_only=True)
    frequency_type = serializers.CharField(source="recurring_task.frequency_type", read_only=True)
    interval = serializers.IntegerField(source="recurring_task.interval", read_only=True)
    weekday = serializers.IntegerField(source="recurring_task.weekday", read_only=True)
    day_of_month = serializers.IntegerField(source="recurring_task.day_of_month", read_only=True)
    estimated_minutes = serializers.IntegerField(source="recurring_task.estimated_minutes", read_only=True)
    integration_kind = serializers.CharField(source="recurring_task.integration_kind", read_only=True)
    linked_fixed_expense = serializers.IntegerField(source="recurring_task.linked_fixed_expense_id", read_only=True)
    linked_product = serializers.IntegerField(source="recurring_task.linked_product_id", read_only=True)
    linked_context = serializers.SerializerMethodField()

    class Meta:
        model = TaskOccurrence
        fields = [
            "id",
            "recurring_task",
            "recurring_task_title",
            "recurring_task_category",
            "recurring_task_area",
            "recurring_task_priority",
            "frequency_type",
            "interval",
            "weekday",
            "day_of_month",
            "estimated_minutes",
            "integration_kind",
            "linked_fixed_expense",
            "linked_product",
            "linked_context",
            "due_date",
            "status",
            "completed_at",
            "completion_notes",
            "created_at",
        ]

    def get_linked_context(self, obj):
        return build_task_linked_context(obj.recurring_task)


class WeeklyCompliancePointSerializer(serializers.Serializer):
    week_start = serializers.DateField()
    week_end = serializers.DateField()
    total_due = serializers.IntegerField()
    completed = serializers.IntegerField()
    skipped = serializers.IntegerField()
    overdue_open = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    estimated_minutes = serializers.IntegerField()


class TaskComplianceItemSerializer(serializers.Serializer):
    recurring_task_id = serializers.IntegerField()
    title = serializers.CharField()
    category = serializers.CharField()
    area = serializers.CharField()
    priority = serializers.CharField()
    estimated_minutes = serializers.IntegerField()
    integration_kind = serializers.CharField(allow_blank=True)
    linked_context = serializers.JSONField(allow_null=True)
    overdue_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()
    late_completion_count = serializers.IntegerField()
    postponement_score = serializers.IntegerField()


class HouseholdInsightsSerializer(serializers.Serializer):
    window_start = serializers.DateField()
    window_end = serializers.DateField()
    weekly_completion = WeeklyCompliancePointSerializer(many=True)
    most_postponed_tasks = TaskComplianceItemSerializer(many=True)
    recurring_overdue_tasks = TaskComplianceItemSerializer(many=True)
    weekly_estimated_minutes = serializers.IntegerField()
    overdue_tasks_count = serializers.IntegerField()


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "doc_type",
            "content",
            "url",
            "entity_type",
            "entity_id",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = ["id", "date", "meal_time", "name", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]