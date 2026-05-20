import { useEffect, useState } from "react";
import { Edit2, ExternalLink, FileText, Plus, Trash2 } from "lucide-react";
import {
  createDocument,
  deleteDocument,
  listDocuments,
  updateDocument,
} from "../../api.js";

const DOC_TYPE_LABELS = {
  note: "Nota",
  receipt: "Comprobante",
  warranty: "Garantia",
  manual: "Manual",
  other: "Otro",
};

const ENTITY_TYPE_LABELS = {
  product: "Producto",
  fixed_expense: "Gasto fijo",
  recurring_task: "Tarea recurrente",
  general: "General",
};

const EMPTY_FORM = {
  title: "",
  doc_type: "note",
  content: "",
  url: "",
  entity_type: "general",
  entity_id: "",
  expires_at: "",
};

export function DocumentsView() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [message, setMessage] = useState(null);
  const [isError, setIsError] = useState(false);

  async function load() {
    try {
      const params = typeFilter ? { doc_type: typeFilter } : {};
      const data = await listDocuments(params);
      setDocuments(Array.isArray(data) ? data : []);
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [typeFilter]);

  function openCreate() {
    setFormData(EMPTY_FORM);
    setEditingId(null);
    setMessage(null);
    setIsFormOpen(true);
  }

  function openEdit(doc) {
    setFormData({
      title: doc.title,
      doc_type: doc.doc_type,
      content: doc.content || "",
      url: doc.url || "",
      entity_type: doc.entity_type,
      entity_id: doc.entity_id ?? "",
      expires_at: doc.expires_at || "",
    });
    setEditingId(doc.id);
    setMessage(null);
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setMessage(null);
  }

  function set(field) {
    return (e) => setFormData((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const payload = { ...formData };
    if (!payload.entity_id) delete payload.entity_id;
    if (!payload.expires_at) delete payload.expires_at;
    if (!payload.url) delete payload.url;
    try {
      if (editingId) {
        await updateDocument(editingId, payload);
      } else {
        await createDocument(payload);
      }
      closeForm();
      setMessage(editingId ? "Documento actualizado." : "Documento creado.");
      setIsError(false);
      load();
    } catch (err) {
      setMessage(err.message);
      setIsError(true);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteDocument(id);
      setMessage("Documento eliminado.");
      setIsError(false);
      load();
    } catch (err) {
      setMessage(err.message);
      setIsError(true);
    }
  }

  return (
    <section className="module-content fade-in">
      <div className="section-header">
        <div>
          <h2>Documentos</h2>
          <p>Notas, comprobantes, garantias y referencias del hogar.</p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={openCreate}>
          <Plus size={13} /> Nuevo
        </button>
      </div>

      {message && !isFormOpen && (
        <div className={`message${isError ? " error" : ""}`}>{message}</div>
      )}

      <div className="documents-filters">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="btn btn-secondary btn-sm"
          style={{ cursor: "pointer" }}
        >
          <option value="">Todos los tipos</option>
          {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <p style={{ color: "var(--text-soft)", padding: "1rem 0" }}>Cargando...</p>
      ) : documents.length === 0 ? (
        <div className="documents-empty">
          <FileText size={32} style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }} />
          <p style={{ color: "var(--text-soft)" }}>No hay documentos registrados.</p>
        </div>
      ) : (
        <div className="documents-list">
          {documents.map((doc) => (
            <div key={doc.id} className="document-card">
              <div className="document-card-header">
                <span className="badge badge-type">{DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}</span>
                <span className="document-title">{doc.title}</span>
                <div className="document-actions">
                  {doc.url && (
                    <a
                      href={doc.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary btn-sm"
                      title="Abrir enlace"
                    >
                      <ExternalLink size={13} />
                    </a>
                  )}
                  <button className="btn btn-secondary btn-sm" onClick={() => openEdit(doc)} title="Editar">
                    <Edit2 size={13} />
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(doc.id)} title="Eliminar">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

              {doc.content && (
                <p className="document-content">{doc.content}</p>
              )}

              <div className="document-meta">
                {doc.entity_type !== "general" && (
                  <span className="document-entity">
                    {ENTITY_TYPE_LABELS[doc.entity_type]}
                    {doc.entity_id ? ` #${doc.entity_id}` : ""}
                  </span>
                )}
                {doc.expires_at && (
                  <span className="document-expiry">Vence: {doc.expires_at}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {isFormOpen && (
        <div className="modal-overlay" onClick={closeForm}>
          <div className="modal-content compact" onClick={(e) => e.stopPropagation()}>
            <div className="modal-form-panel compact">
              <div className="modal-form-header">
                <h3>{editingId ? "Editar documento" : "Nuevo documento"}</h3>
              </div>
              {message && <div className={`message${isError ? " error" : ""}`}>{message}</div>}
              <form onSubmit={handleSubmit}>
                <div className="form-grid">
                  <label>
                    Titulo *
                    <input required value={formData.title} onChange={set("title")} />
                  </label>
                  <label>
                    Tipo
                    <select value={formData.doc_type} onChange={set("doc_type")}>
                      {Object.entries(DOC_TYPE_LABELS).map(([k, v]) => (
                        <option key={k} value={k}>{v}</option>
                      ))}
                    </select>
                  </label>
                  <label style={{ gridColumn: "1 / -1" }}>
                    Notas
                    <textarea
                      value={formData.content}
                      onChange={set("content")}
                      rows={3}
                      style={{ resize: "vertical" }}
                    />
                  </label>
                  <label style={{ gridColumn: "1 / -1" }}>
                    URL / Enlace
                    <input
                      type="url"
                      value={formData.url}
                      onChange={set("url")}
                      placeholder="https://..."
                    />
                  </label>
                  <label>
                    Vinculado a
                    <select value={formData.entity_type} onChange={set("entity_type")}>
                      {Object.entries(ENTITY_TYPE_LABELS).map(([k, v]) => (
                        <option key={k} value={k}>{v}</option>
                      ))}
                    </select>
                  </label>
                  {formData.entity_type !== "general" && (
                    <label>
                      ID de referencia
                      <input
                        type="number"
                        value={formData.entity_id}
                        onChange={set("entity_id")}
                        placeholder="ID"
                        min="1"
                      />
                    </label>
                  )}
                  <label>
                    Fecha de vencimiento
                    <input type="date" value={formData.expires_at} onChange={set("expires_at")} />
                  </label>
                </div>
                <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end", marginTop: "1rem" }}>
                  <button type="button" className="btn btn-secondary" onClick={closeForm}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">
                    {editingId ? "Guardar" : "Crear"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
