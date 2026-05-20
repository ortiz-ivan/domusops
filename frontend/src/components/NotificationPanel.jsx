import { useEffect, useRef, useState } from "react";
import { AlertCircle, Bell, Package, Wallet, X } from "lucide-react";

const LEVEL_CONFIG = {
  danger: { cls: "notif-danger", dot: "dot-danger" },
  warning: { cls: "notif-warning", dot: "dot-warning" },
  info: { cls: "notif-info", dot: "dot-info" },
};

const CATEGORY_ICON = {
  tasks: <AlertCircle size={14} />,
  stock: <Package size={14} />,
  fixed: <Wallet size={14} />,
};

function NotificationGroup({ group }) {
  const { cls, dot } = LEVEL_CONFIG[group.level] ?? LEVEL_CONFIG.info;
  return (
    <div className={`notif-group ${cls}`}>
      <div className="notif-group-header">
        <span className={`notif-dot ${dot}`} />
        <span className="notif-group-icon">{CATEGORY_ICON[group.category]}</span>
        <strong className="notif-group-title">{group.title}</strong>
        <span className="notif-group-count">{group.count}</span>
      </div>
      {group.items.length > 0 && (
        <ul className="notif-items">
          {group.items.map((item, i) => (
            <li key={i} className="notif-item">{item}</li>
          ))}
          {group.overflow > 0 && (
            <li className="notif-item notif-overflow">+{group.overflow} más</li>
          )}
        </ul>
      )}
    </div>
  );
}

const MAX_ITEMS = 3;

export function NotificationPanel({ groups }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const visibleGroups = groups.filter((g) => g.count > 0);
  const totalCount = visibleGroups.reduce((acc, g) => acc + g.count, 0);
  const hasDanger = visibleGroups.some((g) => g.level === "danger");

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (!ref.current?.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <div className="notification-bell" ref={ref}>
      <button
        type="button"
        className={`bell-btn ${hasDanger ? "bell-danger" : totalCount > 0 ? "bell-warning" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notificaciones${totalCount > 0 ? ` (${totalCount})` : ""}`}
        aria-expanded={open}
      >
        <Bell size={16} />
        {totalCount > 0 && (
          <span className={`bell-badge ${hasDanger ? "badge-danger" : "badge-warning"}`} aria-hidden="true">
            {totalCount > 99 ? "99+" : totalCount}
          </span>
        )}
      </button>

      {open && (
        <div className="notification-panel" role="dialog" aria-label="Panel de notificaciones">
          <div className="notif-panel-header">
            <span>Notificaciones</span>
            <button type="button" className="notif-close" onClick={() => setOpen(false)} aria-label="Cerrar">
              <X size={14} />
            </button>
          </div>

          <div className="notif-panel-body">
            {visibleGroups.length === 0 ? (
              <p className="notif-empty">Sin alertas activas</p>
            ) : (
              visibleGroups.map((group) => (
                <NotificationGroup key={group.category} group={group} />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function buildNotificationGroups({ overdueOccurrences, criticalItems, dueSoonFixedExpenses }) {
  return [
    {
      level: "danger",
      category: "tasks",
      title: "Tareas atrasadas",
      count: overdueOccurrences.length,
      items: overdueOccurrences.slice(0, MAX_ITEMS).map((o) => o.recurring_task_title ?? "Tarea sin nombre"),
      overflow: Math.max(0, overdueOccurrences.length - MAX_ITEMS),
    },
    {
      level: "danger",
      category: "stock",
      title: "Stock critico",
      count: criticalItems.length,
      items: criticalItems.slice(0, MAX_ITEMS).map((p) => `${p.name} (${p.stock} ${p.unit ?? "u."})`),
      overflow: Math.max(0, criticalItems.length - MAX_ITEMS),
    },
    {
      level: "warning",
      category: "fixed",
      title: "Gastos fijos por vencer",
      count: dueSoonFixedExpenses.length,
      items: dueSoonFixedExpenses.slice(0, MAX_ITEMS).map((e) => `${e.name} — ${e.daysLeft === 0 ? "hoy" : `${e.daysLeft} día${e.daysLeft !== 1 ? "s" : ""}`}`),
      overflow: Math.max(0, dueSoonFixedExpenses.length - MAX_ITEMS),
    },
  ];
}
