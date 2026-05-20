from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet,
    HouseholdInsightsView,
    MealPlanViewSet,
    RecurringTaskViewSet,
    TaskOccurrenceListView,
    TaskOccurrenceViewSet,
)


router = DefaultRouter()
router.register(r"recurring-tasks", RecurringTaskViewSet, basename="recurring-task")
router.register(r"documents", DocumentViewSet, basename="document")
router.register(r"meal-plans", MealPlanViewSet, basename="meal-plan")

urlpatterns = [
    path("task-occurrences/", TaskOccurrenceListView.as_view(), name="task-occurrence-list"),
    path("household-insights/", HouseholdInsightsView.as_view(), name="household-insights"),
    path(
        "task-occurrences/<int:pk>/complete/",
        TaskOccurrenceViewSet.as_view({"post": "complete"}),
        name="task-occurrence-complete",
    ),
    path(
        "task-occurrences/<int:pk>/skip/",
        TaskOccurrenceViewSet.as_view({"post": "skip"}),
        name="task-occurrence-skip",
    ),
    path(
        "task-occurrences/<int:pk>/reopen/",
        TaskOccurrenceViewSet.as_view({"post": "reopen"}),
        name="task-occurrence-reopen",
    ),
    *router.urls,
]