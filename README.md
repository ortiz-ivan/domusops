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
| Backend | Python 3.11 · Django 5 · Django REST Framework |
| API docs | drf-spectacular (OpenAPI 3) |
| Frontend | React 19 · Vite 8 |
| Estado | React Context API + TanStack Query v5 |
| Estilos | Tailwind CSS v4 |
| Base de datos | PostgreSQL |
| Gestor de paquetes frontend | pnpm |
| Linting / Format | ESLint 9 · Prettier · Black · isort |
| Tests backend | pytest · pytest-django (461 tests) |
| Tests frontend | Vitest · @testing-library/react (77 tests) |

---

## Características

### Finanzas

- Registro de ingresos, gastos fijos y gastos variables por mes
- Resumen financiero mensual con cálculo de balance y ahorro
- Diferenciación de gasto comprometido / pagado / proyectado
- **Proyecciones de cierre de mes**: calcula el gasto proyectado al ritmo diario actual y emite alertas si supera el ingreso
- **Detección de anomalías**: identifica categorías con gasto inusualmente alto (≥50% sobre el promedio histórico) y productos con reposición fuera de patrón (muy rápida o muy lenta)
- Presupuesto por categoría con seguimiento mensual en tiempo real
- Regla 50/30/20: seguimiento de distribución de gastos por bucket

### Reportes y análisis

- Gráfico de tendencia financiera de los últimos 6 meses
- Comparativa de gasto vs presupuesto por categoría
- Composición de gastos (fijos, variables, inventario)
- Fuentes de ingreso y estado de pagos
- Endpoint de dashboard unificado (`GET /api/v1/dashboard-summary/`) que compila resumen financiero, stock crítico, tareas próximas, metas rezagadas y anomalías activas en una sola llamada

### Inventario y compras

- Catálogo de productos consumibles del hogar
- Historial de consumo y reposiciones por producto
- Alertas de stock bajo y stock crítico configurables
- Planificación de lista de compras con sugerencias automáticas

### Tareas domésticas

- Plantillas de tareas recurrentes (diaria, semanal, mensual, etc.)
- Agenda doméstica con seguimiento de cumplimiento
- Vista de calendario mensual con indicadores por día
- Panel de riesgo e insights por área del hogar

### Metas de ahorro/deuda

- Definición y seguimiento de metas financieras con fecha objetivo
- Progreso visual por meta
- Alertas de metas sin actividad prolongada

### Gestión documental

- Registro de notas, recibos, garantías, manuales y otros documentos del hogar
- Vinculación opcional de documentos a entidades (productos, gastos, tareas)
- Alertas de documentos próximos a vencer

### Menú semanal

- Planificador de comidas con grilla semanal (desayuno, almuerzo, cena, snack)
- Navegación entre semanas
- CRUD por celda directamente en la grilla

### Notificaciones consolidadas

- Panel de campana en el topbar que centraliza: tareas vencidas, stock crítico y gastos fijos por vencer
- Badge con conteo total, agrupado por severidad (danger / warning)

### Experiencia de usuario

- **Modo oscuro / claro**: toggle en el topbar, persiste entre sesiones, respeta la preferencia del sistema operativo en primera visita
- **Persistencia de filtros**: el período financiero seleccionado y la sección activa se restauran al recargar la página
- Animaciones de entrada suaves en cada módulo

### Operaciones y mantenimiento

- **Exportación e importación de datos** (JSON) con modos reemplazar y fusionar — `exportar_datos` / `importar_datos`
- **Backup PostgreSQL** con rotación automática — `backup_db` (`--output-dir`, `--keep N`, `--listar`)
- **Purga de auditoría**: elimina `FinancialEvent` con más de N meses de antigüedad, comprime eventos de meses cerrados — `purgar_historial` (`--meses N`, `--dry-run`)
- **Seed de datos de ejemplo** — `seed_datos` (3 meses cerrados + mes actual parcial, anomalía de mantenimiento incluida)

### API REST documentada

- Paginación, filtros y ordenamiento en todos los endpoints
- Respuestas de error consistentes
- Documentación interactiva en `/api/schema/swagger-ui/`

---

## Estructura del proyecto

```
home-manager/
├── backend/
│   ├── core/                  # Configuración Django (settings, urls, wsgi)
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── exceptions.py      # Manejo de errores centralizado
│   │   └── pagination.py
│   ├── apps/
│   │   ├── assistant/         # App scaffoldeada (pendiente)
│   │   ├── configuration/     # Configuración global e InventorySettings
│   │   ├── expenses/          # Ingresos, gastos fijos y variables
│   │   ├── goals/             # Metas de ahorro/deuda
│   │   ├── household/         # Tareas recurrentes, agenda, documentos, menú
│   │   ├── purchases/         # Productos, reposiciones, lista de compras
│   │   └── reports/           # Reportes, proyecciones, anomalías, dashboard
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   └── manage.py
│
└── frontend/
    ├── src/
    │   ├── App.jsx              # Shell de la aplicación
    │   ├── api.js               # Cliente HTTP centralizado
    │   ├── context/
    │   │   ├── AppContext.jsx    # Orquestador + QueryClientProvider
    │   │   ├── FinanceContext.jsx
    │   │   ├── InventoryContext.jsx
    │   │   ├── ReportsContext.jsx
    │   │   └── HouseholdContext.jsx
    │   ├── hooks/
    │   │   ├── useLocalStorage.js
    │   │   └── useTheme.js
    │   └── components/
    │       ├── dashboard/       # Vista principal con KPIs y alertas
    │       ├── expenses/        # Panel de gastos, proyección y anomalías
    │       ├── reports/         # Gráficos y análisis histórico
    │       ├── inventory/       # Catálogo de productos
    │       ├── purchases/       # Lista de compras
    │       ├── household/       # Tareas, calendario e insights
    │       ├── goals/           # Metas financieras
    │       ├── documents/       # Gestión documental
    │       ├── menu/            # Planificador de menú semanal
    │       ├── settings/        # Configuración de categorías
    │       └── NotificationPanel.jsx
    ├── package.json
    └── vite.config.js
```

---

## Requisitos previos

- Python 3.11+
- Node.js 20+ y pnpm
- PostgreSQL 14+
- Git

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd home-manager
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

# (Opcional) Cargar datos de ejemplo
python backend/manage.py seed_datos
```

### 3. Frontend

```bash
cd frontend
pnpm install
```

---

## Configuración

### Backend — `backend/.env`

```env
SECRET_KEY=cambia-esta-clave-en-produccion
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
DATABASE_URL=postgres://usuario:password@localhost:5432/domusops
ANTHROPIC_API_KEY=sk-...   # Reservado para el asistente IA (próximamente)
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
| `pnpm test` | Ejecutar tests con Vitest |
| `pnpm lint` | Ejecutar ESLint |
| `pnpm format` | Formatear código con Prettier |
| `pnpm format:check` | Verificar formato sin modificar archivos |

### Management commands disponibles

| Comando | Descripción |
| --- | --- |
| `seed_datos` | Carga datos de ejemplo (productos, gastos, metas, tareas) |
| `exportar_datos` | Exporta todos los datos a JSON |
| `importar_datos` | Importa datos desde JSON (modos: reemplazar / fusionar) |
| `backup_db` | Genera backup PostgreSQL con rotación automática |
| `purgar_historial` | Elimina eventos de auditoría antiguos (soporta `--dry-run`) |

---

## API

La documentación interactiva de la API está disponible en:

- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- Schema OpenAPI (JSON): `http://localhost:8000/api/schema/`

### Endpoints principales

| Módulo | Prefijo |
| --- | --- |
| Dashboard unificado | `/api/v1/dashboard-summary/` |
| Gastos e ingresos | `/api/v1/` (`fixed-expenses/`, `variable-expenses/`, `incomes/`) |
| Reportes y proyecciones | `/api/v1/monthly-finance-summary/` |
| Anomalías financieras | `/api/v1/financial-anomalies/` |
| Cierres mensuales | `/api/v1/monthly-closes/` |
| Inventario | `/api/v1/products/` |
| Compras | `/api/v1/purchase-suggestions/` |
| Tareas domésticas | `/api/v1/recurring-tasks/`, `/api/v1/task-occurrences/` |
| Documentos | `/api/v1/documents/` |
| Menú semanal | `/api/v1/meal-plans/` |
| Metas | `/api/v1/goals/` |
| Configuración | `/api/v1/inventory-settings/` |

---

## Tests

### Backend

```bash
cd backend
pytest

# Con cobertura
pytest --cov=apps

# Solo un módulo
pytest apps/reports/tests/
```

Suite actual: **461 tests**, todos pasando.

### Frontend

```bash
cd frontend
pnpm test
```

Suite actual: **77 tests** (Vitest + @testing-library/react). Cubre:

- Funciones de cálculo de `constants/inventory.js`
- Helpers de fechas y agenda de `components/household/`
- Hook `InventoryContext` con API mockeada y `QueryClientProvider`

---

## Roadmap

### Completado

- [x] Proyecciones de gasto mensual (`_compute_monthly_projection`)
- [x] Detección de anomalías financieras (`detect_financial_anomalies`)
- [x] Gasto comprometido / pagado / proyectado (campo `status` en `VariableExpense`)
- [x] Presupuesto por categoría con seguimiento mensual (`CategoryBudgetPanel`)
- [x] Tests backend — 461 tests
- [x] Tests frontend — 77 tests (Vitest + @testing-library/react)
- [x] Exportación e importación de datos JSON
- [x] Backup PostgreSQL con rotación (`backup_db`)
- [x] Seed de datos de ejemplo (`seed_datos`)
- [x] Política de retención de auditoría (`purgar_historial`)
- [x] Gestión documental del hogar (`Document` + `DocumentsView`)
- [x] Planificador de menú semanal (`MealPlan` + `MealPlanView`)
- [x] Dashboard endpoint unificado (`/api/v1/dashboard-summary/`)
- [x] Panel de notificaciones consolidado (`NotificationPanel`)
- [x] AppContext dividido en contextos por dominio (InventoryContext, FinanceContext, ReportsContext, HouseholdContext)
- [x] Fetching con TanStack Query v5 (cache automático, stale-while-revalidate, invalidación quirúrgica)
- [x] Persistencia de filtros en localStorage (período financiero, sección activa)
- [x] Modo oscuro / claro con Tailwind CSS v4 (toggle + respeta preferencia del sistema)
- [x] Optimización N+1 en detección de anomalías de reposición (`prefetch_related`)
- [x] Refactor de `ExpensesPanel.jsx`

### Pendiente

- [ ] Asistente IA con Claude (app `assistant/` scaffoldeada, SDK instalado)
- [ ] Separar `InventorySettings` en métodos por dominio
- [ ] Type hints en `services.py` (reports)
- [ ] django-filter para filtros por rango de fechas en endpoints
- [ ] Comparativa año vs año en reportes
- [ ] Vista de calendario para pagos y tareas (ya existe para household)
- [ ] Racha (streak) en tareas recurrentes
