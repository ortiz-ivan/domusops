from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FinancialEvent, MonthlyClose
from .serializers import (
    DashboardSummarySerializer,
    FinancialAnomaliesReportSerializer,
    FinancialEventSerializer,
    MonthlyCloseSerializer,
    MonthlyFinanceSummarySerializer,
)
from .services import (
    calculate_monthly_finance_summary,
    create_monthly_close,
    detect_financial_anomalies,
    get_active_financial_period,
    get_dashboard_summary,
)


def resolve_month_year(query_params):
    default_month, default_year = get_active_financial_period()

    try:
        month = int(query_params.get("month", default_month))
        year = int(query_params.get("year", default_year))
    except ValueError:
        raise ValueError("Mes y anio deben ser valores numericos")

    if month < 1 or month > 12:
        raise ValueError("El mes debe estar entre 1 y 12")

    return month, year


class MonthlyFinanceSummaryView(APIView):
    serializer_class = MonthlyFinanceSummarySerializer

    def get(self, request):
        try:
            month, year = resolve_month_year(request.query_params)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = calculate_monthly_finance_summary(month, year)
        serializer = MonthlyFinanceSummarySerializer(payload)
        return Response(serializer.data)


class FinancialEventListView(APIView):
    serializer_class = FinancialEventSerializer
    pagination_class = None

    def get(self, request):
        try:
            month, year = resolve_month_year(request.query_params)
            limit = int(request.query_params.get("limit", 25))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        events = FinancialEvent.objects.filter(month=month, year=year)[: max(1, min(limit, 100))]
        serializer = FinancialEventSerializer(events, many=True)
        return Response(serializer.data)


class MonthlyCloseView(APIView):
    serializer_class = MonthlyCloseSerializer
    pagination_class = None

    def get(self, request):
        closes = MonthlyClose.objects.all()
        serializer = MonthlyCloseSerializer(closes, many=True)
        return Response(serializer.data)

    def post(self, request):
        today = timezone.localdate()

        try:
            month = int(request.data.get("month", today.month))
            year = int(request.data.get("year", today.year))
        except (TypeError, ValueError):
            return Response({"detail": "Mes y anio deben ser numericos"}, status=status.HTTP_400_BAD_REQUEST)

        notes = str(request.data.get("notes", "")).strip()

        try:
            monthly_close = create_monthly_close(month, year, notes)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MonthlyCloseSerializer(monthly_close)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FinancialAnomaliesView(APIView):
    serializer_class = FinancialAnomaliesReportSerializer

    def get(self, request):
        try:
            month, year = resolve_month_year(request.query_params)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        data = detect_financial_anomalies(month, year)
        return Response(FinancialAnomaliesReportSerializer(data).data)


class DashboardSummaryView(APIView):
    serializer_class = DashboardSummarySerializer

    def get(self, request):
        data = get_dashboard_summary()
        return Response(DashboardSummarySerializer(data).data)