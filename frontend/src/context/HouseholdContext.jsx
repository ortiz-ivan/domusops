import { createContext, useCallback, useContext, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listTaskOccurrences } from "../api.js";
import { addDays, formatDateInput } from "../components/household/index.js";

export const HOUSEHOLD_KEYS = {
  all: ["household"],
  occurrences: ["household", "occurrences"],
};

const HouseholdContext = createContext(null);

export function HouseholdProvider({ children, onError }) {
  const queryClient = useQueryClient();

  const { data, error } = useQuery({
    queryKey: HOUSEHOLD_KEYS.occurrences,
    queryFn: () => {
      const dateFrom = formatDateInput(addDays(new Date(), -30));
      const dateTo = formatDateInput(addDays(new Date(), 7));
      return listTaskOccurrences(dateFrom, dateTo).then((d) => d || []);
    },
  });

  const householdOccurrences = data ?? [];

  useEffect(() => {
    if (error) onError?.(error.message || "Error al cargar agenda del hogar.");
  }, [error, onError]);

  const refreshHousehold = useCallback(
    () => queryClient.invalidateQueries({ queryKey: HOUSEHOLD_KEYS.all }),
    [queryClient],
  );

  return (
    <HouseholdContext.Provider value={{ householdOccurrences, refreshHousehold }}>
      {children}
    </HouseholdContext.Provider>
  );
}

export function useHouseholdContext() {
  const ctx = useContext(HouseholdContext);
  if (!ctx) throw new Error("useHouseholdContext must be used inside HouseholdProvider");
  return ctx;
}
