import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Link2 } from "lucide-react";
import {
  createMealPlan,
  deleteMealPlan,
  linkMealPlan,
  listMealPlans,
  unlinkMealPlan,
  updateMealPlan,
} from "../../api.js";

const MEAL_TIMES = [
  { key: "breakfast", label: "Desayuno" },
  { key: "lunch", label: "Almuerzo" },
  { key: "dinner", label: "Cena" },
  { key: "snack", label: "Merienda" },
];

const COMPANION = { lunch: "dinner", dinner: "lunch" };
const COMPANION_LABEL = { lunch: "la cena", dinner: "el almuerzo" };

const DAY_SHORT = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];
const MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function getMonday(from) {
  const d = new Date(from);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function toIso(date) {
  return date.toISOString().slice(0, 10);
}

function dayIndex(date) {
  const d = date.getDay();
  return d === 0 ? 6 : d - 1;
}

function formatWeekRange(monday) {
  const sunday = addDays(monday, 6);
  const sameMonth = monday.getMonth() === sunday.getMonth();
  if (sameMonth) {
    return `${monday.getDate()} – ${sunday.getDate()} ${MONTHS_ES[sunday.getMonth()]} ${sunday.getFullYear()}`;
  }
  return `${monday.getDate()} ${MONTHS_ES[monday.getMonth()]} – ${sunday.getDate()} ${MONTHS_ES[sunday.getMonth()]} ${sunday.getFullYear()}`;
}

export function MealPlanView() {
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()));
  const [meals, setMeals] = useState({});
  const [editingCell, setEditingCell] = useState(null);
  const [formName, setFormName] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [formShareOther, setFormShareOther] = useState(false);
  const [deleteLinked, setDeleteLinked] = useState(false);
  const [formError, setFormError] = useState(null);

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const fromDate = toIso(weekStart);
  const toDate = toIso(addDays(weekStart, 6));

  async function load() {
    try {
      const data = await listMealPlans({ from: fromDate, to: toDate });
      const map = {};
      for (const m of Array.isArray(data) ? data : []) {
        map[`${m.date}_${m.meal_time}`] = m;
      }
      setMeals(map);
    } catch {
      setMeals({});
    }
  }

  useEffect(() => {
    load();
  }, [fromDate]);

  function openCell(dateStr, mealTime) {
    const existing = meals[`${dateStr}_${mealTime}`] ?? null;
    setEditingCell({ date: dateStr, meal_time: mealTime, meal: existing });
    setFormName(existing?.name ?? "");
    setFormNotes(existing?.notes ?? "");
    setFormShareOther(!!existing?.linked_meal_id);
    setDeleteLinked(false);
    setFormError(null);
  }

  function closeCell() {
    setEditingCell(null);
    setFormError(null);
    setFormShareOther(false);
    setDeleteLinked(false);
  }

  const canShare = editingCell && COMPANION[editingCell.meal_time] !== undefined;
  const wasLinked = !!editingCell?.meal?.linked_meal_id;

  async function handleSave(e) {
    e.preventDefault();
    const { date, meal_time, meal } = editingCell;
    try {
      let savedMeal;
      if (meal) {
        savedMeal = await updateMealPlan(meal.id, { name: formName, notes: formNotes });
      } else {
        savedMeal = await createMealPlan({ date, meal_time, name: formName, notes: formNotes });
      }

      if (canShare) {
        if (formShareOther) {
          await linkMealPlan(savedMeal.id, COMPANION[meal_time]);
        } else if (wasLinked) {
          await unlinkMealPlan(savedMeal.id);
        }
      }

      closeCell();
      load();
    } catch (err) {
      setFormError(err.message);
    }
  }

  async function handleDelete() {
    try {
      const linkedId = editingCell.meal.linked_meal_id;
      if (deleteLinked && linkedId) {
        try {
          await deleteMealPlan(linkedId);
        } catch {}
      }
      await deleteMealPlan(editingCell.meal.id);
      closeCell();
      load();
    } catch (err) {
      setFormError(err.message);
    }
  }

  const mealTimeLabel = editingCell
    ? MEAL_TIMES.find((m) => m.key === editingCell.meal_time)?.label
    : "";

  return (
    <section className="module-content fade-in">
      <div className="section-header">
        <div>
          <h2>Menu semanal</h2>
          <p>Planificacion de comidas por semana. Haz clic en cualquier celda para agregar o editar.</p>
        </div>
        <div className="week-nav">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setWeekStart((d) => addDays(d, -7))}
            aria-label="Semana anterior"
          >
            <ChevronLeft size={15} />
          </button>
          <span className="week-nav-label">{formatWeekRange(weekStart)}</span>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setWeekStart((d) => addDays(d, 7))}
            aria-label="Semana siguiente"
          >
            <ChevronRight size={15} />
          </button>
        </div>
      </div>

      <div className="meal-plan-grid">
        <div className="meal-plan-header">
          <div className="meal-time-col" />
          {weekDays.map((day) => (
            <div key={toIso(day)} className="meal-day-header">
              <span className="meal-day-name">{DAY_SHORT[dayIndex(day)]}</span>
              <span className="meal-day-num">{day.getDate()}</span>
            </div>
          ))}
        </div>

        {MEAL_TIMES.map(({ key: mealTime, label }) => (
          <div key={mealTime} className="meal-plan-row">
            <div className="meal-time-col">{label}</div>
            {weekDays.map((day) => {
              const dateStr = toIso(day);
              const meal = meals[`${dateStr}_${mealTime}`];
              const isLinked = !!meal?.linked_meal_id;
              return (
                <button
                  key={dateStr}
                  className={`meal-cell${meal ? " meal-cell--filled" : " meal-cell--empty"}${isLinked ? " meal-cell--linked" : ""}`}
                  onClick={() => openCell(dateStr, mealTime)}
                  title={meal ? meal.name : `Agregar ${label.toLowerCase()}`}
                  type="button"
                >
                  {meal ? (
                    <>
                      <span className="meal-cell-name">{meal.name}</span>
                      {isLinked && <Link2 size={10} className="meal-cell-link-icon" />}
                    </>
                  ) : (
                    <span className="meal-cell-add">+</span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {editingCell && (
        <div className="modal-overlay" onClick={closeCell}>
          <div className="modal-content compact" onClick={(e) => e.stopPropagation()}>
            <div className="modal-form-panel compact">
              <div className="modal-form-header">
                <h3>
                  {mealTimeLabel} — {editingCell.date}
                </h3>
              </div>
              {formError && <div className="message error">{formError}</div>}
              <form onSubmit={handleSave}>
                <div className="form-grid">
                  <label style={{ gridColumn: "1 / -1" }}>
                    Comida *
                    <input
                      required
                      autoFocus
                      value={formName}
                      onChange={(e) => setFormName(e.target.value)}
                      placeholder="Ej: Pasta con tomate"
                    />
                  </label>
                  <label style={{ gridColumn: "1 / -1" }}>
                    Notas / Receta
                    <textarea
                      value={formNotes}
                      onChange={(e) => setFormNotes(e.target.value)}
                      rows={3}
                      placeholder="Ingredientes, preparacion..."
                      style={{ resize: "vertical" }}
                    />
                  </label>
                  {canShare && (
                    <label className="meal-share-toggle" style={{ gridColumn: "1 / -1" }}>
                      <input
                        type="checkbox"
                        checked={formShareOther}
                        onChange={(e) => setFormShareOther(e.target.checked)}
                      />
                      <Link2 size={13} />
                      Unificar con {COMPANION_LABEL[editingCell.meal_time]}
                    </label>
                  )}
                </div>
                <div className="meal-modal-actions">
                  {editingCell.meal && (
                    <div className="meal-delete-section">
                      {wasLinked && (
                        <label className="meal-delete-linked-toggle">
                          <input
                            type="checkbox"
                            checked={deleteLinked}
                            onChange={(e) => setDeleteLinked(e.target.checked)}
                          />
                          También eliminar {COMPANION_LABEL[editingCell.meal_time]}
                        </label>
                      )}
                      <button type="button" className="btn btn-danger" onClick={handleDelete}>
                        Eliminar
                      </button>
                    </div>
                  )}
                  <div className="meal-modal-right-actions">
                    <button type="button" className="btn btn-secondary" onClick={closeCell}>
                      Cancelar
                    </button>
                    <button type="submit" className="btn btn-primary">
                      Guardar
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
