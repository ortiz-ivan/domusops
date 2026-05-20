import { createContext, useCallback, useContext, useState } from "react";
import { updateInventorySettings } from "../api.js";
import { normalizeInventorySettings } from "../constants/inventory.js";
import { FinanceProvider, useFinanceContext } from "./FinanceContext.jsx";
import { HouseholdProvider, useHouseholdContext } from "./HouseholdContext.jsx";
import { InventoryProvider, useInventoryContext } from "./InventoryContext.jsx";
import { ReportsProvider, useReportsContext } from "./ReportsContext.jsx";

// ─── Error context ────────────────────────────────────────────────────────────

const AppErrorContext = createContext(null);

export function useAppErrorContext() {
  const ctx = useContext(AppErrorContext);
  if (!ctx) throw new Error("useAppErrorContext must be used inside AppProvider");
  return ctx;
}

// ─── Orchestrator context ─────────────────────────────────────────────────────
// Lives inside all domain providers so it can call their refresh functions.

const AppOrchestratorContext = createContext(null);

export function useOrchestratorContext() {
  const ctx = useContext(AppOrchestratorContext);
  if (!ctx) throw new Error("useOrchestratorContext must be used inside AppProvider");
  return ctx;
}

function AppOrchestrator({ children }) {
  const { refreshProducts, updateSettings } = useInventoryContext();
  const { refreshFinance } = useFinanceContext();
  const { refreshReports } = useReportsContext();
  const { refreshHousehold } = useHouseholdContext();
  const { setAppError } = useContext(AppErrorContext);

  const refreshAllData = useCallback(async () => {
    await Promise.all([refreshProducts(), refreshFinance(), refreshReports(), refreshHousehold()]);
  }, [refreshProducts, refreshFinance, refreshReports, refreshHousehold]);

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
          <ReportsProvider onError={setAppError}>
            <HouseholdProvider onError={setAppError}>
              <AppOrchestrator>
                {children}
              </AppOrchestrator>
            </HouseholdProvider>
          </ReportsProvider>
        </FinanceProvider>
      </InventoryProvider>
    </AppErrorContext.Provider>
  );
}

// ─── Domain hook re-exports ───────────────────────────────────────────────────

export { useInventoryContext } from "./InventoryContext.jsx";
export { useFinanceContext } from "./FinanceContext.jsx";
export { useReportsContext } from "./ReportsContext.jsx";
export { useHouseholdContext } from "./HouseholdContext.jsx";

export function useInventorySettings() {
  return useInventoryContext().inventorySettings;
}
