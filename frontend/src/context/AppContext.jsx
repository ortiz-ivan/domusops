import { createContext, useCallback, useContext, useState } from "react";
import { updateInventorySettings } from "../api.js";
import { normalizeInventorySettings } from "../constants/inventory.js";
import { FinanceProvider, useFinanceContext } from "./FinanceContext.jsx";
import { HouseholdProvider, useHouseholdContext } from "./HouseholdContext.jsx";
import { InventoryProvider, useInventoryContext } from "./InventoryContext.jsx";

// ─── Error context ────────────────────────────────────────────────────────────
// Outermost layer — all domain providers report errors here.

const AppErrorContext = createContext(null);

// ─── Orchestrator context ─────────────────────────────────────────────────────
// Lives inside all domain providers so it can call their refresh functions.

const AppOrchestratorContext = createContext(null);

function AppOrchestrator({ children }) {
  const { refreshProducts, updateSettings } = useInventoryContext();
  const { refreshFinance } = useFinanceContext();
  const { refreshHousehold } = useHouseholdContext();
  const { setAppError } = useContext(AppErrorContext);

  const refreshAllData = useCallback(async () => {
    await Promise.all([refreshProducts(), refreshFinance(), refreshHousehold()]);
  }, [refreshProducts, refreshFinance, refreshHousehold]);

  const saveSettings = useCallback(async (nextSettings) => {
    try {
      const response = await updateInventorySettings(nextSettings);
      const updated = normalizeInventorySettings(response);
      updateSettings(updated);
      await refreshAllData();
    } catch (err) {
      setAppError(err.message || "Error al guardar configuracion.");
      throw err;
    }
  }, [updateSettings, refreshAllData, setAppError]);

  return (
    <AppOrchestratorContext.Provider value={{ refreshAllData, saveSettings }}>
      {children}
    </AppOrchestratorContext.Provider>
  );
}

// ─── Public provider ──────────────────────────────────────────────────────────

export function AppProvider({ children }) {
  const [appError, setAppError] = useState(null);
  const clearAppError = useCallback(() => setAppError(null), []);

  return (
    <AppErrorContext.Provider value={{ appError, setAppError, clearAppError }}>
      <InventoryProvider onError={setAppError}>
        <FinanceProvider onError={setAppError}>
          <HouseholdProvider onError={setAppError}>
            <AppOrchestrator>
              {children}
            </AppOrchestrator>
          </HouseholdProvider>
        </FinanceProvider>
      </InventoryProvider>
    </AppErrorContext.Provider>
  );
}

// ─── Backward-compat hook ─────────────────────────────────────────────────────
// Merges all domain contexts into the original flat shape so existing consumers
// (App.jsx, CategoryBudgetPanel.jsx) continue to work without changes.

export function useAppContext() {
  const errorCtx = useContext(AppErrorContext);
  const orchCtx = useContext(AppOrchestratorContext);
  const inventory = useInventoryContext();
  const finance = useFinanceContext();
  const household = useHouseholdContext();

  if (!errorCtx || !orchCtx) {
    throw new Error("useAppContext must be used inside AppProvider");
  }

  return {
    // ── Inventory ──
    products: inventory.products,
    inventorySettings: inventory.inventorySettings,
    loadingSettings: inventory.loadingSettings,
    loading: inventory.loadingProducts,

    // ── Finance ──
    fixedExpenses: finance.fixedExpenses,
    incomes: finance.incomes,
    variableExpenses: finance.variableExpenses,
    financeSummary: finance.financeSummary,
    financialEvents: finance.financialEvents,
    monthlyCloses: finance.monthlyCloses,
    selectedFinancePeriod: finance.selectedFinancePeriod,
    setSelectedFinancePeriod: finance.setSelectedFinancePeriod,

    // ── Household ──
    householdOccurrences: household.householdOccurrences,

    // ── App-level ──
    appError: errorCtx.appError,
    clearAppError: errorCtx.clearAppError,
    refreshAllData: orchCtx.refreshAllData,
    saveSettings: orchCtx.saveSettings,
  };
}

// ─── Domain-specific hooks (for new code) ─────────────────────────────────────

export { useInventoryContext } from "./InventoryContext.jsx";
export { useFinanceContext } from "./FinanceContext.jsx";
export { useHouseholdContext } from "./HouseholdContext.jsx";

// Kept for backward compat (referenced in constants/inventory.js comment)
export function useInventorySettings() {
  return useInventoryContext().inventorySettings;
}
