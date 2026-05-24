import { createContext, useCallback, useContext, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listFinancialEvents, listMonthlyCloses } from "../api.js";
import { useFinanceContext } from "./FinanceContext.jsx";

export const REPORTS_KEYS = {
  all: ["reports"],
  events: (month, year) => ["reports", "events", month, year],
  monthlyCloses: ["reports", "monthly-closes"],
};

const ReportsContext = createContext(null);

export function ReportsProvider({ children, onError }) {
  const queryClient = useQueryClient();
  const { selectedFinancePeriod } = useFinanceContext();
  const month = selectedFinancePeriod?.month;
  const year = selectedFinancePeriod?.year;

  const { data: eventsData, error: eventsError } = useQuery({
    queryKey: REPORTS_KEYS.events(month, year),
    queryFn: () => listFinancialEvents(month, year).then((d) => d || []),
  });

  const { data: closesData, error: closesError } = useQuery({
    queryKey: REPORTS_KEYS.monthlyCloses,
    queryFn: () => listMonthlyCloses().then((d) => d || []),
    staleTime: 60_000,
  });

  const financialEvents = eventsData ?? [];
  const monthlyCloses = closesData ?? [];

  useEffect(() => {
    const err = eventsError || closesError;
    if (err) onError?.(err.message || "Error al cargar historial financiero.");
  }, [eventsError, closesError, onError]);

  const refreshReports = useCallback(
    () => queryClient.invalidateQueries({ queryKey: REPORTS_KEYS.all }),
    [queryClient],
  );

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
