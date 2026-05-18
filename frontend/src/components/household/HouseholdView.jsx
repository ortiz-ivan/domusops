import { useState } from "react";
import { CalendarDays, List } from "lucide-react";
import { CalendarView } from "./CalendarView.jsx";
import { HouseholdFiltersBar } from "./HouseholdFiltersBar.jsx";
import { HouseholdComplianceSection } from "./HouseholdComplianceSection.jsx";
import { HouseholdInsightsCards } from "./HouseholdInsightsCards.jsx";
import { HouseholdRiskSection } from "./HouseholdRiskSection.jsx";
import { RecurringTaskForm } from "./RecurringTaskForm.jsx";
import { RecurringTaskTemplatesSection } from "./RecurringTaskTemplatesSection.jsx";
import { HouseholdSummaryCards } from "./HouseholdSummaryCards.jsx";
import { TaskAgendaSection } from "./TaskAgendaSection.jsx";
import { useHouseholdViewController } from "./useHouseholdViewController.js";

export function HouseholdView() {
  const [viewMode, setViewMode] = useState("list");

  const {
    recurringTasks,
    insights,
    filters,
    categoryOptions,
    areaOptions,
    priorityOptions,
    integrationOptions,
    fixedExpenseOptions,
    productOptions,
    todayOccurrences,
    upcomingOccurrences,
    overdueOccurrences,
    resolvedOccurrences,
    loading,
    isActing,
    isTaskModalOpen,
    formData,
    message,
    isError,
    today,
    handleChange,
    handleFilterChange,
    handleResetFilters,
    handleSubmit,
    handleOccurrenceAction,
    openTaskModal,
    closeTaskModal,
    refreshData,
  } = useHouseholdViewController();

  return (
    <section className="module-content fade-in">
      <div className="section-header expenses-header">
        <div className="section-header-copy">
          <h2>Rutinas del hogar</h2>
          <p>Crea tareas semanales o mensuales y visualizalas en una agenda operativa basica.</p>
        </div>
        <div className="expenses-header-actions">
          <div className="view-toggle" role="group" aria-label="Modo de vista">
            <button
              className={`view-toggle-btn${viewMode === "list" ? " active" : ""}`}
              type="button"
              onClick={() => setViewMode("list")}
            >
              <List size={13} />
              Lista
            </button>
            <button
              className={`view-toggle-btn${viewMode === "calendar" ? " active" : ""}`}
              type="button"
              onClick={() => setViewMode("calendar")}
            >
              <CalendarDays size={13} />
              Calendario
            </button>
          </div>
          <button className="btn btn-primary" type="button" onClick={openTaskModal}>
            Nueva tarea recurrente
          </button>
        </div>
      </div>

      {isTaskModalOpen && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Nueva tarea recurrente"
          onClick={closeTaskModal}
        >
          <div className="modal-content compact" onClick={(event) => event.stopPropagation()}>
            <RecurringTaskForm
              formData={formData}
              message={message}
              isError={isError}
              categoryOptions={categoryOptions}
              areaOptions={areaOptions}
              priorityOptions={priorityOptions}
              integrationOptions={integrationOptions}
              fixedExpenseOptions={fixedExpenseOptions}
              productOptions={productOptions}
              onChange={handleChange}
              onSubmit={handleSubmit}
              onClose={closeTaskModal}
            />
          </div>
        </div>
      )}

      {loading ? (
        <article className="panel">
          <p>Cargando tareas recurrentes...</p>
        </article>
      ) : (
        <>
          <HouseholdSummaryCards
            overdueCount={overdueOccurrences.length}
            todayCount={todayOccurrences.length}
            upcomingCount={upcomingOccurrences.length}
          />

          <HouseholdInsightsCards
            weeklyEstimatedMinutes={insights.weekly_estimated_minutes}
            overdueTasksCount={insights.overdue_tasks_count}
            latestCompletionRate={insights.weekly_completion.at(-1)?.completion_rate || 0}
          />

          {viewMode === "list" && (
            <>
              <HouseholdFiltersBar
                filters={filters}
                categoryOptions={categoryOptions}
                areaOptions={areaOptions}
                priorityOptions={priorityOptions}
                onChange={handleFilterChange}
                onReset={handleResetFilters}
              />

              <div className="finance-grid">
                <RecurringTaskTemplatesSection recurringTasks={recurringTasks} />
                <HouseholdComplianceSection weeklyCompletion={insights.weekly_completion} />
                <HouseholdRiskSection
                  mostPostponedTasks={insights.most_postponed_tasks}
                  recurringOverdueTasks={insights.recurring_overdue_tasks}
                />
                <TaskAgendaSection
                  title="Atrasadas"
                  description="Lo pendiente con vencimiento previo a hoy debe salir primero."
                  occurrences={overdueOccurrences}
                  emptyMessage="No hay tareas atrasadas."
                  isActing={isActing}
                  onComplete={(id) => handleOccurrenceAction(id, "complete")}
                  onSkip={(id) => handleOccurrenceAction(id, "skip")}
                />
                <TaskAgendaSection
                  title="Hoy"
                  description={`Tareas con vencimiento para ${today}.`}
                  occurrences={todayOccurrences}
                  emptyMessage="No hay tareas previstas para hoy."
                  isActing={isActing}
                  onComplete={(id) => handleOccurrenceAction(id, "complete")}
                  onSkip={(id) => handleOccurrenceAction(id, "skip")}
                />
                <TaskAgendaSection
                  title="Proximos 7 dias"
                  description="Rutinas semanales o mensuales que ya conviene anticipar."
                  occurrences={upcomingOccurrences}
                  emptyMessage="No hay pendientes para la proxima semana."
                  isActing={isActing}
                  onComplete={(id) => handleOccurrenceAction(id, "complete")}
                  onSkip={(id) => handleOccurrenceAction(id, "skip")}
                />
                <TaskAgendaSection
                  title="Actividad reciente"
                  description="Desde aqui puedes reabrir tareas hechas u omitidas por error."
                  occurrences={resolvedOccurrences}
                  emptyMessage="Aun no hay actividad reciente para mostrar."
                  actionMode="resolved"
                  isActing={isActing}
                  onReopen={(id) => handleOccurrenceAction(id, "reopen")}
                />
              </div>
            </>
          )}

          {viewMode === "calendar" && (
            <div className="finance-grid">
              <CalendarView
                fixedExpenses={fixedExpenseOptions}
                onAfterAction={refreshData}
              />
            </div>
          )}
        </>
      )}
    </section>
  );
}