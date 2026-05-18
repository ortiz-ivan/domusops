import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  completeTaskOccurrence,
  listTaskOccurrences,
  reopenTaskOccurrence,
  skipTaskOccurrence,
} from "../../api.js";
import {
  getHouseholdTaskCategoryLabel,
  getHouseholdTaskPriorityLabel,
} from "../../constants/inventory.js";
import { getOccurrenceUrgency } from "./utils.js";

const MONTH_NAMES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];
const DAY_NAMES = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"];

function padTwo(n) {
  return String(n).padStart(2, "0");
}

function toDateStr(year, month, day) {
  return `${year}-${padTwo(month + 1)}-${padTwo(day)}`;
}

function daysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate();
}

function firstWeekdayOfMonth(year, month) {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1; // Mon=0 … Sun=6
}

function getTodayStr() {
  const d = new Date();
  return toDateStr(d.getFullYear(), d.getMonth(), d.getDate());
}

function OccurrenceStatusBadge({ occurrence }) {
  const urgency = getOccurrenceUrgency(occurrence);
  const label =
    occurrence.status === "done" ? "Hecha" :
    occurrence.status === "skipped" ? "Omitida" :
    urgency === "overdue" ? "Atrasada" :
    urgency === "today" ? "Hoy" : "Pendiente";
  const cls = urgency === "overdue" ? "low-stock" : "";
  return <span className={`badge ${cls}`}>{label}</span>;
}

function DayDetail({ dateStr, occurrences, fixedExpenses, onAction, isActing, todayStr }) {
  const [day, month, year] = (() => {
    const parts = dateStr.split("-");
    return [Number(parts[2]), Number(parts[1]) - 1, Number(parts[0])];
  })();

  const dayOccurrences = occurrences.filter((o) => o.due_date === dateStr);
  const dayExpenses = fixedExpenses.filter((e) => e.next_due_date === dateStr);
  const hasContent = dayOccurrences.length > 0 || dayExpenses.length > 0;

  return (
    <div className="cal-day-detail">
      <div className="cal-detail-header">
        <h4>
          {day} de {MONTH_NAMES[month]} {year}
          {dateStr === todayStr ? " — Hoy" : ""}
        </h4>
      </div>

      {!hasContent && (
        <p className="cal-empty">Sin eventos para este día.</p>
      )}

      {dayOccurrences.length > 0 && (
        <div className="cal-detail-section">
          <h5>Tareas</h5>
          <div className="income-list">
            {dayOccurrences.map((occ) => (
              <div className="income-row" key={occ.id}>
                <div>
                  <strong>{occ.recurring_task_title}</strong>
                  <p>{getHouseholdTaskCategoryLabel(occ.recurring_task_category)}</p>
                  <small>{getHouseholdTaskPriorityLabel(occ.recurring_task_priority)}</small>
                </div>
                <div className="fixed-expense-side">
                  <OccurrenceStatusBadge occurrence={occ} />
                  <div className="actions">
                    {occ.status === "pending" && (
                      <>
                        <button
                          className="btn btn-success"
                          type="button"
                          disabled={isActing}
                          onClick={() => onAction(occ.id, "complete")}
                        >
                          Hecha
                        </button>
                        <button
                          className="btn btn-outline"
                          type="button"
                          disabled={isActing}
                          onClick={() => onAction(occ.id, "skip")}
                        >
                          Omitir
                        </button>
                      </>
                    )}
                    {occ.status !== "pending" && (
                      <button
                        className="btn btn-secondary"
                        type="button"
                        disabled={isActing}
                        onClick={() => onAction(occ.id, "reopen")}
                      >
                        Reabrir
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {dayExpenses.length > 0 && (
        <div className="cal-detail-section">
          <h5>Gastos fijos con vencimiento</h5>
          <div className="income-list">
            {dayExpenses.map((exp) => (
              <div className="income-row" key={exp.id}>
                <div>
                  <strong>{exp.name}</strong>
                  <p>{exp.category}</p>
                </div>
                <div className="fixed-expense-side">
                  <strong>
                    {Number(exp.monthly_amount).toLocaleString("es-PY")} Gs.
                  </strong>
                  <span className={`badge ${exp.monthly_payment_status === "pending" ? "low-stock" : ""}`}>
                    {exp.monthly_payment_status === "paid" ? "Pagado" : "Por pagar"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function CalendarView({ fixedExpenses = [], onAfterAction }) {
  const today = new Date();
  const todayStr = getTodayStr();

  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());
  const [occurrences, setOccurrences] = useState([]);
  const [selectedDay, setSelectedDay] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isActing, setIsActing] = useState(false);

  const fetchMonth = useCallback(async (year, month) => {
    setLoading(true);
    try {
      const total = daysInMonth(year, month);
      const from = `${year}-${padTwo(month + 1)}-01`;
      const to = `${year}-${padTwo(month + 1)}-${padTwo(total)}`;
      const data = await listTaskOccurrences(from, to);
      setOccurrences(data || []);
    } catch {
      setOccurrences([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMonth(viewYear, viewMonth);
    setSelectedDay(null);
  }, [viewYear, viewMonth, fetchMonth]);

  const goToPrevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1); }
    else setViewMonth((m) => m - 1);
  };

  const goToNextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1); }
    else setViewMonth((m) => m + 1);
  };

  const goToToday = () => {
    setViewYear(today.getFullYear());
    setViewMonth(today.getMonth());
    setSelectedDay(today.getDate());
  };

  const handleAction = async (occurrenceId, action) => {
    setIsActing(true);
    try {
      if (action === "complete") await completeTaskOccurrence(occurrenceId);
      else if (action === "skip") await skipTaskOccurrence(occurrenceId);
      else if (action === "reopen") await reopenTaskOccurrence(occurrenceId);

      await fetchMonth(viewYear, viewMonth);
      if (onAfterAction) onAfterAction();
    } finally {
      setIsActing(false);
    }
  };

  // Build event index: dateStr → { tasks[], expenses[] }
  const eventIndex = {};

  for (const occ of occurrences) {
    if (!eventIndex[occ.due_date]) eventIndex[occ.due_date] = { tasks: [], expenses: [] };
    eventIndex[occ.due_date].tasks.push(occ);
  }
  for (const exp of fixedExpenses) {
    if (!exp.next_due_date) continue;
    const d = exp.next_due_date;
    if (!eventIndex[d]) eventIndex[d] = { tasks: [], expenses: [] };
    eventIndex[d].expenses.push(exp);
  }

  // Build grid cells
  const totalDays = daysInMonth(viewYear, viewMonth);
  const offset = firstWeekdayOfMonth(viewYear, viewMonth);
  const cells = Array(offset).fill(null);
  for (let d = 1; d <= totalDays; d++) cells.push(d);

  const selectedDateStr = selectedDay
    ? toDateStr(viewYear, viewMonth, selectedDay)
    : null;

  return (
    <article className="panel cal-panel">
      {/* Navigation header */}
      <div className="cal-header">
        <button className="btn btn-outline cal-nav-btn" type="button" onClick={goToPrevMonth} aria-label="Mes anterior">
          <ChevronLeft size={16} />
        </button>
        <div className="cal-header-center">
          <span className="cal-month-title">
            {MONTH_NAMES[viewMonth]} {viewYear}
          </span>
          <button className="cal-today-btn" type="button" onClick={goToToday}>
            Hoy
          </button>
        </div>
        <button className="btn btn-outline cal-nav-btn" type="button" onClick={goToNextMonth} aria-label="Mes siguiente">
          <ChevronRight size={16} />
        </button>
      </div>

      {loading ? (
        <p className="cal-loading">Cargando tareas del mes...</p>
      ) : (
        <>
          {/* Day-of-week headers */}
          <div className="cal-grid">
            {DAY_NAMES.map((d) => (
              <div key={d} className="cal-day-name">{d}</div>
            ))}

            {/* Day cells */}
            {cells.map((day, idx) => {
              if (day === null) {
                return <div key={`empty-${idx}`} className="cal-cell cal-cell-empty" />;
              }

              const dateStr = toDateStr(viewYear, viewMonth, day);
              const events = eventIndex[dateStr] || { tasks: [], expenses: [] };
              const isToday = dateStr === todayStr;
              const isSelected = day === selectedDay;
              const hasEvents = events.tasks.length > 0 || events.expenses.length > 0;

              const hasOverdue = events.tasks.some(
                (t) => t.status === "pending" && t.due_date < todayStr,
              );
              const hasPending = events.tasks.some(
                (t) => t.status === "pending" && t.due_date >= todayStr,
              );
              const hasDone = events.tasks.some((t) => t.status === "done");
              const hasSkipped = events.tasks.some((t) => t.status === "skipped");
              const hasUnpaidExpense = events.expenses.some(
                (e) => e.monthly_payment_status === "pending",
              );
              const hasPaidExpense = events.expenses.some(
                (e) => e.monthly_payment_status === "paid",
              );

              return (
                <div
                  key={dateStr}
                  role="button"
                  tabIndex={hasEvents ? 0 : -1}
                  aria-label={`${day} de ${MONTH_NAMES[viewMonth]}`}
                  aria-pressed={isSelected}
                  className={[
                    "cal-cell",
                    isToday ? "cal-cell-today" : "",
                    isSelected ? "cal-cell-selected" : "",
                    hasEvents ? "cal-cell-has-events" : "",
                  ].filter(Boolean).join(" ")}
                  onClick={() => hasEvents && setSelectedDay(isSelected ? null : day)}
                  onKeyDown={(e) => e.key === "Enter" && hasEvents && setSelectedDay(isSelected ? null : day)}
                >
                  <span className="cal-day-num">{day}</span>
                  {hasEvents && (
                    <div className="cal-dots">
                      {hasOverdue && <span className="cal-dot cal-dot-danger" title="Tarea atrasada" />}
                      {hasPending && <span className="cal-dot cal-dot-accent" title="Tarea pendiente" />}
                      {hasDone && <span className="cal-dot cal-dot-success" title="Tarea completada" />}
                      {hasSkipped && <span className="cal-dot cal-dot-muted" title="Tarea omitida" />}
                      {hasUnpaidExpense && <span className="cal-dot cal-dot-warning" title="Pago pendiente" />}
                      {hasPaidExpense && <span className="cal-dot cal-dot-success-soft" title="Pago realizado" />}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="cal-legend">
            <span><span className="cal-dot cal-dot-danger" />Tareas atrasadas</span>
            <span><span className="cal-dot cal-dot-accent" />Tareas pendientes</span>
            <span><span className="cal-dot cal-dot-success" />Completadas</span>
            <span><span className="cal-dot cal-dot-muted" />Omitidas</span>
            <span><span className="cal-dot cal-dot-warning" />Pago por vencer</span>
            <span><span className="cal-dot cal-dot-success-soft" />Pago realizado</span>
          </div>
        </>
      )}

      {/* Day detail panel */}
      {selectedDateStr && !loading && (
        <DayDetail
          dateStr={selectedDateStr}
          occurrences={occurrences}
          fixedExpenses={fixedExpenses}
          onAction={handleAction}
          isActing={isActing}
          todayStr={todayStr}
        />
      )}
    </article>
  );
}
