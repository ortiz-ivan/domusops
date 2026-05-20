from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import RecurringTaskFilter, TaskOccurrenceFilter
from .models import Document, MealPlan, RecurringTask, TaskOccurrence
from .serializers import (
    DocumentSerializer,
    HouseholdInsightsSerializer,
    MealPlanSerializer,
    RecurringTaskSerializer,
    TaskOccurrenceSerializer,
)
from .services import (
    build_household_insights,
    complete_task_occurrence,
    create_recurring_task_record,
    ensure_occurrences_for_range,
    reopen_task_occurrence,
    skip_task_occurrence,
    update_recurring_task_record,
)


def parse_date_param(raw_value, fallback, field_name):
    if not raw_value:
        return fallback

    try:
        return timezone.datetime.fromisoformat(raw_value).date()
    except ValueError as exc:
        raise ValueError(f"La fecha '{field_name}' debe tener formato YYYY-MM-DD.") from exc


def _household_filters_from_params(query_params):
    return {
        "category": query_params.get("category") or "",
        "area": query_params.get("area") or "",
        "priority": query_params.get("priority") or "",
    }


class RecurringTaskViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringTaskSerializer
    filterset_class = RecurringTaskFilter

    def get_queryset(self):
        return (
            RecurringTask.objects
            .select_related("linked_fixed_expense", "linked_product")
            .all()
            .order_by("title", "id")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = create_recurring_task_record(serializer.validated_data)
        output_serializer = self.get_serializer(instance)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = update_recurring_task_record(instance, serializer.validated_data)
        return Response(self.get_serializer(updated_instance).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class TaskOccurrenceListView(generics.ListAPIView):
    serializer_class = TaskOccurrenceSerializer
    filterset_class = TaskOccurrenceFilter

    def get_queryset(self):
        today = timezone.localdate()

        try:
            date_from = parse_date_param(self.request.query_params.get("from"), today, "from")
            date_to = parse_date_param(self.request.query_params.get("to"), today + timedelta(days=30), "to")
            ensure_occurrences_for_range(date_from, date_to)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})

        return TaskOccurrence.objects.select_related(
            "recurring_task",
            "recurring_task__linked_fixed_expense",
            "recurring_task__linked_product",
        ).filter(
            recurring_task__is_active=True,
            due_date__gte=date_from,
            due_date__lte=date_to,
        ).order_by("due_date", "id")


class HouseholdInsightsView(generics.GenericAPIView):
    serializer_class = HouseholdInsightsSerializer
    pagination_class = None

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        try:
            date_from = parse_date_param(request.query_params.get("from"), today - timedelta(days=55), "from")
            date_to = parse_date_param(request.query_params.get("to"), today + timedelta(days=7), "to")
            payload = build_household_insights(date_from, date_to, _household_filters_from_params(request.query_params))
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        serializer = self.get_serializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TaskOccurrenceViewSet(viewsets.GenericViewSet):
    queryset = TaskOccurrence.objects.select_related(
        "recurring_task",
        "recurring_task__linked_fixed_expense",
        "recurring_task__linked_product",
    ).all()
    serializer_class = TaskOccurrenceSerializer

    def _notes_from_request(self, request):
        notes = request.data.get("completion_notes", "")
        if isinstance(notes, list):
            notes = notes[0] if notes else ""
        return str(notes or "").strip()

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        try:
            occurrence = complete_task_occurrence(self.get_object(), self._notes_from_request(request))
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(self.get_serializer(occurrence).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def skip(self, request, pk=None):
        try:
            occurrence = skip_task_occurrence(self.get_object(), self._notes_from_request(request))
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(self.get_serializer(occurrence).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        try:
            occurrence = reopen_task_occurrence(self.get_object())
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(self.get_serializer(occurrence).data, status=status.HTTP_200_OK)


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    filterset_fields = ["doc_type", "entity_type"]

    def get_queryset(self):
        return Document.objects.all()


class MealPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanSerializer

    def get_queryset(self):
        qs = MealPlan.objects.all()
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        return qs