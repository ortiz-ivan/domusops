from rest_framework import serializers

from .models import FinancialEvent, MonthlyClose


class CategoryBudgetItemSerializer(serializers.Serializer):
    category = serializers.CharField()
    label = serializers.CharField()
    budget_bucket = serializers.CharField()
    budget = serializers.FloatField(allow_null=True)
    actual = serializers.FloatField()
    remaining = serializers.FloatField(allow_null=True)
    variable_expense_total = serializers.FloatField()
    committed_variable_total = serializers.FloatField()
    fixed_payment_total = serializers.FloatField()
    product_restock_total = serializers.FloatField()


class BudgetBucketSummarySerializer(serializers.Serializer):
    needs = serializers.FloatField()
    wants = serializers.FloatField()
    savings = serializers.FloatField()


class BudgetRuleSummarySerializer(serializers.Serializer):
    targets = BudgetBucketSummarySerializer()
    actuals = BudgetBucketSummarySerializer()
    variance = BudgetBucketSummarySerializer()


class MonthlyCloseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyClose
        fields = ["id", "month", "year", "notes", "summary_snapshot", "created_at"]
        read_only_fields = ["id", "summary_snapshot", "created_at"]


class FinancialEventSerializer(serializers.ModelSerializer):
    entity_label = serializers.CharField(source="get_entity_type_display", read_only=True)
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = FinancialEvent
        fields = [
            "id",
            "entity_type",
            "entity_label",
            "action",
            "action_label",
            "entity_id",
            "title",
            "amount",
            "effective_date",
            "month",
            "year",
            "reason",
            "previous_data",
            "current_data",
            "metadata",
            "created_at",
        ]


class ProjectionAlertSerializer(serializers.Serializer):
    level = serializers.CharField()
    code = serializers.CharField()
    message = serializers.CharField()


class MonthlyProjectionSerializer(serializers.Serializer):
    is_current_month = serializers.BooleanField()
    days_elapsed = serializers.IntegerField()
    days_total = serializers.IntegerField()
    actual_spend_so_far = serializers.FloatField()
    daily_rate = serializers.FloatField(allow_null=True)
    projected_month_end = serializers.FloatField(allow_null=True)
    projected_remaining = serializers.FloatField(allow_null=True)
    projected_expense_pct = serializers.FloatField(allow_null=True)
    alerts = ProjectionAlertSerializer(many=True)


class FinancialAnomalySerializer(serializers.Serializer):
    type = serializers.CharField()
    level = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    category_label = serializers.CharField(allow_null=True)
    current_amount = serializers.FloatField(allow_null=True)
    reference_amount = serializers.FloatField(allow_null=True)
    deviation_pct = serializers.FloatField()
    product_id = serializers.IntegerField(allow_null=True)
    product_name = serializers.CharField(allow_null=True)
    days_since_last_restock = serializers.IntegerField(allow_null=True)
    avg_restock_interval_days = serializers.FloatField(allow_null=True)


class FinancialAnomaliesReportSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    lookback_months = serializers.IntegerField()
    anomalies = FinancialAnomalySerializer(many=True)


class MonthlyFinanceSummarySerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    total_income = serializers.FloatField()
    home_estimated_expenses = serializers.FloatField()
    fixed_estimated_expenses = serializers.FloatField()
    variable_expenses = serializers.FloatField()
    paid_expenses = serializers.FloatField()
    committed_expenses = serializers.FloatField()
    committed_fixed_expenses = serializers.FloatField()
    paid_variable_expenses = serializers.FloatField()
    committed_variable_expenses = serializers.FloatField()
    estimated_expenses = serializers.FloatField()
    expense_percentage = serializers.FloatField(allow_null=True)
    remaining_balance = serializers.FloatField()
    rule_50_30_20 = BudgetRuleSummarySerializer()
    category_breakdown = CategoryBudgetItemSerializer(many=True)
    monthly_close = MonthlyCloseSerializer(allow_null=True)
    projection = MonthlyProjectionSerializer()


class DashboardCriticalProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    category = serializers.CharField()
    stock = serializers.FloatField()
    stock_min = serializers.FloatField()
    unit = serializers.CharField()


class DashboardTaskSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    due_date = serializers.DateField()
    priority = serializers.CharField()
    category = serializers.CharField()


class DashboardGoalSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    goal_type = serializers.CharField()
    target_amount = serializers.FloatField()
    current_amount = serializers.FloatField()
    progress_pct = serializers.FloatField()
    days_left = serializers.IntegerField(allow_null=True)


class DashboardSummarySerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    finance_summary = MonthlyFinanceSummarySerializer()
    critical_products = DashboardCriticalProductSerializer(many=True)
    overdue_tasks = DashboardTaskSerializer(many=True)
    upcoming_tasks = DashboardTaskSerializer(many=True)
    lagging_goals = DashboardGoalSerializer(many=True)
    anomalies = FinancialAnomalySerializer(many=True)
    anomalies_lookback_months = serializers.IntegerField()