"""Testes do Protocolo de Injeção Aberta (LKIF)."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from lira_binary import LiraBinary
from lira_open_injection import (
    OpenInjectionProtocol,
    KnowledgeEntry,
    SchemaValidationError,
    lkif_json_schema,
)


@pytest.fixture
def container():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "agente.lira"
        base = {"layer.weight": np.ones((2, 2), dtype=np.float32)}
        lb = LiraBinary.create(path, base)
        yield lb
        lb.close()


def test_inject_and_read(container):
    oip = OpenInjectionProtocol(container)
    assert oip.read_category("fisica") == []

    entry_id = oip.inject(
        category="fisica",
        question="O que é inércia?",
        answer="A tendência de um corpo manter seu estado de repouso ou movimento.",
        source_model="Claude Sonnet 5",
        confidence=0.9,
    )
    assert entry_id
    entries = oip.read_category("fisica")
    assert len(entries) == 1
    assert entries[0]["source_model"] == "Claude Sonnet 5"
    assert "fisica" in oip.list_knowledge_categories()
    # a categoria também deve aparecer no índice geral de categorias
    assert "fisica" in container._metadata["categories"]


def test_deduplication_is_deterministic(container):
    oip = OpenInjectionProtocol(container)
    id1 = oip.inject(
        category="fisica",
        question="O que é inércia?",
        answer="A tendência de um corpo manter seu estado de repouso ou movimento.",
        source_model="Claude Sonnet 5",
    )
    # mesma pergunta/resposta (mesmo com espaços/maiúsculas diferentes),
    # fonte diferente -> não deve duplicar
    id2 = oip.inject(
        category="fisica",
        question="  O que é INÉRCIA?  ",
        answer="a tendência de um corpo manter seu estado de repouso ou movimento.",
        source_model="GPT",
    )
    assert id1 == id2
    assert len(oip.read_category("fisica")) == 1


def test_allow_duplicate_forces_new_entry(container):
    oip = OpenInjectionProtocol(container)
    oip.inject(category="fisica", question="Q", answer="A", source_model="Claude")
    oip.inject(category="fisica", question="Q", answer="A", source_model="Claude", allow_duplicate=True)
    assert len(oip.read_category("fisica")) == 2


def test_validation_rejects_missing_fields(container):
    oip = OpenInjectionProtocol(container)
    with pytest.raises(SchemaValidationError):
        oip.inject(category="fisica", question="", answer="A", source_model="Claude")
    with pytest.raises(SchemaValidationError):
        oip.inject(category="fisica", question="Q", answer="A", source_model="")
    with pytest.raises(SchemaValidationError):
        oip.inject(category="fisica", question="Q", answer="A", source_model="Claude", confidence=2.0)


def test_export_and_import_roundtrip(container):
    oip = OpenInjectionProtocol(container)
    oip.inject(category="fisica", question="Q1", answer="A1", source_model="Claude")
    oip.inject(category="quimica", question="Q2", answer="A2", source_model="Claude")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "export.lkif.jsonl"
        oip.export_jsonl(out_path)
        lines = out_path.read_text(encoding="utf-8").splitlines()
        assert json.loads(lines[0])["lkif_manifest"] is True
        assert len(lines) == 3  # manifesto + 2 entradas

        # cria um segundo container "vazio" e importa o conhecimento exportado
        path2 = Path(tmpdir) / "outro.lira"
        base = {"layer.weight": np.ones((2, 2), dtype=np.float32)}
        lb2 = LiraBinary.create(path2, base)
        oip2 = OpenInjectionProtocol(lb2)
        ids = oip2.import_jsonl(out_path)
        assert len(ids) == 2
        assert set(oip2.list_knowledge_categories()) == {"fisica", "quimica"}
        lb2.close()


def test_import_rejects_malformed_jsonl(container):
    oip = OpenInjectionProtocol(container)
    with tempfile.TemporaryDirectory() as tmpdir:
        bad = Path(tmpdir) / "bad.jsonl"
        bad.write_text("{ isso nao eh json valido", encoding="utf-8")
        with pytest.raises(Exception):
            oip.import_jsonl(bad)


def test_search(container):
    oip = OpenInjectionProtocol(container)
    oip.inject(category="fisica", question="O que é inércia?", answer="Resposta A", source_model="Claude")
    oip.inject(category="quimica", question="O que é um átomo?", answer="Resposta B", source_model="Claude")
    results = oip.search("inércia")
    assert len(results) == 1
    assert results[0]["category"] == "fisica"


def test_stats(container):
    oip = OpenInjectionProtocol(container)
    oip.inject(category="fisica", question="Q1", answer="A1", source_model="Claude")
    oip.inject(category="fisica", question="Q2", answer="A2", source_model="GPT")
    stats = oip.stats()
    assert stats["total_entries"] == 2
    assert stats["entries_by_source_model"] == {"Claude": 1, "GPT": 1}


def test_schema_has_required_fields():
    schema = lkif_json_schema()
    assert set(schema["required"]) == {"category", "question", "answer", "source_model"}


def test_knowledge_entry_from_dict_validates():
    with pytest.raises(SchemaValidationError):
        KnowledgeEntry.from_dict({"category": "fisica", "question": "Q", "answer": "A", "source_model": ""})


def test_persists_across_reopen():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "agente.lira"
        base = {"layer.weight": np.ones((2, 2), dtype=np.float32)}
        lb = LiraBinary.create(path, base)
        oip = OpenInjectionProtocol(lb)
        oip.inject(category="fisica", question="Q", answer="A", source_model="Claude")
        lb.close()

        lb2 = LiraBinary(path)
        oip2 = OpenInjectionProtocol(lb2)
        assert len(oip2.read_category("fisica")) == 1
        lb2.close()
