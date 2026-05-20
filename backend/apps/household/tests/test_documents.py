import pytest

from apps.household.models import Document

DOCS_BASE = "/api/v1/documents/"


@pytest.fixture
def doc(db):
    return Document.objects.create(title="Manual lavadora", doc_type="manual")


# ---------------------------------------------------------------------------
# Lista y filtros
# ---------------------------------------------------------------------------

class TestDocumentList:
    def test_lista_vacia(self, api):
        response = api.get(DOCS_BASE)
        assert response.status_code == 200
        assert response.data["results"] == []

    def test_lista_documentos(self, api, doc):
        response = api.get(DOCS_BASE)
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filtra_por_doc_type(self, api):
        Document.objects.create(title="Nota rápida", doc_type="note")
        Document.objects.create(title="Garantía TV", doc_type="warranty")
        response = api.get(DOCS_BASE, {"doc_type": "warranty"})
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["doc_type"] == "warranty"

    def test_filtra_por_entity_type(self, api):
        Document.objects.create(title="Doc producto", entity_type="product", entity_id=5)
        Document.objects.create(title="General", entity_type="general")
        response = api.get(DOCS_BASE, {"entity_type": "product"})
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["entity_id"] == 5


# ---------------------------------------------------------------------------
# Creación
# ---------------------------------------------------------------------------

class TestDocumentCreate:
    def test_crea_nota_minima(self, api):
        response = api.post(DOCS_BASE, {"title": "Nota"}, format="json")
        assert response.status_code == 201
        assert response.data["doc_type"] == "note"
        assert response.data["entity_type"] == "general"

    def test_crea_garantia_completa(self, api):
        payload = {
            "title": "Garantia TV",
            "doc_type": "warranty",
            "content": "2 años de garantia.",
            "url": "https://ejemplo.com/garantia.pdf",
            "entity_type": "product",
            "entity_id": 3,
            "expires_at": "2028-01-01",
        }
        response = api.post(DOCS_BASE, payload, format="json")
        assert response.status_code == 201
        assert response.data["expires_at"] == "2028-01-01"
        assert response.data["entity_id"] == 3

    def test_crea_comprobante_con_url(self, api):
        payload = {"title": "Factura luz", "doc_type": "receipt", "url": "https://ejemplo.com/factura.pdf"}
        response = api.post(DOCS_BASE, payload, format="json")
        assert response.status_code == 201
        assert response.data["url"] == "https://ejemplo.com/factura.pdf"

    def test_title_requerido(self, api):
        response = api.post(DOCS_BASE, {"doc_type": "note"}, format="json")
        assert response.status_code == 400

    def test_url_invalida_rechazada(self, api):
        response = api.post(DOCS_BASE, {"title": "Test", "url": "no-es-una-url"}, format="json")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Actualización y eliminación
# ---------------------------------------------------------------------------

class TestDocumentUpdate:
    def test_actualiza_titulo(self, api, doc):
        response = api.patch(f"{DOCS_BASE}{doc.id}/", {"title": "Actualizado"}, format="json")
        assert response.status_code == 200
        assert response.data["title"] == "Actualizado"

    def test_actualiza_content(self, api, doc):
        response = api.patch(f"{DOCS_BASE}{doc.id}/", {"content": "Nueva nota."}, format="json")
        assert response.status_code == 200
        assert response.data["content"] == "Nueva nota."

    def test_elimina_documento(self, api, doc):
        response = api.delete(f"{DOCS_BASE}{doc.id}/")
        assert response.status_code == 204
        assert not Document.objects.filter(id=doc.id).exists()

    def test_detalle_documento(self, api, doc):
        response = api.get(f"{DOCS_BASE}{doc.id}/")
        assert response.status_code == 200
        assert response.data["id"] == doc.id

    def test_not_found(self, api):
        response = api.get(f"{DOCS_BASE}9999/")
        assert response.status_code == 404
