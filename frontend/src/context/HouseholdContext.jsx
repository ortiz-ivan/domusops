import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { listTaskOccurrences } from "../api.js";
import { addDays, formatDateInput } from "../components/household/index.js";

const HouseholdContext = createContext(null);

export function HouseholdProvider({ children, onError }) {
  const [householdOccurrences, setHouseholdOccurrences] = useState([]);

  const refreshHousehold = useCallback(async () => {
    const dateFrom = formatDateInput(addDays(new Date(), -30));
    const dateTo = formatDateInput(addDays(new Date(), 7));
    try {
      const data = await listTaskOccurrences(dateFrom, dateTo);
      setHouseholdOccurrences(data || []);
    } catch (err) {
      setHouseholdOccurrences([]);
      onError?.(err.message || "Error al cargar agenda del hogar.");
    }
  }, [onError]);

  useEffect(() => {
    refreshHousehold();
  }, [refreshHousehold]);

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
