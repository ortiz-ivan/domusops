import { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  getMonthlyFinanceSummary,
  listFixedExpenses,
  listIncomes,
  listVariableExpenses,
} from "../api.js";

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
  const [fixedExpenses, setFixedExpenses] = useState([]);
  const [incomes, setIncomes] = useState([]);
  const [variableExpenses, setVariableExpenses] = useState([]);
  const [financeSummary, setFinanceSummary] = useState(EMPTY_FINANCE_SUMMARY);
  const [selectedFinancePeriod, setSelectedFinancePeriod] = useState(null);

  const refreshFinance = useCallback(async () => {
    const month = selectedFinancePeriod?.month;
    const year = selectedFinancePeriod?.year;
    try {
      const [fixed, income, variable, summary] = await Promise.all([
        listFixedExpenses(month, year),
        listIncomes(month, year),
        listVariableExpenses(month, year),
        getMonthlyFinanceSummary(month, year),
      ]);
      setFixedExpenses(fixed || []);
      setIncomes(income || []);
      setVariableExpenses(variable || []);
      if (summary) setFinanceSummary(summary);
    } catch (err) {
      setFixedExpenses([]);
      setIncomes([]);
      setVariableExpenses([]);
      onError?.(err.message || "Error al cargar datos financieros.");
    }
  }, [selectedFinancePeriod, onError]);

  useEffect(() => {
    refreshFinance();
  }, [refreshFinance]);

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
