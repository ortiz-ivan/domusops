import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useLocalStorage } from "./hooks/useLocalStorage.js";
import { useTheme } from "./hooks/useTheme.js";
import {
  BarChart2,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  Home,
  LayoutDashboard,
  Moon,
  Package,
  PiggyBank,
  Plus,
  Settings,
  ShoppingCart,
  Sun,
  UtensilsCrossed,
  Wallet,
} from "lucide-react";
import "./App.css";
import {
  AppProvider,
  useAppErrorContext,
  useFinanceContext,
  useHouseholdContext,
  useInventoryContext,
  useOrchestratorContext,
  useReportsContext,
} from "./context/AppContext.jsx";
import { buildNotificationGroups, NotificationPanel } from "./components/NotificationPanel.jsx";
import { DashboardView } from "./components/dashboard/index.js";
import { PurchasesView } from "./components/PurchasesView.jsx";
import { ExpensesPanel } from "./components/ExpensesPanel.jsx";
import { ReportsView } from "./components/ReportsView.jsx";
import {
  getHouseholdAgendaBuckets,
  getHouseholdReminderSummary,
  HouseholdView,
} from "./components/household/index.js";
import { GoalsView } from "./components/goals/index.js";
import { DocumentsView } from "./components/documents/index.js";
import { MealPlanView } from "./components/menu/index.js";
import { ProductForm, ProductList } from "./components/inventory/index.js";
import { SettingsView } from "./components/settings/index.js";
import {
  getCategoryFallbackUnitCost,
  getCategoryLabel,
  getUsageFrequencyWeight,
  isHomeInventoryCategory,
} from "./constants/inventory.js";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

const MODULES = [
  { key: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={15} /> },
  { key: "household", label: "Rutinas", icon: <Home size={15} /> },
  { key: "goals", label: "Metas", icon: <PiggyBank size={15} /> },
  { key: "reports", label: "Reportes", icon: <BarChart2 size={15} /> },
  { key: "inventory", label: "Inventario", icon: <Package size={15} /> },
  { key: "purchases", label: "Compras", icon: <ShoppingCart size={15} /> },
  { key: "expenses", label: "Gastos", icon: <Wallet size={15} /> },
  { key: "documents", label: "Documentos", icon: <FileText size={15} /> },
  { key: "menu", label: "Menu semanal", icon: <UtensilsCrossed size={15} /> },
  { key: "settings", label: "Categorias y Configuracion", icon: <Settings size={15} /> },
];

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function daysBetween(dateString) {
  if (!dateString) return null;
  const target = new Date(dateString);
  if (Number.isNaN(target.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  target.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

function formatPeriodInputValue(month, year) {
  return `${String(year)}-${String(month).padStart(2, "0")}`;
}

function getDefaultFinancePeriodValue(summary) {
  if (summary?.month && summary?.year) {
    return formatPeriodInputValue(summary.month, summary.year);
  }
  const now = new Date();
  return formatPeriodInputValue(now.getMonth() + 1, now.getFullYear());
}

function parsePeriodInputValue(value) {
  const [year, month] = String(value || "").split("-");
  return { month: Number(month), year: Number(year) };
}

// ---------------------------------------------------------------------------
// Hook: derived state for the shell
// ---------------------------------------------------------------------------

function useAppShellState(searchQuery) {
  const { products, inventorySettings } = useInventoryContext();
  const { fixedExpenses } = useFinanceContext();
  const { householdOccurrences } = useHouseholdContext();

  const homeProducts = products.filter((p) =>
    isHomeInventoryCategory(p.category, inventorySettings),
  );

  const filteredHomeProducts = homeProducts.filter((product) => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return true;
    const category = getCategoryLabel(product.category, inventorySettings);
    return (
      product.name.toLowerCase().includes(query) ||
      String(category).toLowerCase().includes(query)
    );
  });

  const lowStockProducts = homeProducts.filter(
    (p) =>
      p.stock <=
      Number(p.stock_min || 0) *
        Number(inventorySettings.thresholds.low_stock_ratio || 1),
  );

  const criticalItems = homeProducts.filter(
    (p) =>
      p.stock <=
        Number(p.stock_min || 0) *
          Number(inventorySettings.thresholds.critical_stock_ratio || 1) &&
      inventorySettings.alerts.critical_frequencies.includes(p.usage_frequency),
  );

  const expiringSoon = homeProducts.filter((p) => {
    const remaining = daysBetween(p.next_due_date);
    return (
      remaining !== null &&
      remaining >= 0 &&
      remaining <= Number(inventorySettings.alerts.expiring_soon_days || 14)
    );
  });

  const totalStockUnits = homeProducts.reduce(
    (acc, p) => acc + Number(p.stock || 0),
    0,
  );

  const monthlySpendEstimate = homeProducts.reduce((acc, p) => {
    const fallbackCost = getCategoryFallbackUnitCost(p.category, inventorySettings);
    const explicitPrice = Number(p.price);
    const baseCost =
      Number.isNaN(explicitPrice) || explicitPrice <= 0 ? fallbackCost : explicitPrice;
    const frequency = getUsageFrequencyWeight(p.usage_frequency, inventorySettings);
    const projectedUnits = p.type === "consumable" ? Number(p.stock_min || 1) : 1;
    return acc + projectedUnits * baseCost * frequency;
  }, 0);

  const householdAgendaSummary = getHouseholdAgendaBuckets(householdOccurrences);
  const householdReminderSummary = getHouseholdReminderSummary(householdOccurrences);

  const dueSoonFixedExpenses = fixedExpenses
    .filter((e) => e.is_active && e.next_due_date)
    .map((e) => ({ ...e, daysLeft: daysBetween(e.next_due_date) }))
    .filter((e) => e.daysLeft !== null && e.daysLeft >= 0 && e.daysLeft <= 7)
    .sort((a, b) => a.daysLeft - b.daysLeft);

  const notificationGroups = buildNotificationGroups({
    overdueOccurrences: householdReminderSummary.overdue,
    criticalItems,
    dueSoonFixedExpenses,
  });

  const reminderHeadline =
    householdReminderSummary.overdue.length > 0
      ? `${householdReminderSummary.overdue.length} tarea(s) atrasadas requieren atencion inmediata.`
      : householdReminderSummary.today.length > 0
        ? `${householdReminderSummary.today.length} tarea(s) vencen hoy.`
        : householdReminderSummary.tomorrow.length > 0
          ? `${householdReminderSummary.tomorrow.length} tarea(s) vencen mañana.`
          : householdReminderSummary.weekUpcoming.length > 0
            ? `${householdReminderSummary.weekUpcoming.length} tarea(s) quedan pendientes esta semana.`
            : "No hay recordatorios urgentes del hogar ahora mismo.";

  return {
    homeProducts,
    filteredHomeProducts,
    lowStockProducts,
    criticalItems,
    expiringSoon,
    totalStockUnits,
    monthlySpendEstimate,
    householdAgendaSummary,
    householdReminderSummary,
    notificationGroups,
    reminderHeadline,
  };
}

// ---------------------------------------------------------------------------
// Shell
// ---------------------------------------------------------------------------

function AppShell() {
  const { theme, toggleTheme } = useTheme();
  const { inventorySettings, loadingSettings, loadingProducts: loading } = useInventoryContext();
  const { fixedExpenses, incomes, variableExpenses, financeSummary, selectedFinancePeriod, setSelectedFinancePeriod } = useFinanceContext();
  const { financialEvents, monthlyCloses } = useReportsContext();
  const { refreshAllData, saveSettings } = useOrchestratorContext();
  const { appError, clearAppError } = useAppErrorContext();

  const [route, setRoute] = useLocalStorage("app-route", "dashboard");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const {
    homeProducts,
    filteredHomeProducts,
    lowStockProducts,
    criticalItems,
    expiringSoon,
    totalStockUnits,
    monthlySpendEstimate,
    householdAgendaSummary,
    householdReminderSummary,
    notificationGroups,
    reminderHeadline,
  } = useAppShellState(searchQuery);

  const navigateTo = (moduleKey) => {
    setRoute(moduleKey);
    setIsModalOpen(false);
  };

  useEffect(() => {
    if (!isModalOpen) return;
    const handleEsc = (event) => { if (event.key === "Escape") setIsModalOpen(false); };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [isModalOpen]);

  const currentModuleLabel = MODULES.find((m) => m.key === route)?.label || "Dashboard";
  const showSearch = route === "dashboard" || route === "inventory";
  const showFinancePeriodSelector = route === "dashboard" || route === "reports" || route === "expenses";
  const financePeriodValue = selectedFinancePeriod
    ? formatPeriodInputValue(selectedFinancePeriod.month, selectedFinancePeriod.year)
    : getDefaultFinancePeriodValue(financeSummary);

  const handleFinancePeriodChange = (event) => {
    const next = event.target.value;
    setSelectedFinancePeriod(next ? parsePeriodInputValue(next) : null);
  };

  return (
    <div className={`app-shell ${isSidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-block">
            <h1>DomusOps</h1>
            <p>Control domestico inteligente</p>
          </div>
          <button
            className="sidebar-toggle"
            type="button"
            onClick={() => setIsSidebarCollapsed((v) => !v)}
            aria-label={isSidebarCollapsed ? "Expandir barra lateral" : "Contraer barra lateral"}
            aria-pressed={isSidebarCollapsed}
          >
            {isSidebarCollapsed ? <ChevronsRight size={15} /> : <ChevronsLeft size={15} />}
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Modulos principales">
          {MODULES.map((module) => (
            <button
              key={module.key}
              className={`nav-item ${route === module.key ? "active" : ""}`}
              type="button"
              onClick={() => navigateTo(module.key)}
              aria-label={module.label}
              title={isSidebarCollapsed ? module.label : undefined}
            >
              <span className="nav-item-icon" aria-hidden="true">{module.icon}</span>
              <span className="nav-item-label">{module.label}</span>
              {module.key === "household" && householdReminderSummary.urgentCount > 0 && (
                <span className="nav-badge" aria-label={`${householdReminderSummary.urgentCount} recordatorios urgentes`}>
                  {householdReminderSummary.urgentCount}
                </span>
              )}
            </button>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="topbar-title">
            <h2>{currentModuleLabel}</h2>
            <p>Estado actualizado del hogar en tiempo real</p>
          </div>

          <div className="topbar-actions">
            <button
              className="btn btn-outline"
              type="button"
              onClick={toggleTheme}
              aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
              title={theme === "dark" ? "Modo claro" : "Modo oscuro"}
              style={{ width: 36, height: 36, padding: 0, display: "inline-grid", placeItems: "center", flexShrink: 0 }}
            >
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>
            <NotificationPanel groups={notificationGroups} />

            {showFinancePeriodSelector && (
              <div className="period-control">
                <label className="period-control-label" htmlFor="finance-period-input">
                  Periodo financiero
                </label>
                <div className="period-control-fields">
                  <input
                    id="finance-period-input"
                    type="month"
                    value={financePeriodValue}
                    onChange={handleFinancePeriodChange}
                    aria-label="Seleccionar periodo financiero"
                  />
                  <button className="btn btn-outline" type="button" onClick={() => setSelectedFinancePeriod(null)}>
                    Periodo activo
                  </button>
                </div>
              </div>
            )}

            {showSearch && (
              <input
                type="search"
                placeholder="Buscar por nombre o categoria"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Buscar en inventario"
              />
            )}

            {route === "inventory" && (
              <button
                className="btn btn-primary"
                type="button"
                onClick={() => setIsModalOpen(true)}
                style={{ display: "flex", alignItems: "center", gap: "6px" }}
              >
                <Plus size={14} />
                Agregar producto de hogar
              </button>
            )}
          </div>
        </header>

        {appError && (
          <div className="app-error-banner" role="alert">
            <span>{appError}</span>
            <button type="button" className="app-error-dismiss" onClick={clearAppError} aria-label="Cerrar">✕</button>
          </div>
        )}

        <section className={`reminder-strip ${householdReminderSummary.overdue.length > 0 ? "is-danger" : householdReminderSummary.today.length > 0 ? "is-warning" : ""}`}>
          <div>
            <strong>Recordatorios del hogar</strong>
            <p>{reminderHeadline}</p>
          </div>
          <div className="reminder-strip-badges">
            <span className="badge low-stock">Atrasadas: {householdReminderSummary.overdue.length}</span>
            <span className="badge">Hoy: {householdReminderSummary.today.length}</span>
            <span className="badge">Mañana: {householdReminderSummary.tomorrow.length}</span>
            <span className="badge">Semana: {householdReminderSummary.weekUpcoming.length}</span>
          </div>
        </section>

        {route === "dashboard" && (
          <DashboardView
            products={homeProducts}
            filteredProducts={filteredHomeProducts}
            householdAgendaSummary={householdAgendaSummary}
            householdReminderSummary={householdReminderSummary}
            lowStockProducts={lowStockProducts}
            criticalItems={criticalItems}
            expiringSoon={expiringSoon}
            monthlySpendEstimate={monthlySpendEstimate}
            financeSummary={financeSummary}
            totalStockUnits={totalStockUnits}
            inventorySettings={inventorySettings}
          />
        )}

        {route === "household" && <HouseholdView />}

        {route === "goals" && <GoalsView />}

        {route === "reports" && (
          <ReportsView
            products={homeProducts}
            incomes={incomes}
            variableExpenses={variableExpenses}
            financeSummary={financeSummary}
            fixedExpenses={fixedExpenses}
            onSelectPeriod={setSelectedFinancePeriod}
            onResetPeriod={() => setSelectedFinancePeriod(null)}
          />
        )}

        {route === "inventory" && (
          <section className="module-content fade-in">
            <div className="section-header">
              <h2>Inventario activo</h2>
              <p>Gestion de productos con buscador, filtros y acciones rapidas.</p>
            </div>
            <ProductList
              products={filteredHomeProducts}
              loading={loading}
              onUpdate={refreshAllData}
              onDelete={refreshAllData}
            />
          </section>
        )}

        {route === "purchases" && (
          <PurchasesView products={homeProducts} onDataChanged={refreshAllData} />
        )}

        {route === "expenses" && (
          <ExpensesPanel
            incomes={incomes}
            summary={financeSummary}
            fixedExpenses={fixedExpenses}
            variableExpenses={variableExpenses}
            financialEvents={financialEvents}
            monthlyCloses={monthlyCloses}
            selectedPeriod={selectedFinancePeriod}
            onDataChanged={refreshAllData}
          />
        )}

        {route === "documents" && <DocumentsView />}

        {route === "menu" && <MealPlanView />}

        {route === "settings" && (
          <SettingsView
            settings={inventorySettings}
            loading={loadingSettings}
            onSave={saveSettings}
          />
        )}
      </section>

      {isModalOpen && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Agregar nuevo producto"
          onClick={() => setIsModalOpen(false)}
        >
          <div className="modal-content compact" onClick={(e) => e.stopPropagation()}>
            <ProductForm
              compact
              onProductCreated={refreshAllData}
              onClose={() => setIsModalOpen(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppProvider>
        <AppShell />
      </AppProvider>
    </QueryClientProvider>
  );
}

export default App;
