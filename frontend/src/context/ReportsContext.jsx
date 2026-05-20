import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { listFinancialEvents, listMonthlyCloses } from "../api.js";
import { useFinanceContext } from "./FinanceContext.jsx";

const ReportsContext = createContext(null);

export function ReportsProvider({ children, onError }) {
  const { selectedFinancePeriod } = useFinanceContext();
  const [financialEvents, setFinancialEvents] = useState([]);
  const [monthlyCloses, setMonthlyCloses] = useState([]);

  const refreshReports = useCallback(async () => {
    const month = selectedFinancePeriod?.month;
    const year = selectedFinancePeriod?.year;
    try {
      const [events, closes] = await Promise.all([
        listFinancialEvents(month, year),
        listMonthlyCloses(),
      ]);
      setFinancialEvents(events || []);
      setMonthlyCloses(closes || []);
    } catch (err) {
      setFinancialEvents([]);
      setMonthlyCloses([]);
      onError?.(err.message || "Error al cargar historial financiero.");
    }
  }, [selectedFinancePeriod, onError]);

  useEffect(() => {
    refreshReports();
  }, [refreshReports]);

  return (
    <ReportsContext.Provider value={{ financialEvents, monthlyCloses, refreshReports }}>
      {children}
    </ReportsContext.Provider>
  );
}

export function useReportsContext() {
  const ctx = useContext(ReportsContext);
  if (!ctx) throw new Error("useReportsContext must be used inside ReportsProvider");
  return ctx;
}
