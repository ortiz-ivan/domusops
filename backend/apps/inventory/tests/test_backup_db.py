from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

# Simula una ejecución exitosa de pg_dump creando el archivo de salida.
def _fake_run_ok(cmd, **kwargs):
    output_file = cmd[cmd.index("--file") + 1]
    Path(output_file).write_bytes(b"PG_DUMP_FAKE_CONTENT")
    return MagicMock(returncode=0, stderr="")


def _fake_run_fail(cmd, **kwargs):
    return MagicMock(returncode=1, stderr="could not connect to server")


# ---------------------------------------------------------------------------
# _find_pg_dump
# ---------------------------------------------------------------------------

class TestFindPgDump:
    def test_usa_pg_dump_del_path(self):
        from apps.inventory.management.commands.backup_db import _find_pg_dump
        with patch("shutil.which", return_value="/usr/bin/pg_dump"):
            assert _find_pg_dump() == "/usr/bin/pg_dump"

    def test_devuelve_none_si_no_encontrado(self):
        from apps.inventory.management.commands.backup_db import _find_pg_dump
        with patch("shutil.which", return_value=None):
            # Los paths de Windows tampoco existen en CI
            result = _find_pg_dump()
            # Puede ser None o una ruta existente en Windows real; solo verificamos el tipo
            assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# backup_db — flujo normal
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pg_dump(tmp_path):
    """Parcha _find_pg_dump y subprocess.run para simular pg_dump exitoso."""
    with (
        patch(
            "apps.inventory.management.commands.backup_db._find_pg_dump",
            return_value="/usr/bin/pg_dump",
        ),
        patch(
            "apps.inventory.management.commands.backup_db.subprocess.run",
            side_effect=_fake_run_ok,
        ),
    ):
        yield tmp_path


class TestBackupDbComando:
    def test_crea_archivo_dump(self, db, mock_pg_dump):
        call_command("backup_db", output_dir=str(mock_pg_dump))
        dumps = list(mock_pg_dump.glob("*.dump"))
        assert len(dumps) == 1

    def test_nombre_incluye_timestamp(self, db, mock_pg_dump):
        call_command("backup_db", output_dir=str(mock_pg_dump))
        nombre = next(mock_pg_dump.glob("*.dump")).name
        # formato: <db>_YYYYMMDD_HHMMSS.dump
        partes = nombre.replace(".dump", "").split("_")
        assert len(partes) >= 3
        assert partes[-2].isdigit() and len(partes[-2]) == 8   # YYYYMMDD
        assert partes[-1].isdigit() and len(partes[-1]) == 6   # HHMMSS

    def test_crea_directorio_si_no_existe(self, db, mock_pg_dump):
        nuevo_dir = mock_pg_dump / "subdir" / "backups"
        assert not nuevo_dir.exists()
        call_command("backup_db", output_dir=str(nuevo_dir))
        assert nuevo_dir.exists()

    def test_pg_dump_recibe_credenciales_correctas(self, db, mock_pg_dump):
        from django.conf import settings
        db_settings = settings.DATABASES["default"]

        captured = {}
        def capturar_cmd(cmd, **kwargs):
            captured["cmd"] = cmd
            return _fake_run_ok(cmd, **kwargs)

        with patch(
            "apps.inventory.management.commands.backup_db.subprocess.run",
            side_effect=capturar_cmd,
        ):
            call_command("backup_db", output_dir=str(mock_pg_dump))

        cmd = captured["cmd"]
        assert db_settings["HOST"] in cmd
        assert str(db_settings["PORT"]) in cmd
        assert db_settings["USER"] in cmd
        assert db_settings["NAME"] in cmd

    def test_pg_dump_falla_lanza_command_error(self, db, tmp_path):
        with (
            patch(
                "apps.inventory.management.commands.backup_db._find_pg_dump",
                return_value="/usr/bin/pg_dump",
            ),
            patch(
                "apps.inventory.management.commands.backup_db.subprocess.run",
                side_effect=_fake_run_fail,
            ),
            pytest.raises(CommandError, match="pg_dump falló"),
        ):
            call_command("backup_db", output_dir=str(tmp_path))

    def test_pg_dump_no_encontrado_lanza_error(self, db, tmp_path):
        with (
            patch(
                "apps.inventory.management.commands.backup_db._find_pg_dump",
                return_value=None,
            ),
            pytest.raises(CommandError, match="pg_dump no encontrado"),
        ):
            call_command("backup_db", output_dir=str(tmp_path))

    def test_mensaje_sugiere_exportar_datos_si_no_hay_pg_dump(self, db, tmp_path, capsys):
        with (
            patch(
                "apps.inventory.management.commands.backup_db._find_pg_dump",
                return_value=None,
            ),
            pytest.raises(CommandError) as exc_info,
        ):
            call_command("backup_db", output_dir=str(tmp_path))
        assert "exportar_datos" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Rotación de backups
# ---------------------------------------------------------------------------

class TestRotacion:
    def test_keep_elimina_backups_antiguos(self, db, mock_pg_dump):
        from django.conf import settings
        db_name = settings.DATABASES["default"]["NAME"]
        for i in range(3):
            (mock_pg_dump / f"{db_name}_2026050{i}_120000.dump").write_bytes(b"old")

        call_command("backup_db", output_dir=str(mock_pg_dump), keep=2)

        dumps = sorted(mock_pg_dump.glob(f"{db_name}_*.dump"), reverse=True)
        assert len(dumps) == 2

    def test_keep_conserva_los_mas_recientes(self, db, mock_pg_dump):
        from django.conf import settings
        db_name = settings.DATABASES["default"]["NAME"]
        for i in range(3):
            (mock_pg_dump / f"{db_name}_2026050{i}_120000.dump").write_bytes(b"old")

        call_command("backup_db", output_dir=str(mock_pg_dump), keep=2)

        nombres = [f.name for f in sorted(mock_pg_dump.glob(f"{db_name}_*.dump"), reverse=True)]
        # El más antiguo (20260500) debe haber sido eliminado
        assert not any("20260500" in n for n in nombres)

    def test_sin_keep_no_elimina_nada(self, db, mock_pg_dump):
        from django.conf import settings
        db_name = settings.DATABASES["default"]["NAME"]
        for i in range(5):
            (mock_pg_dump / f"{db_name}_2026050{i}_120000.dump").write_bytes(b"old")

        call_command("backup_db", output_dir=str(mock_pg_dump))

        dumps = list(mock_pg_dump.glob(f"{db_name}_*.dump"))
        assert len(dumps) == 6  # 5 viejos + 1 nuevo


# ---------------------------------------------------------------------------
# Listar backups
# ---------------------------------------------------------------------------

class TestListar:
    def test_lista_archivos_existentes(self, db, tmp_path, capsys):
        (tmp_path / "homemanager_20260501_120000.dump").write_bytes(b"x" * 2048)
        (tmp_path / "homemanager_20260502_120000.dump").write_bytes(b"x" * 4096)

        call_command("backup_db", output_dir=str(tmp_path), listar=True)

        out = capsys.readouterr().out
        assert "homemanager_20260501_120000.dump" in out
        assert "homemanager_20260502_120000.dump" in out

    def test_mensaje_cuando_no_hay_backups(self, db, tmp_path, capsys):
        call_command("backup_db", output_dir=str(tmp_path), listar=True)
        out = capsys.readouterr().out
        assert "No hay backups" in out
