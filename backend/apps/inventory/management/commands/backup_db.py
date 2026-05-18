import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# Rutas comunes de pg_dump en Windows cuando no está en el PATH.
_PG_DUMP_WINDOWS = [
    Path(r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"),
    Path(r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"),
    Path(r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"),
    Path(r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe"),
]


def _find_pg_dump():
    found = shutil.which("pg_dump")
    if found:
        return found
    for path in _PG_DUMP_WINDOWS:
        if path.exists():
            return str(path)
    return None


def _default_backup_dir():
    return settings.BASE_DIR.parent / "backups"


class Command(BaseCommand):
    help = "Crea un backup de la base de datos PostgreSQL con pg_dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=None,
            help="Directorio donde guardar el backup (por defecto: <proyecto>/backups/).",
        )
        parser.add_argument(
            "--keep",
            type=int,
            default=None,
            metavar="N",
            help="Conserva solo los N backups más recientes; elimina los anteriores.",
        )
        parser.add_argument(
            "--listar",
            action="store_true",
            help="Muestra los backups existentes y sale.",
        )

    def handle(self, *args, **options):
        backup_dir = Path(options["output_dir"] or _default_backup_dir())
        backup_dir.mkdir(parents=True, exist_ok=True)

        if options["listar"]:
            self._listar(backup_dir)
            return

        pg_dump = _find_pg_dump()
        if not pg_dump:
            raise CommandError(
                "pg_dump no encontrado en el PATH ni en rutas estándar de Windows.\n"
                "Instala PostgreSQL client tools o añade su directorio bin al PATH.\n"
                "Alternativa: usa 'python manage.py exportar_datos' para backup en JSON."
            )

        db = settings.DATABASES["default"]
        db_name = db.get("NAME", "homemanager")
        ts = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = backup_dir / f"{db_name}_{ts}.dump"

        env = os.environ.copy()
        password = db.get("PASSWORD", "")
        if password:
            env["PGPASSWORD"] = password

        cmd = [
            pg_dump,
            "--format=custom",   # Comprimido; restaurable con pg_restore
            "--host",   db.get("HOST", "localhost"),
            "--port",   str(db.get("PORT", "5432")),
            "--username", db.get("USER", "postgres"),
            "--dbname", db_name,
            "--file",   str(filename),
        ]

        self.stdout.write(f"Ejecutando pg_dump → {filename.name} ...")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            raise CommandError(f"pg_dump falló (código {result.returncode}):\n{result.stderr.strip()}")

        if not filename.exists():
            raise CommandError("pg_dump finalizó sin error pero no creó el archivo.")

        size_kb = filename.stat().st_size // 1024
        self.stdout.write(self.style.SUCCESS(f"\nBackup creado: {filename}  ({size_kb} KB)"))
        self.stdout.write(f"Restaurar con:  pg_restore -d {db_name} {filename}")

        if options["keep"] is not None:
            self._rotar(backup_dir, db_name, options["keep"])

    # ------------------------------------------------------------------

    def _listar(self, backup_dir):
        dumps = sorted(backup_dir.glob("*.dump"), reverse=True)
        if not dumps:
            self.stdout.write(f"No hay backups en {backup_dir}")
            return
        self.stdout.write(f"Backups en {backup_dir}:")
        for f in dumps:
            size_kb = f.stat().st_size // 1024
            self.stdout.write(f"  {f.name}  ({size_kb} KB)")

    def _rotar(self, backup_dir, db_name, keep):
        dumps = sorted(backup_dir.glob(f"{db_name}_*.dump"), reverse=True)
        to_delete = dumps[keep:]
        for f in to_delete:
            f.unlink()
            self.stdout.write(f"  Eliminado (rotación): {f.name}")
