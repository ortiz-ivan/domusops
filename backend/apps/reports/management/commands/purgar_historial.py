from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.utils import timezone

from apps.reports.models import FinancialEvent, MonthlyClose


def _subtract_months(year, month, n):
    """Resta n meses a (year, month) y retorna (year, month) resultante."""
    month -= n % 12
    year -= n // 12
    if month <= 0:
        month += 12
        year -= 1
    return year, month


class Command(BaseCommand):
    help = (
        "Purga eventos de auditoría (FinancialEvent) más antiguos que N meses.\n"
        "Los datos originales (ingresos, gastos, pagos) no se modifican.\n"
        "Los cierres mensuales (MonthlyClose) nunca se tocan."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--meses",
            type=int,
            default=24,
            metavar="N",
            help="Meses de historial a conservar (por defecto: 24).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué se eliminaría sin realizar cambios.",
        )

    def handle(self, *args, **options):
        retention = options["meses"]
        dry = options["dry_run"]

        if retention < 1:
            raise CommandError("--meses debe ser al menos 1.")

        today = timezone.localdate()
        cutoff_year, cutoff_month = _subtract_months(today.year, today.month, retention)

        to_purge = FinancialEvent.objects.filter(
            Q(year__lt=cutoff_year) | Q(year=cutoff_year, month__lt=cutoff_month)
        )

        total = to_purge.count()
        if total == 0:
            self.stdout.write("No hay eventos para purgar (todos dentro del período de retención).")
            return

        self._warn_missing_closes(to_purge)
        self._print_breakdown(to_purge, total, cutoff_year, cutoff_month, dry)

        if dry:
            self.stdout.write(self.style.WARNING("\nDry run: no se eliminó nada."))
            return

        deleted, _ = to_purge.delete()
        self.stdout.write(self.style.SUCCESS(f"\n{deleted} eventos eliminados correctamente."))

    # ------------------------------------------------------------------

    def _warn_missing_closes(self, queryset):
        months_without_close = []
        for year, month in queryset.values_list("year", "month").distinct().order_by("year", "month"):
            if not MonthlyClose.objects.filter(year=year, month=month).exists():
                months_without_close.append(f"{month:02d}/{year}")
        if months_without_close:
            self.stdout.write(
                self.style.WARNING(
                    "Advertencia: los siguientes meses no tienen cierre registrado:\n"
                    f"  {', '.join(months_without_close)}\n"
                    "  Los datos originales (ingresos, gastos) se conservan en sus tablas."
                )
            )

    def _print_breakdown(self, queryset, total, cutoff_year, cutoff_month, dry):
        prefix = "[DRY RUN] " if dry else ""
        self.stdout.write(
            f"\n{prefix}Eventos a purgar: {total}  "
            f"(anteriores a {cutoff_month:02d}/{cutoff_year})"
        )
        breakdown = (
            queryset
            .values("entity_type", "action")
            .annotate(n=Count("id"))
            .order_by("entity_type", "action")
        )
        for row in breakdown:
            self.stdout.write(f"  {row['entity_type']:<25}  {row['action']:<20}  {row['n']:>5}")
