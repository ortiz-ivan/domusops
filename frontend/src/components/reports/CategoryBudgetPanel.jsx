import { useState } from "react";
import { useInventoryContext, useOrchestratorContext } from "../../context/AppContext.jsx";
import { formatCompactGuarani } from "./utils.js";

const BUCKETS = [
  { key: "needs", label: "Necesidades" },
  { key: "wants", label: "Deseos" },
  { key: "savings", label: "Ahorro / Deuda" },
];

export function CategoryBudgetPanel({ summary }) {
  const { inventorySettings } = useInventoryContext();
  const { saveSettings } = useOrchestratorContext();
  const [editing, setEditing] = useState(null); // { category, value }
  const [saving, setSaving] = useState(false);

  const breakdown = summary.category_breakdown ?? [];
  const targets = summary.rule_50_30_20?.targets ?? {};

  function startEdit(cat) {
    setEditing({ category: cat.category, value: cat.budget != null ? String(cat.budget) : "" });
  }

  async function handleSave() {
    if (!editing) return;
    setSaving(true);
    try {
      const raw = editing.value.trim();
      const newBudget = raw === "" ? null : parseFloat(raw);
      const updatedCategories = (inventorySettings.categories ?? []).map((cat) =>
        cat.value === editing.category
          ? { ...cat, monthly_budget: newBudget && newBudget > 0 ? newBudget : null }
          : cat
      );
      await saveSettings({ ...inventorySettings, categories: updatedCategories });
      setEditing(null);
    } finally {
      setSaving(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") setEditing(null);
  }

  return (
    <article className="panel reports-panel reports-panel-wide">
      <div className="panel-title">
        <div>
          <h3>Presupuesto por categoría</h3>
          <p>Gasto real vs. límite mensual. Haz clic en el monto presupuestado para editarlo.</p>
        </div>
      </div>

      <div className="category-budget-grid">
        {BUCKETS.map((bucket) => {
          const categories = breakdown.filter((c) => c.budget_bucket === bucket.key);
          const bucketActual = categories.reduce((sum, c) => sum + c.actual, 0);
          const bucketTarget = Number(targets[bucket.key] ?? 0);
          const isOver = bucketActual > bucketTarget && bucketTarget > 0;
          const statusClass = bucketTarget === 0 ? "neutral" : isOver ? "danger" : "success";
          const maxActual = Math.max(...categories.map((c) => c.actual), 1);

          return (
            <div key={bucket.key} className="category-budget-bucket">
              <div className="category-budget-bucket-header">
                <div className="category-budget-bucket-title">
                  <strong>{bucket.label}</strong>
                  <span className={`budget-rule-status ${statusClass}`}>
                    {bucketTarget === 0 ? "Sin meta" : isOver ? "Excedido" : "En rango"}
                  </span>
                </div>
                <div className="category-budget-amounts">
                  <span>{formatCompactGuarani(bucketActual)}</span>
                  {bucketTarget > 0 && (
                    <small>meta {formatCompactGuarani(bucketTarget)}</small>
                  )}
                </div>
              </div>

              {categories.length === 0 ? (
                <p className="empty-report">Sin gastos registrados este mes.</p>
              ) : (
                <div className="category-budget-rows">
                  {categories.map((cat) => {
                    const hasBudget = cat.budget != null && cat.budget > 0;
                    const isEditingThis = editing?.category === cat.category;
                    const isOverBudget = hasBudget && cat.actual > cat.budget;
                    const pct = hasBudget
                      ? Math.min((cat.actual / cat.budget) * 100, 100)
                      : Math.max(4, (cat.actual / maxActual) * 100);

                    return (
                      <div key={cat.category} className="category-budget-row">
                        <span className="category-budget-name">{cat.label}</span>

                        {isEditingThis ? (
                          <div className="category-budget-edit-row">
                            <input
                              type="number"
                              className="category-budget-input"
                              value={editing.value}
                              onChange={(e) => setEditing({ ...editing, value: e.target.value })}
                              onKeyDown={handleKeyDown}
                              autoFocus
                              min="0"
                              placeholder="Sin límite"
                            />
                            <button
                              className="cb-edit-confirm"
                              onClick={handleSave}
                              disabled={saving}
                              title="Guardar"
                            >
                              ✓
                            </button>
                            <button
                              className="cb-edit-cancel"
                              onClick={() => setEditing(null)}
                              title="Cancelar"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <div
                            className={`category-budget-bar-track${hasBudget ? " has-budget" : ""}`}
                            title={hasBudget ? `${Math.round(pct)}% del presupuesto` : ""}
                          >
                            <div
                              className={`category-budget-bar-fill${isOverBudget ? " over" : ""}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        )}

                        <div className="category-budget-meta">
                          <span className={`category-budget-amount${isOverBudget ? " text-danger" : ""}`}>
                            {formatCompactGuarani(cat.actual)}
                          </span>
                          {!isEditingThis && (
                            hasBudget ? (
                              <button
                                className="cb-budget-btn"
                                onClick={() => startEdit(cat)}
                                title="Editar presupuesto"
                              >
                                / {formatCompactGuarani(cat.budget)}
                              </button>
                            ) : (
                              <button
                                className="cb-budget-btn muted"
                                onClick={() => startEdit(cat)}
                                title="Fijar presupuesto"
                              >
                                + límite
                              </button>
                            )
                          )}
                          {hasBudget && !isEditingThis && (
                            <small className={isOverBudget ? "text-danger" : "text-muted"}>
                              {isOverBudget
                                ? `+${formatCompactGuarani(Math.abs(cat.remaining ?? 0))} exceso`
                                : `${formatCompactGuarani(cat.remaining ?? 0)} restante`}
                            </small>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </article>
  );
}
