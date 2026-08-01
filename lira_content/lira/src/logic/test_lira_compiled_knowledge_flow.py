import json
import zlib
from pathlib import Path

import numpy as np
import pytest

from .lira_binary import LiraBinary
from .lira_knowledge_compiler import KnowledgeCompiler, KnowledgePayloadIntegrityError
from .lira_open_injection import (
    KnowledgeEntry,
    KnowledgeIntegrityError,
    OpenInjectionProtocol,
    SchemaValidationError,
    _content_hash,
)


def make_container(path: Path) -> LiraBinary:
    return LiraBinary.create(path, {"layer.weight": np.ones((2, 2), dtype=np.float32)})


def inject_public_and_private(oip: OpenInjectionProtocol) -> tuple[str, str]:
    public = KnowledgeEntry(
        id="pub_python_generator",
        category="programacao/python",
        question="O que é um generator em Python?",
        answer="Uma função que usa yield para produzir valores sob demanda.",
        source_model="Claude",
        confidence=0.95,
        tags=["python", "iteradores"],
        evidence="PEP 255",
        scope="public",
        created_at=1234.5,
    )
    private = KnowledgeEntry(
        id="priv_user_pref",
        category="programacao/python",
        question="Qual estilo de resposta o usuário prefere?",
        answer="Respostas curtas com comandos de teste explícitos.",
        source_model="Claude",
        confidence=0.8,
        tags=["preferencias"],
        evidence="Preferência observada na conversa",
        scope="private",
        created_at=1235.5,
    )
    ids = oip.inject_batch([public, private])
    return ids[0], ids[1]


def compile_python(lb: LiraBinary, oip: OpenInjectionProtocol) -> dict:
    return KnowledgeCompiler(lb, n_features=32).compile_category("programacao/python", oip)


def test_inject_compile_read_search_and_markdown(tmp_path: Path) -> None:
    lb = make_container(tmp_path / "agent.lira")
    oip = OpenInjectionProtocol(lb)
    public_id, private_id = inject_public_and_private(oip)

    report = compile_python(lb, oip)
    assert report["n_examples"] == 2

    entries = oip.read_category("programacao/python")
    assert {e["id"] for e in entries} == {public_id, private_id}
    public = next(e for e in entries if e["id"] == public_id)
    assert public["question"] == "O que é um generator em Python?"
    assert public["tags"] == ["python", "iteradores"]
    assert public["evidence"] == "PEP 255"
    assert public["created_at"] == 1234.5
    assert public["scope"] == "public"

    results = oip.search("yield")
    assert [r["id"] for r in results] == [public_id]
    markdown = oip.export_markdown("programacao/python")
    assert "**P:** O que é um generator em Python?" in markdown
    assert "**R:** Uma função que usa yield" in markdown
    lb.close()


def test_export_jsonl_after_compile_is_valid_reinjectable_and_respects_privacy(tmp_path: Path) -> None:
    lb = make_container(tmp_path / "agent.lira")
    oip = OpenInjectionProtocol(lb)
    public_id, private_id = inject_public_and_private(oip)
    compile_python(lb, oip)

    public_jsonl = tmp_path / "public.lkif.jsonl"
    oip.export_jsonl(public_jsonl)
    public_lines = [json.loads(line) for line in public_jsonl.read_text(encoding="utf-8").splitlines()[1:]]
    assert [e["id"] for e in public_lines] == [public_id]
    assert all({"category", "question", "answer", "scope"} <= set(e) for e in public_lines)

    all_jsonl = tmp_path / "all.lkif.jsonl"
    oip.export_jsonl(all_jsonl, include_private=True)
    all_lines = [json.loads(line) for line in all_jsonl.read_text(encoding="utf-8").splitlines()[1:]]
    assert {e["id"] for e in all_lines} == {public_id, private_id}

    lb2 = make_container(tmp_path / "other.lira")
    oip2 = OpenInjectionProtocol(lb2)
    imported = oip2.import_jsonl(all_jsonl)
    assert set(imported) == {public_id, private_id}
    assert len(oip2.read_category("programacao/python")) == 2
    lb.close()
    lb2.close()


def test_external_content_hash_is_recomputed_and_validated(tmp_path: Path) -> None:
    good = {
        "id": "hash_ok",
        "category": "fisica",
        "question": "O que é inércia?",
        "answer": "Tendência de manter o estado de movimento.",
        "source_model": "Claude",
    }
    good["content_hash"] = _content_hash(good["category"], good["question"], good["answer"])
    bad = dict(good, id="hash_bad", content_hash="0" * 64)

    lb = make_container(tmp_path / "agent.lira")
    oip = OpenInjectionProtocol(lb)
    ok_path = tmp_path / "ok.jsonl"
    ok_path.write_text(json.dumps(good, ensure_ascii=False) + "\n", encoding="utf-8")
    assert oip.import_jsonl(ok_path) == ["hash_ok"]

    bad_path = tmp_path / "bad.jsonl"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(SchemaValidationError, match="Linha 1: content_hash inválido"):
        oip.import_jsonl(bad_path)
    lb.close()


def test_jsonl_rejects_fields_outside_schema(tmp_path: Path) -> None:
    entry = {
        "category": "fisica",
        "question": "Q",
        "answer": "A",
        "source_model": "Claude",
        "extra": "not allowed",
    }
    lb = make_container(tmp_path / "agent.lira")
    oip = OpenInjectionProtocol(lb)
    path = tmp_path / "extra.jsonl"
    path.write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(SchemaValidationError, match="Campos não permitidos: extra"):
        oip.import_jsonl(path)
    lb.close()


def test_corrupted_compiled_payload_fails_before_decompress(tmp_path: Path) -> None:
    path = tmp_path / "agent.lira"
    lb = make_container(path)
    oip = OpenInjectionProtocol(lb)
    inject_public_and_private(oip)
    compile_python(lb, oip)
    module = lb._metadata["modules"]["knowledge_adapter::programacao/python"]
    offset = module["metadata"]["knowledge_payload_offset"]
    lb.close()

    with open(path, "r+b") as f:
        f.seek(offset)
        b = f.read(1)
        f.seek(offset)
        f.write(bytes([b[0] ^ 0xFF]))

    lb2 = LiraBinary(path)
    oip2 = OpenInjectionProtocol(lb2)
    with pytest.raises(KnowledgeIntegrityError, match="Hash do payload"):
        oip2.read_category("programacao/python")
    with pytest.raises(KnowledgePayloadIntegrityError, match="hash do payload"):
        KnowledgeCompiler(lb2, n_features=32).query("programacao/python", "generator")
    lb2.close()


def test_incremental_force_recompile_and_mixed_category(tmp_path: Path) -> None:
    lb = make_container(tmp_path / "agent.lira")
    oip = OpenInjectionProtocol(lb)
    inject_public_and_private(oip)
    first = compile_python(lb, oip)
    size_after_first = lb.path.stat().st_size

    new_id = oip.inject(
        category="programacao/python",
        question="Para que serve o GIL?",
        answer="Ele limita a execução simultânea de bytecode Python por threads.",
        source_model="GPT",
        tags=["python", "threads"],
    )
    mixed = oip.read_category("programacao/python")
    assert {e["id"] for e in mixed} >= {new_id, "pub_python_generator"}

    second = compile_python(lb, oip)
    assert second["n_novas_entradas"] == 1
    assert second["n_reaproveitadas"] == 2
    forced = KnowledgeCompiler(lb, n_features=32).compile_category(
        "programacao/python", oip, force_recompile=True
    )
    assert forced["n_novas_entradas"] == 0
    assert forced["n_reaproveitadas"] == 3
    assert lb.path.stat().st_size <= size_after_first + 8192
    assert forced["storage_compaction"]["after"]["bytes_orfaos"] == 0
    lb.close()


def test_old_payload_without_new_fields_can_be_hydrated(tmp_path: Path) -> None:
    lb = make_container(tmp_path / "agent.lira")
    oip = OpenInjectionProtocol(lb)
    public_id, _ = inject_public_and_private(oip)
    compile_python(lb, oip)

    module = lb._metadata["modules"]["knowledge_adapter::programacao/python"]
    old_payload = [
        {
            "id": public_id,
            "question": "O que é um generator em Python?",
            "answer": "Uma função que usa yield para produzir valores sob demanda.",
            "source_model": "Claude",
            "confidence": 0.95,
            "content_hash": _content_hash(
                "programacao/python",
                "O que é um generator em Python?",
                "Uma função que usa yield para produzir valores sob demanda.",
            ),
            "scope": "public",
        }
    ]
    raw = zlib.compress(json.dumps(old_payload, ensure_ascii=False).encode("utf-8"), level=9)
    offset, length = lb._append_raw(raw)
    new_meta = json.loads(json.dumps(lb._metadata))
    mod_meta = new_meta["modules"]["knowledge_adapter::programacao/python"]["metadata"]
    mod_meta["knowledge_payload_offset"] = offset
    mod_meta["knowledge_payload_length"] = length
    mod_meta["knowledge_payload_sha256"] = __import__("hashlib").sha256(raw).hexdigest()
    mod_meta["answer_order"] = [public_id]
    new_meta["knowledge"]["programacao/python"] = [new_meta["knowledge"]["programacao/python"][0]]
    lb._commit(new_meta)

    hydrated = oip.read_category("programacao/python")
    assert hydrated[0]["category"] == "programacao/python"
    assert hydrated[0]["tags"] == []
    assert hydrated[0]["evidence"] is None
    lb.close()


def test_query_returns_matching_id_answer_and_vector_order(tmp_path: Path) -> None:
    lb = make_container(tmp_path / "agent.lira")
    oip = OpenInjectionProtocol(lb)
    inject_public_and_private(oip)
    compile_python(lb, oip)

    result = KnowledgeCompiler(lb, n_features=32).query("programacao/python", "generator", top_k=1)[0]
    assert result["id"] == result["answer_id"]
    entry = next(e for e in oip.read_category("programacao/python") if e["id"] == result["id"])
    assert result["answer"] == entry["answer"]

    new_meta = json.loads(json.dumps(lb._metadata))
    new_meta["modules"]["knowledge_adapter::programacao/python"]["metadata"]["answer_order"] = list(reversed(
        new_meta["modules"]["knowledge_adapter::programacao/python"]["metadata"]["answer_order"]
    ))
    lb._commit(new_meta)
    with pytest.raises(KnowledgePayloadIntegrityError, match="answer_order diverge"):
        KnowledgeCompiler(lb, n_features=32).query("programacao/python", "generator", top_k=1)
    lb.close()
