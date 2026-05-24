import { createContext, useCallback, useContext, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { updateInventorySettings } from "../api.js";
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

const AppOrchestratorContext = createContext(null);

export function useOrchestratorContext() {
  const ctx = useContext(AppOrchestratorContext);
  if (!ctx) throw new Error("useOrchestratorContext must be used inside AppProvider");
  return ctx;
}

function AppOrchestrator({ children }) {
  const queryClient = useQueryClient();
  const { setAppError } = useContext(AppErrorContext);

  const refreshAllData = useCallback(
    () => queryClient.invalidateQueries(),
    [queryClient],
  );

  const saveSettings = useCallback(async (nextSettings) => {
    try {
      await updateInventorySettings(nextSettings);
      await queryClient.invalidateQueries();
    } catch (err) {
      setAppError(err.message || "Error al guardar configuracion.");
      throw err;
    }
  }, [queryClient, setAppError]);

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
