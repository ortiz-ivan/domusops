import { useCallback, useEffect, useState } from "react";
import {
  completeTaskOccurrence,
  createRecurringTask,
  getHouseholdInsights,
  listFixedExpenses,
  listProducts,
  listRecurringTasks,
  listTaskOccurrences,
  reopenTaskOccurrence,
  skipTaskOccurrence,
} from "../../api.js";
import {
  getHouseholdTaskAreaOptions,
  getHouseholdTaskCategoryOptions,
  getHouseholdTaskPriorityOptions,
} from "../../constants/inventory.js";
import { HOUSEHOLD_INTEGRATION_OPTIONS } from "./integration.js";
import { addDays, formatDateInput, getHouseholdAgendaBuckets, getTodayDateInput } from "./utils.js";

function createInitialFormData() {
  const categoryOptions = getHouseholdTaskCategoryOptions();
  const areaOptions = getHouseholdTaskAreaOptions();
  const priorityOptions = getHouseholdTaskPriorityOptions();

  return {
    title: "",
    category: categoryOptions[0]?.value || "cleaning",
    area: areaOptions[0]?.value || "home_admin",
    priority: priorityOptions[1]?.value || priorityOptions[0]?.value || "medium",
    estimated_minutes: 15,
    integration_kind: "",
    linked_fixed_expense: "",
    linked_product: "",
    frequency_type: "weekly",
    interval: 1,
    weekday: new Date().getDay() === 0 ? 6 : new Date().getDay() - 1,
    day_of_month: 1,
    start_date: formatDateInput(new Date()),
    notes: "",
    is_active: true,
  };
}

export function useHouseholdViewController() {
  const categoryOptions = getHouseholdTaskCategoryOptions();
  const areaOptions = getHouseholdTaskAreaOptions();
  const priorityOptions = getHouseholdTaskPriorityOptions();

  const [recurringTasks, setRecurringTasks] = useState([]);
  const [occurrences, setOccurrences] = useState([]);
  const [insights, setInsights] = useState({
    weekly_completion: [],
    most_postponed_tasks: [],
    recurring_overdue_tasks: [],
    weekly_estimated_minutes: 0,
    overdue_tasks_count: 0,
  });
  const [filters, setFilters] = useState({ category: "", area: "", priority: "" });
  const [fixedExpenseOptions, setFixedExpenseOptions] = useState([]);
  const [productOptions, setProductOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [formData, setFormData] = useState(() => createInitialFormData());
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);

  const today = getTodayDateInput();
  const rangeStart = formatDateInput(addDays(new Date(), -30));
  const rangeEnd = formatDateInput(addDays(new Date(), 7));

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [taskData, occurrenceData, fixedExpenseData, productData, insightsData] = await Promise.all([
        listRecurringTasks(filters),
        listTaskOccurrences(rangeStart, rangeEnd, undefined, filters),
        listFixedExpenses(),
        listProducts(),
        getHouseholdInsights(rangeStart, rangeEnd, filters),
      ]);
      setRecurringTasks(taskData || []);
      setOccurrences(occurrenceData || []);
      setFixedExpenseOptions(fixedExpenseData || []);
      setProductOptions(productData || []);
      setInsights(insightsData || {
        weekly_completion: [],
        most_postponed_tasks: [],
        recurring_overdue_tasks: [],
        weekly_estimated_minutes: 0,
        overdue_tasks_count: 0,
      });
    } catch (error) {
      setMessage(error.message);
      setIsError(true);
      setRecurringTasks([]);
      setOccurrences([]);
      setFixedExpenseOptions([]);
      setProductOptions([]);
      setInsights({
        weekly_completion: [],
        most_postponed_tasks: [],
        recurring_overdue_tasks: [],
        weekly_estimated_minutes: 0,
        overdue_tasks_count: 0,
      });
    } finally {
      setLoading(false);
    }
  }, [filters, rangeEnd, rangeStart]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData((prev) => {
      const nextData = {
        ...prev,
        [name]: type === "checkbox" ? checked : value,
      };

      if (name === "frequency_type") {
        if (value === "weekly") {
          nextData.day_of_month = 1;
        }
        if (value === "monthly") {
          nextData.weekday = 0;
        }
      }

      if (name === "integration_kind") {
        nextData.linked_fixed_expense = "";
        nextData.linked_product = "";
      }

      if (["interval", "weekday", "day_of_month"].includes(name)) {
        nextData[name] = Number(value);
      }

      return nextData;
    });
  };

  const handleFilterChange = (event) => {
    const { name, value } = event.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleResetFilters = () => {
    setFilters({ category: "", area: "", priority: "" });
  };

  const openTaskModal = () => {
    setMessage("");
    setIsError(false);
    setIsTaskModalOpen(true);
  };

  const closeTaskModal = () => {
    setIsTaskModalOpen(false);
    setMessage("");
    setIsError(false);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    setIsError(false);

    try {
      const payload = {
        ...formData,
        interval: Number(formData.interval),
        estimated_minutes: Number(formData.estimated_minutes),
        integration_kind: formData.integration_kind || "",
        linked_fixed_expense:
          formData.integration_kind === "fixed_expense" && formData.linked_fixed_expense
            ? Number(formData.linked_fixed_expense)
            : null,
        linked_product:
          ["product_restock", "product_expiry"].includes(formData.integration_kind) && formData.linked_product
            ? Number(formData.linked_product)
            : null,
        weekday: formData.frequency_type === "weekly" ? Number(formData.weekday) : null,
        day_of_month: formData.frequency_type === "monthly" ? Number(formData.day_of_month) : null,
      };
      await createRecurringTask(payload);
      setFormData(createInitialFormData());
      setIsTaskModalOpen(false);
      await loadData();
    } catch (error) {
      setMessage(error.message);
      setIsError(true);
    }
  };

  const handleOccurrenceAction = async (occurrenceId, action) => {
    setMessage("");
    setIsError(false);
    setIsActing(true);

    try {
      if (action === "complete") {
        await completeTaskOccurrence(occurrenceId);
      } else if (action === "skip") {
        await skipTaskOccurrence(occurrenceId);
      } else if (action === "reopen") {
        await reopenTaskOccurrence(occurrenceId);
      }

      await loadData();
    } catch (error) {
      setMessage(error.message);
      setIsError(true);
    } finally {
      setIsActing(false);
    }
  };

  const agendaBuckets = getHouseholdAgendaBuckets(occurrences, today);

  return {
    recurringTasks,
    occurrences,
    insights,
    filters,
    categoryOptions,
    areaOptions,
    priorityOptions,
    integrationOptions: HOUSEHOLD_INTEGRATION_OPTIONS,
    fixedExpenseOptions,
    productOptions,
    todayOccurrences: agendaBuckets.today,
    upcomingOccurrences: agendaBuckets.upcoming,
    overdueOccurrences: agendaBuckets.overdue,
    resolvedOccurrences: agendaBuckets.resolvedRecent,
    loading,
    isActing,
    isTaskModalOpen,
    formData,
    message,
    isError,
    today,
    rangeStart,
    rangeEnd,
    handleChange,
    handleFilterChange,
    handleResetFilters,
    handleSubmit,
    handleOccurrenceAction,
    openTaskModal,
    closeTaskModal,
    refreshData: loadData,
  };
}