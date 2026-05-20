/**
 * @typedef {{ month: number, year: number }} Period
 * @typedef {{ id: number, name: string, category: string, type: string, budget_bucket: string, stock: number, stock_min: number, unit: string, price: number|null, usage_frequency: string, is_active: boolean }} Product
 * @typedef {{ id: number, amount: string, source: string, notes: string, date: string }} Income
 * @typedef {{ id: number, name: string, category: string, monthly_amount: string, budget_bucket: string, is_active: boolean, next_due_date: string|null }} FixedExpense
 * @typedef {{ id: number, amount: string, category: string, description: string, date: string }} VariableExpense
 * @typedef {{ month: number, year: number, total_income: number, estimated_expenses: number, expense_percentage: number|null, remaining_balance: number, rule_50_30_20: object }} FinanceSummary
 * @typedef {{ id: number, name: string, goal_type: string, target_amount: string, current_amount: string, is_active: boolean }} SavingsGoal
 * @typedef {{ id: number, title: string, category: string, area: string, priority: string, frequency_type: string, is_active: boolean }} RecurringTask
 * @typedef {{ id: number, recurring_task: RecurringTask, due_date: string, status: string }} TaskOccurrence
 */

function normalizeBaseUrl(url) {
  return url.endsWith("/") ? url : `${url}/`;
}

const API_BASE = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1/",
);
const API_KEY = import.meta.env.VITE_API_KEY || "";

const PATHS = {
  products: "products/",
  fixedExpenses: "fixed-expenses/",
  incomes: "incomes/",
  variableExpenses: "variable-expenses/",
  recurringTasks: "recurring-tasks/",
  taskOccurrences: "task-occurrences/",
  savingsGoals: "savings-goals/",
  financialEvents: "financial-events/",
  monthlyCloses: "monthly-closes/",
  monthlyFinanceSummary: "monthly-finance-summary/",
  householdInsights: "household-insights/",
  financialAnomalies: "financial-anomalies/",
  dashboardSummary: "dashboard-summary/",
  settings: "settings/",
  documents: "documents/",
  mealPlans: "meal-plans/",
};

function buildUrl(base, params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  const qs = query.toString();
  return qs ? `${base}?${qs}` : base;
}

async function request(path = "", options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-Api-Key": API_KEY } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = data?.detail || "No se pudo completar la operacion";
    throw new Error(detail);
  }

  if (data !== null && typeof data === "object" && Array.isArray(data.results)) {
    return data.results;
  }

  return data;
}

/** @returns {Promise<Product[]>} */
export function listProducts() {
  return request(PATHS.products);
}

export function createProduct(payload) {
  return request(PATHS.products, { method: "POST", body: JSON.stringify(payload) });
}

export function updateProduct(id, payload) {
  return request(`${PATHS.products}${id}/`, { method: "PUT", body: JSON.stringify(payload) });
}

export function deleteProduct(id) {
  return request(`${PATHS.products}${id}/`, { method: "DELETE" });
}

export function consumeProduct(id, quantity = 1) {
  return request(`${PATHS.products}${id}/consume/`, { method: "POST", body: JSON.stringify({ quantity }) });
}

export function buyProduct(id, quantity = 1) {
  return request(`${PATHS.products}${id}/buy/`, { method: "POST", body: JSON.stringify({ quantity }) });
}

export function markOutOfStock(id) {
  return request(`${PATHS.products}${id}/out_of_stock/`, { method: "POST", body: JSON.stringify({}) });
}

export function getProductStats(id, days = 90) {
  return request(buildUrl(`${PATHS.products}${id}/stats/`, { days }));
}

export function listProductConsumptions(id, days = 90) {
  return request(buildUrl(`${PATHS.products}${id}/consumption/`, { days }));
}

export function listProductRestocks(id, days = 90) {
  return request(buildUrl(`${PATHS.products}${id}/restocks/`, { days }));
}

/** @returns {Promise<FixedExpense[]>} */
export function listFixedExpenses(month, year) {
  return request(buildUrl(PATHS.fixedExpenses, { month, year }));
}

export function createFixedExpense(payload) {
  return request(PATHS.fixedExpenses, { method: "POST", body: JSON.stringify(payload) });
}

export function updateFixedExpense(id, payload) {
  return request(`${PATHS.fixedExpenses}${id}/`, { method: "PUT", body: JSON.stringify(payload) });
}

export function payFixedExpense(id, payload = {}) {
  return request(`${PATHS.fixedExpenses}${id}/pay/`, { method: "POST", body: JSON.stringify(payload) });
}

/** @returns {Promise<Income[]>} */
export function listIncomes(month, year) {
  return request(buildUrl(PATHS.incomes, { month, year }));
}

export function createIncome(payload) {
  return request(PATHS.incomes, { method: "POST", body: JSON.stringify(payload) });
}

export function deleteIncome(id) {
  return request(`${PATHS.incomes}${id}/`, { method: "DELETE" });
}

export function updateIncome(id, payload) {
  return request(`${PATHS.incomes}${id}/`, { method: "PUT", body: JSON.stringify(payload) });
}

export function listVariableExpenses(month, year) {
  return request(buildUrl(PATHS.variableExpenses, { month, year }));
}

export function createVariableExpense(payload) {
  return request(PATHS.variableExpenses, { method: "POST", body: JSON.stringify(payload) });
}

export function deleteVariableExpense(id) {
  return request(`${PATHS.variableExpenses}${id}/`, { method: "DELETE" });
}

export function updateVariableExpense(id, payload) {
  return request(`${PATHS.variableExpenses}${id}/`, { method: "PUT", body: JSON.stringify(payload) });
}

/** @returns {Promise<FinanceSummary>} */
export function getMonthlyFinanceSummary(month, year) {
  return request(buildUrl(PATHS.monthlyFinanceSummary, { month, year }));
}

export function listFinancialEvents(month, year, limit = 25) {
  return request(buildUrl(PATHS.financialEvents, { month, year, limit }));
}

export function listMonthlyCloses() {
  return request(PATHS.monthlyCloses);
}

export function createMonthlyClose(payload) {
  return request(PATHS.monthlyCloses, { method: "POST", body: JSON.stringify(payload) });
}

export function getInventorySettings() {
  return request(PATHS.settings);
}

export function updateInventorySettings(config) {
  return request(PATHS.settings, { method: "PUT", body: JSON.stringify({ config }) });
}

/** @returns {Promise<RecurringTask[]>} */
export function listRecurringTasks(filters = {}) {
  return request(buildUrl(PATHS.recurringTasks, filters));
}

export function createRecurringTask(payload) {
  return request(PATHS.recurringTasks, { method: "POST", body: JSON.stringify(payload) });
}

export function updateRecurringTask(id, payload) {
  return request(`${PATHS.recurringTasks}${id}/`, { method: "PUT", body: JSON.stringify(payload) });
}

export function deleteRecurringTask(id) {
  return request(`${PATHS.recurringTasks}${id}/`, { method: "DELETE" });
}

/** @returns {Promise<TaskOccurrence[]>} */
export function listTaskOccurrences(dateFrom, dateTo, status, filters = {}) {
  return request(buildUrl(PATHS.taskOccurrences, {
    from: dateFrom,
    to: dateTo,
    status,
    ...filters,
  }));
}

export function completeTaskOccurrence(id, payload = {}) {
  return request(`${PATHS.taskOccurrences}${id}/complete/`, { method: "POST", body: JSON.stringify(payload) });
}

export function skipTaskOccurrence(id, payload = {}) {
  return request(`${PATHS.taskOccurrences}${id}/skip/`, { method: "POST", body: JSON.stringify(payload) });
}

export function reopenTaskOccurrence(id) {
  return request(`${PATHS.taskOccurrences}${id}/reopen/`, { method: "POST", body: JSON.stringify({}) });
}

/** @returns {Promise<SavingsGoal[]>} */
export function listSavingsGoals(filters = {}) {
  return request(buildUrl(PATHS.savingsGoals, filters));
}

export function createSavingsGoal(payload) {
  return request(PATHS.savingsGoals, { method: "POST", body: JSON.stringify(payload) });
}

export function updateSavingsGoal(id, payload) {
  return request(`${PATHS.savingsGoals}${id}/`, { method: "PUT", body: JSON.stringify(payload) });
}

export function deleteSavingsGoal(id) {
  return request(`${PATHS.savingsGoals}${id}/`, { method: "DELETE" });
}

export function contributeToGoal(id, amount) {
  return request(`${PATHS.savingsGoals}${id}/contribute/`, { method: "POST", body: JSON.stringify({ amount }) });
}

export function getHouseholdInsights(dateFrom, dateTo, filters = {}) {
  return request(buildUrl(PATHS.householdInsights, { from: dateFrom, to: dateTo, ...filters }));
}

export function getFinancialAnomalies(month, year) {
  return request(buildUrl(PATHS.financialAnomalies, { month, year }));
}

export function getDashboardSummary() {
  return request(PATHS.dashboardSummary);
}

export function listDocuments(params = {}) {
  return request(buildUrl(PATHS.documents, params));
}

export function createDocument(payload) {
  return request(PATHS.documents, { method: "POST", body: JSON.stringify(payload) });
}

export function updateDocument(id, payload) {
  return request(`${PATHS.documents}${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteDocument(id) {
  return request(`${PATHS.documents}${id}/`, { method: "DELETE" });
}

export function listMealPlans(params = {}) {
  return request(buildUrl(PATHS.mealPlans, params));
}

export function createMealPlan(payload) {
  return request(PATHS.mealPlans, { method: "POST", body: JSON.stringify(payload) });
}

export function updateMealPlan(id, payload) {
  return request(`${PATHS.mealPlans}${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteMealPlan(id) {
  return request(`${PATHS.mealPlans}${id}/`, { method: "DELETE" });
}
