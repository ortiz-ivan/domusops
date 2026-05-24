import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getMonthlyFinanceSummary,
  listFixedExpenses,
  listIncomes,
  listVariableExpenses,
} from "../api.js";
import { useLocalStorage } from "../hooks/useLocalStorage.js";

export const FINANCE_KEYS = {
  all: ["finance"],
  summary: (month, year) => ["finance", "summary", month, year],
  fixedExpenses: (month, year) => ["finance", "fixed-expenses", month, year],
  incomes: (month, year) => ["finance", "incomes", month, year],
  variableExpenses: (month, year) => ["finance", "variable-expenses", month, year],
};

const EMPTY_FINANCE_SUMMARY = {
  month: new Date().getMonth() + 1,
  year: new Date().getFullYear(),
  total_income: 0,
  home_estimated_expenses: 0,
  fixed_estimated_expenses: 0,
  variable_expenses: 0,
  paid_expenses: 0,
  committed_expenses: 0,
  committed_fixed_expenses: 0,
  paid_variable_expenses: 0,
  committed_variable_expenses: 0,
  estimated_expenses: 0,
  expense_percentage: null,
  remaining_balance: 0,
  rule_50_30_20: {
    targets: { needs: 0, wants: 0, savings: 0 },
    actuals: { needs: 0, wants: 0, savings: 0 },
    variance: { needs: 0, wants: 0, savings: 0 },
  },
  projection: null,
};

const FinanceContext = createContext(null);

export function FinanceProvider({ children, onError }) {
  const queryClient = useQueryClient();
  const [selectedFinancePeriod, setSelectedFinancePeriod] = useLocalStorage("finance-period", null);

  const month = selectedFinancePeriod?.month;
  const year = selectedFinancePeriod?.year;

  const { data: fixedExpensesData, error: feError } = useQuery({
    queryKey: FINANCE_KEYS.fixedExpenses(month, year),
    queryFn: () => listFixedExpenses(month, year).then((d) => d || []),
  });

  const { data: incomesData, error: incError } = useQuery({
    queryKey: FINANCE_KEYS.incomes(month, year),
    queryFn: () => listIncomes(month, year).then((d) => d || []),
  });

  const { data: variableExpensesData, error: veError } = useQuery({
    queryKey: FINANCE_KEYS.variableExpenses(month, year),
    queryFn: () => listVariableExpenses(month, year).then((d) => d || []),
  });

  const { data: financeSummaryData, error: fsError } = useQuery({
    queryKey: FINANCE_KEYS.summary(month, year),
    queryFn: () => getMonthlyFinanceSummary(month, year),
  });

  const fixedExpenses = fixedExpensesData ?? [];
  const incomes = incomesData ?? [];
  const variableExpenses = variableExpensesData ?? [];
  const financeSummary = financeSummaryData ?? EMPTY_FINANCE_SUMMARY;

  useEffect(() => {
    const err = feError || incError || veError || fsError;
    if (err) onError?.(err.message || "Error al cargar datos financieros.");
  }, [feError, incError, veError, fsError, onError]);

  const refreshFinance = useCallback(
    () => queryClient.invalidateQueries({ queryKey: FINANCE_KEYS.all }),
    [queryClient],
  );

  return (
    <FinanceContext.Provider value={{
      fixedExpenses,
      incomes,
      variableExpenses,
      financeSummary,
      selectedFinancePeriod,
      setSelectedFinancePeriod,
      refreshFinance,
    }}>
      {children}
    </FinanceContext.Provider>
  );
}

export function useFinanceContext() {
  const ctx = useContext(FinanceContext);
  if (!ctx) throw new Error("useFinanceContext must be used inside FinanceProvider");
  return ctx;
}
