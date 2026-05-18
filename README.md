# DomusOps

Sistema personal de gestión del hogar: finanzas, inventario, tareas domésticas y metas de ahorro.

## Tabla de contenidos

- [Descripción](#descripción)
- [Stack tecnológico](#stack-tecnológico)
- [Características](#características)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [API](#api)
- [Tests](#tests)
- [Roadmap](#roadmap)

---

## Descripción

DomusOps centraliza la administración del hogar en una sola aplicación: controla ingresos, gastos fijos y variables, gestiona el inventario de productos, planifica compras, lleva el seguimiento de tareas recurrentes del hogar y monitorea el avance hacia metas financieras.

Incluye análisis automático: proyecciones de gasto mensual, detección de anomalías financieras y alertas tempranas cuando el ritmo de gasto supera el ingreso disponible.

---

## Stack tecnológico

| Capa | Tecnología |
| --- | --- |
| Backend | Python 3 · Django 5 · Django REST Framework |
| API docs | drf-spectacular (OpenAPI 3) |
| Frontend | React 19 · Vite 8 |
| Estilos | CSS nativo (sin framework) |
| Base de datos | SQLite (desarrollo) |
| Linting / Format | ESLint 9 · Prettier · Black · isort |
| Tests backend | pytest · pytest-django |

---

## Características

### Finanzas

- Registro de ingresos, gastos fijos y gastos variables por mes
- Resumen financiero mensual con cálculo de balance y ahorro
- **Proyecciones de cierre de mes**: calcula el gasto proyectado al ritmo diario actual y emite alertas si supera el ingreso
- **Detección de anomalías**: identifica categorías con gasto inusualmente alto (≥50% sobre el promedio histórico) y productos con reposición fuera de patrón (muy rápida o muy lenta)

### Inventario y compras

- Catálogo de productos consumibles del hogar
- Historial de consumo y reposiciones por producto
- Planificación de lista de compras con sugerencias automáticas

### Tareas domésticas

- Plantillas de tareas recurrentes (diaria, semanal, mensual, etc.)
- Agenda doméstica con seguimiento de cumplimiento
- Panel de riesgo e insights por área del hogar

### Metas de ahorro/deuda

- Definición y seguimiento de metas financieras con fecha objetivo
- Progreso visual por meta

### API REST documentada

- Paginación, filtros y ordenamiento en todos los endpoints
- Respuestas de error consistentes
- Documentación interactiva en `/api/schema/swagger-ui/`

---

## Estructura del proyecto

```tree
home-manager/
├── backend/
│   ├── core/                  # Configuración Django (settings, urls, wsgi)
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── exceptions.py      # Manejo de errores centralizado
│   │   └── pagination.py
│   ├── apps/
│   │   ├── configuration/     # Configuración de la app
│   │   ├── expenses/          # Ingresos, gastos fijos y variables
│   │   ├── inventory/         # Catálogo de productos
│   │   ├── purchases/         # Lista y planificación de compras
│   │   ├── reports/           # Reportes, proyecciones y anomalías
│   │   ├── household/         # Tareas y agenda doméstica
│   │   └── goals/             # Metas de ahorro/deuda
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   └── manage.py
│
└── frontend/
    ├── src/
    │   ├── App.jsx            # Componente raíz
    │   ├── api.js             # Cliente HTTP centralizado
    │   ├── context/
    │   │   └── AppContext.jsx # Estado global (React Context)
    │   └── components/
    │       ├── expenses/      # Panel de gastos y finanzas
    │       ├── purchases/     # Vista de compras
    │       ├── inventory/     # Gestión de inventario
    │       ├── household/     # Tareas domésticas
    │       ├── goals/         # Metas financieras
    │       └── reports/       # Reportes y gráficos
    ├── package.json
    └── vite.config.js
```

---

## Requisitos previos

- Python 3.11+
- Node.js 20+ y pnpm
- Git

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd domusops
```

### 2. Backend

```bash
# Crear y activar entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Instalar dependencias
pip install -r backend/requirements.txt
# Para desarrollo
pip install -r backend/requirements-dev.txt

# Aplicar migraciones
python backend/manage.py migrate

# Crear superusuario (opcional)
python backend/manage.py createsuperuser
```

### 3. Frontend

```bash
cd frontend
pnpm install
```

---

## Configuración

### Backend — `backend/.env`

Crear el archivo copiando el ejemplo y ajustando los valores:

```env
SECRET_KEY=cambia-esta-clave-en-produccion
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### Frontend — `frontend/.env`

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Uso

### Iniciar el backend

```bash
# Desde la raíz del proyecto, con el venv activado
python backend/manage.py runserver
```

El servidor queda disponible en `http://localhost:8000`.

### Iniciar el frontend

```bash
cd frontend
pnpm dev
```

La app queda disponible en `http://localhost:5173`.

### Scripts frontend disponibles

| Comando | Descripción |
| --- | --- |
| `pnpm dev` | Servidor de desarrollo con HMR |
| `pnpm build` | Build de producción |
| `pnpm preview` | Previsualizar el build de producción |
| `pnpm lint` | Ejecutar ESLint |
| `pnpm format` | Formatear código con Prettier |
| `pnpm format:check` | Verificar formato sin modificar archivos |

---

## API

La documentación interactiva de la API está disponible en:

- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- Schema OpenAPI (JSON): `http://localhost:8000/api/schema/`

### Endpoints principales

| Módulo | Prefijo |
| --- | --- |
| Gastos e ingresos | `/api/v1/expenses/` |
| Reportes y proyecciones | `/api/v1/reports/` |
| Anomalías financieras | `/api/v1/financial-anomalies/` |
| Inventario | `/api/v1/inventory/` |
| Compras | `/api/v1/purchases/` |
| Tareas domésticas | `/api/v1/household/` |
| Metas | `/api/v1/goals/` |
| Configuración | `/api/v1/configuration/` |

---

## Tests

### Backend

```bash
# Desde la raíz del proyecto, con el venv activado
cd backend
pytest

# Con cobertura
pytest --cov=apps

# Solo un módulo
pytest apps/reports/tests/
```

La configuración de pytest está en `backend/pytest.ini` y `backend/pyproject.toml`.

### Frontend

El proyecto usa ESLint para análisis estático. No hay suite de tests unitarios de frontend configurada aún (previsto en el roadmap).

```bash
cd frontend
pnpm lint
```

---

## Roadmap

### Completado

- [x] Proyecciones de gasto mensual
- [x] Detección de anomalías financieras
- [x] Diferenciar gasto comprometido / pagado / proyectado
- [x] Presupuesto por categoría con seguimiento mensual
- [x] Ampliar cobertura de tests críticos (backend) — 358 tests
- [x] Exportación e importación de datos (JSON) — `exportar_datos` / `importar_datos`
- [x] Script de backup PostgreSQL — `backup_db` con rotación automática
- [x] Seed de datos de ejemplo — `seed_datos` (3 meses cerrados + mes actual, anomalía incluida)
- [x] Refactor de `ExpensesPanel.jsx`

### Pendiente

- [ ] Política de retención de datos históricos
- [ ] Gestión documental del hogar
- [ ] Planificador de menú semanal integrado con inventario
