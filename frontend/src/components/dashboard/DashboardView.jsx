import { AlertCircle, AlertTriangle, CalendarClock, CalendarDays, Zap } from "lucide-react";
import { formatCurrency, getCategoryLabel } from "../../constants/inventory.js";
import { HouseholdDashboardSection } from "../household/index.js";

export function DashboardView({
  products,
  filteredProducts,
  householdAgendaSummary,
  householdReminderSummary,
  lowStockProducts,
  criticalItems,
  expiringSoon,
  monthlySpendEstimate,
  financeSummary,
  totalStockUnits,
  inventorySettings,
}) {
  return (
    <section className="module-content fade-in">
      <div className="section-header">
        <h2>Control operativo del hogar</h2>
        <p>Monitorea riesgos, consumo y gasto estimado desde una sola vista.</p>
      </div>

      <div className="alerts-grid">
        <article className="alert-card alert-danger">
          <header>
            <span className="alert-icon"><AlertTriangle size={14} /></span>
            <h3>Stock bajo</h3>
          </header>
          <strong>{lowStockProducts.length} productos</strong>
          <p>Prioriza reposicion de productos criticos para evitar faltantes.</p>
        </article>

        <article className="alert-card alert-warning">
          <header>
            <span className="alert-icon"><CalendarClock size={14} /></span>
            <h3>Proximos a vencer</h3>
          </header>
          <strong>{expiringSoon.length} productos</strong>
          <p>
            Detectados con fecha de vencimiento dentro de {inventorySettings.alerts.expiring_soon_days} dias.
          </p>
        </article>

        <article className="alert-card alert-critical">
          <header>
            <span className="alert-icon"><Zap size={14} /></span>
            <h3>Items criticos</h3>
          </header>
          <strong>{criticalItems.length} items</strong>
          <p>Stock critico en productos con frecuencia marcada como sensible.</p>
        </article>

        <article className="alert-card alert-danger">
          <header>
            <span className="alert-icon"><AlertCircle size={14} /></span>
            <h3>Tareas atrasadas</h3>
          </header>
          <strong>{householdReminderSummary.overdue.length} rutinas</strong>
          <p>Lo vencido debe resolverse primero para que no se acumule friccion operativa.</p>
        </article>

        <article className="alert-card alert-warning">
          <header>
            <span className="alert-icon"><CalendarDays size={14} /></span>
            <h3>Vence mañana</h3>
          </header>
          <strong>{householdReminderSummary.tomorrow.length} tareas</strong>
          <p>Te ayuda a preparar compras, limpieza o pagos antes del siguiente dia.</p>
        </article>

        <article className="alert-card alert-critical">
          <header>
            <span className="alert-icon"><CalendarDays size={14} /></span>
            <h3>Esta semana</h3>
          </header>
          <strong>{householdReminderSummary.weekUpcoming.length} pendientes</strong>
          <p>Visibilidad rapida de lo que aun no vence hoy pero ya conviene anticipar.</p>
        </article>
      </div>

      <div className="kpi-grid">
        <article className="kpi-card">
          <p>Gasto mensual estimado</p>
          <h3>{formatCurrency(monthlySpendEstimate)}</h3>
          <small>Estimacion basada en categoria y frecuencia de uso.</small>
        </article>

        <article className="kpi-card">
          <p>Total de productos en stock</p>
          <h3>{totalStockUnits}</h3>
          <small>Unidades totales disponibles en inventario.</small>
        </article>

        <article className="kpi-card">
          <p>Productos gestionados</p>
          <h3>{products.length}</h3>
          <small>{filteredProducts.length} visibles con filtros activos.</small>
        </article>

        <article className="kpi-card">
          <p>Gasto sobre ingreso mensual</p>
          <h3>
            {financeSummary.expense_percentage === null
              ? "Sin ingresos"
              : `${financeSummary.expense_percentage}%`}
          </h3>
          <small>Saldo: {formatCurrency(financeSummary.remaining_balance)}</small>
        </article>
      </div>

      <article className="panel recent-panel">
        <div className="panel-title">
          <h3>Resumen de inventario</h3>
        </div>
        <div className="summary-list">
          {filteredProducts.slice(0, 6).map((product) => {
            const isLow = product.stock <= product.stock_min;
            const status = isLow ? "Bajo" : product.stock <= product.stock_min * 2 ? "Medio" : "Alto";
            return (
              <div className="summary-row" key={product.id}>
                <div>
                  <strong>{product.name}</strong>
                  <p>{getCategoryLabel(product.category)}</p>
                </div>
                <div className={`stock-chip ${status.toLowerCase()}`}>{status}</div>
              </div>
            );
          })}
          {filteredProducts.length === 0 && <p>No hay productos para mostrar.</p>}
        </div>
      </article>

      <HouseholdDashboardSection summary={householdAgendaSummary} />
    </section>
  );
}
