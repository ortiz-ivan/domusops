from django.urls import path

from .views import DashboardSummaryView, FinancialAnomaliesView, FinancialEventListView, MonthlyCloseView, MonthlyFinanceSummaryView


urlpatterns = [
    path("financial-events/", FinancialEventListView.as_view(), name="financial-event-list"),
    path("monthly-closes/", MonthlyCloseView.as_view(), name="monthly-close-list"),
    path("monthly-finance-summary/", MonthlyFinanceSummaryView.as_view(), name="monthly-finance-summary"),
    path("financial-anomalies/", FinancialAnomaliesView.as_view(), name="financial-anomalies"),
    path("dashboard-summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
]