"""Open Injection Protocol (OIP) / LKIF — Lira Knowledge Injection Format.

Este módulo é a contraparte "aberta e legível" do `.lira` binário
(`lira_binary.py`). Enquanto o container binário guarda pesos, deltas e
LoRAs em bytes crus (rápido, mas opaco — como um `.safetensors`), o
LKIF guarda **conhecimento declarativo** — pares pergunta/resposta,
categorizados semanticamente, em JSON puro. Qualquer modelo (Claude,
GPT, Gemini, Llama, o que for) consegue:

1. **Ler** o que já existe em cada categoria antes de decidir o que
   ensinar (evita redundância — item 3 da especificação: "Transparência
   para Agentes").
2. **Escrever** conhecimento novo seguindo um schema aberto e simples
   (sem SDK, sem binário, sem dependência de nenhum vendor).
3. **Auditar** quem ensinou o quê, quando, e com que confiança — cada
   entrada carrega proveniência (`source_model`) e não pode ser editada
   silenciosamente (é append-only e hasheada).

Diferente do `safetensors`, que só descreve tensores, o LKIF descreve
**conhecimento em linguagem natural organizado por categoria semântica**
— é o "dicionário comum de aprendizado" que faz vários modelos
convergirem para a mesma organização de conteúdo dentro do mesmo
arquivo `.lira`.

Formato de intercâmbio (o que um outro modelo de fato lê/escreve):
    Um arquivo `.jsonl` (uma entrada JSON por linha, sem vírgulas entre
    linhas, sem envelope binário) — o formato mais simples possível de
    gerar por qualquer LLM via texto puro. Ver `lkif_schema.json`
    (gerado por `write_schema()`) para o schema formal.

Este módulo NÃO reimplementa o container binário: ele decora uma
instância de `LiraBinary` (ou qualquer objeto com `._metadata` e
`._commit`) adicionando uma seção `knowledge` à metadata, do mesmo
jeito que `memory`/`skills`/`experiences` já existem.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
import uuid
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

LKIF_FORMAT_VERSION = "1.0"


class OpenInjectionError(Exception):
    """Base class for LKIF-related errors."""


class SchemaValidationError(OpenInjectionError):
    """Raised when a knowledge entry does not conform to the LKIF schema."""


class DuplicateKnowledgeError(OpenInjectionError):
    """Raised (optionally) when an entry looks like a near-duplicate of an existing one."""


class KnowledgeIntegrityError(OpenInjectionError):
    """Raised when a compiled knowledge payload fails integrity checks."""


LKIF_FIELDS = (
    "id",
    "category",
    "question",
    "answer",
    "source_model",
    "confidence",
    "tags",
    "evidence",
    "scope",
    "created_at",
    "format_version",
    "content_hash",
)


# ---------------------------------------------------------------------------
# Normalização e hashing (para deduplicação determinística, sem ML)
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Normaliza texto para comparação de duplicatas: minúsculas, sem
    acentuação de espaços redundante, sem pontuação nas bordas.

    Isto é deliberadamente simples (comparação exata pós-normalização),
    não uma similaridade semântica — o container não roda embeddings.
    Se dois textos diferentes normalizarem igual, é duplicata; qualquer
    coisa mais sutil deve ser resolvida pelo modelo que está injetando,
    lendo `read_category()` antes de escrever.
    """
    t = text.strip().lower()
    t = _WS_RE.sub(" ", t)
    t = t.strip(" .!?")
    return t


def _content_hash(category: str, question: str, answer: str) -> str:
    payload = f"{category}\x1f{_normalize(question)}\x1f{_normalize(answer)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Entrada de conhecimento
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeEntry:
    """Uma unidade atômica de conhecimento injetável.

    Campos obrigatórios pelo schema (ver `write_schema`):
    category, question, answer, source_model.
    """

    category: str
    question: str
    answer: str
    source_model: str
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)
    evidence: Optional[str] = None
    scope: str = "public"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    created_at: float = field(default_factory=time.time)
    format_version: str = LKIF_FORMAT_VERSION
    content_hash: str = ""

    def __post_init__(self) -> None:
        expected = _content_hash(self.category, self.question, self.answer)
        if self.content_hash and self.content_hash != expected:
            raise SchemaValidationError(
                "content_hash inválido: esperado "
                f"{expected}, recebido {self.content_hash}"
            )
        self.content_hash = expected

    def validate(self) -> None:
        if not self.category or "/" not in self.category and " " in self.category:
            # categorias podem ser simples ("fisica") ou hierárquicas
            # ("fisica/quantica"); só exigimos que não seja vazia.
            pass
        if not self.category:
            raise SchemaValidationError("category é obrigatório (ex: 'programacao/python')")
        if not self.question or not self.question.strip():
            raise SchemaValidationError("question não pode ser vazio")
        if not self.answer or not self.answer.strip():
            raise SchemaValidationError("answer não pode ser vazio")
        if not self.source_model or not self.source_model.strip():
            raise SchemaValidationError(
                "source_model é obrigatório: todo conhecimento injetado precisa de proveniência"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise SchemaValidationError("confidence deve estar entre 0.0 e 1.0")
        if self.scope not in ("public", "private"):
            raise SchemaValidationError("scope deve ser 'public' ou 'private'")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category,
            "question": self.question,
            "answer": self.answer,
            "source_model": self.source_model,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "evidence": self.evidence,
            "scope": self.scope,
            "created_at": self.created_at,
            "format_version": self.format_version,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "KnowledgeEntry":
        known = set(LKIF_FIELDS)
        unknown = set(d) - known
        if unknown:
            raise SchemaValidationError(f"Campos não permitidos: {', '.join(sorted(unknown))}")
        clean = {k: v for k, v in d.items() if k in known}
        entry = cls(**clean)
        entry.validate()
        return entry


# ---------------------------------------------------------------------------
# Protocolo de Injeção Aberta
# ---------------------------------------------------------------------------

class OpenInjectionProtocol:
    """Camada de leitura/escrita de conhecimento sobre um container `.lira`.

    Uso típico por um modelo externo::

        lb = LiraBinary("agente.lira")
        oip = OpenInjectionProtocol(lb)

        # 1. Ler antes de escrever (evita redundância)
        existentes = oip.read_category("fisica/mecanica_quantica")

        # 2. Injetar conhecimento novo
        oip.inject(
            category="fisica/mecanica_quantica",
            question="O que é o princípio da incerteza de Heisenberg?",
            answer="...",
            source_model="Claude Sonnet 5",
            confidence=0.95,
        )
    """

    def __init__(self, container) -> None:
        self._c = container
        self._ensure_knowledge_section()

    # -- bootstrap / migração --------------------------------------------
    def _ensure_knowledge_section(self) -> None:
        """Garante que containers criados antes deste módulo existir
        (ou criados sem a seção 'knowledge') ganhem a estrutura vazia,
        sem quebrar compatibilidade com o que já está gravado."""
        meta = self._c._metadata
        if "knowledge" not in meta:
            new_meta = copy.deepcopy(meta)
            new_meta["knowledge"] = {}
            self._c._commit(new_meta)

    # -- escrita -----------------------------------------------------------
    def inject(
        self,
        category: str,
        question: str,
        answer: str,
        source_model: str,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        evidence: Optional[str] = None,
        scope: str = "public",
        allow_duplicate: bool = False,
    ) -> str:
        """Injeta uma entrada de conhecimento na categoria indicada.

        `scope` controla se a entrada pode sair do container: "public"
        (padrão) é elegível para `export_jsonl()` normal; "private" só
        sai se `export_jsonl(..., include_private=True)` for chamado
        explicitamente. Serve para conhecimento sobre o usuário (ex:
        preferências, dados pessoais) que o modelo aprende com o tempo
        mas que não deve vazar por padrão para outro modelo/agente.

        Retorna o `id` da entrada (nova, ou da existente se for uma
        duplicata detectada e `allow_duplicate=False`).
        """
        entry = KnowledgeEntry(
            category=category,
            question=question,
            answer=answer,
            source_model=source_model,
            confidence=confidence,
            tags=tags or [],
            evidence=evidence,
            scope=scope,
        )
        entry.validate()

        existing = self._c._metadata["knowledge"].get(category, [])
        if not allow_duplicate:
            for prior in existing:
                if prior.get("content_hash") == entry.content_hash:
                    return prior["id"]  # já existe; não duplica

        new_metadata = copy.deepcopy(self._c._metadata)
        bucket = new_metadata["knowledge"].setdefault(category, [])
        bucket.append(entry.to_dict())

        # mantém a categoria também visível em `categories`, do mesmo
        # jeito que módulos e skills já fazem, para que list_categories()
        # continue sendo a única fonte de verdade sobre o que existe.
        cat = new_metadata["categories"].get(category, {"modules": [], "skills": []})
        cat.setdefault("knowledge", [])
        cat["knowledge"].append(entry.id)
        new_metadata["categories"][category] = cat

        self._c._commit(new_metadata)
        return entry.id

    def inject_batch(self, entries: Iterable[KnowledgeEntry], allow_duplicate: bool = False) -> List[str]:
        """Injeta várias entradas em um único commit (uma escrita em disco)."""
        entries = list(entries)
        for e in entries:
            e.validate()

        new_metadata = copy.deepcopy(self._c._metadata)
        ids: List[str] = []
        for entry in entries:
            bucket = new_metadata["knowledge"].setdefault(entry.category, [])
            if not allow_duplicate:
                dup = next((p for p in bucket if p.get("content_hash") == entry.content_hash), None)
                if dup is not None:
                    ids.append(dup["id"])
                    continue
            bucket.append(entry.to_dict())
            cat = new_metadata["categories"].get(entry.category, {"modules": [], "skills": []})
            cat.setdefault("knowledge", [])
            cat["knowledge"].append(entry.id)
            new_metadata["categories"][entry.category] = cat
            ids.append(entry.id)

        self._c._commit(new_metadata)
        return ids

    # -- leitura -------------------------------------------------------------
    def list_knowledge_categories(self) -> List[str]:
        return list(self._c._metadata["knowledge"].keys())

    def _read_category_internal(self, category: str) -> List[Dict]:
        """Return stored entries without hydrating compiled indexes."""
        return copy.deepcopy(self._c._metadata["knowledge"].get(category, []))

    def _read_all_internal(self) -> Dict[str, List[Dict]]:
        return copy.deepcopy(self._c._metadata["knowledge"])

    def _read_compiled_payload(self, module_name: str) -> Dict[str, Dict]:
        module = self._c._metadata.get("modules", {}).get(module_name)
        if module is None:
            raise KnowledgeIntegrityError(f"Módulo compilado ausente: {module_name}")
        meta = module.get("metadata", {})
        required = ("knowledge_payload_offset", "knowledge_payload_length", "knowledge_payload_sha256")
        missing = [k for k in required if k not in meta]
        if missing:
            raise KnowledgeIntegrityError(
                f"Payload de {module_name} sem campos obrigatórios: {', '.join(missing)}"
            )

        offset = meta["knowledge_payload_offset"]
        length = meta["knowledge_payload_length"]
        if not isinstance(offset, int) or not isinstance(length, int) or offset < 0 or length <= 0:
            raise KnowledgeIntegrityError(
                f"Payload de {module_name} tem offset/comprimento inválido: {offset}/{length}"
            )
        file_size = Path(self._c.path).stat().st_size
        if offset + length > file_size:
            raise KnowledgeIntegrityError(
                f"Payload de {module_name} excede o arquivo: "
                f"offset={offset}, length={length}, file_size={file_size}"
            )

        raw = bytes(self._c._ensure_mmap()[offset: offset + length])
        actual = hashlib.sha256(raw).hexdigest()
        expected = meta["knowledge_payload_sha256"]
        if actual != expected:
            raise KnowledgeIntegrityError(
                f"Hash do payload de {module_name} divergente: esperado {expected}, obtido {actual}"
            )
        try:
            payload_obj = json.loads(zlib.decompress(raw).decode("utf-8"))
        except (zlib.error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KnowledgeIntegrityError(
                f"Payload de {module_name} não pôde ser decodificado após validação de hash: {exc}"
            ) from exc
        if not isinstance(payload_obj, list):
            raise KnowledgeIntegrityError(f"Payload de {module_name} não é uma lista")
        return {e["id"]: e for e in payload_obj if isinstance(e, dict) and "id" in e}

    def _hydrate_entry(self, category: str, entry: Dict, payload_cache: Dict[str, Dict[str, Dict]]) -> Dict:
        if "compiled_into" not in entry:
            return {k: copy.deepcopy(v) for k, v in entry.items() if k in LKIF_FIELDS}

        module_name = entry["compiled_into"]
        if module_name not in payload_cache:
            payload_cache[module_name] = self._read_compiled_payload(module_name)
        payload = payload_cache[module_name].get(entry.get("id"), {})
        hydrated = {
            "id": entry.get("id", payload.get("id")),
            "category": payload.get("category", category),
            "question": payload.get("question"),
            "answer": payload.get("answer"),
            "source_model": entry.get("source_model", payload.get("source_model", "")),
            "confidence": entry.get("confidence", payload.get("confidence", 1.0)),
            "tags": payload.get("tags", entry.get("tags", [])),
            "evidence": payload.get("evidence", entry.get("evidence")),
            "scope": entry.get("scope", payload.get("scope", "public")),
            "created_at": payload.get("created_at", entry.get("created_at", 0.0)),
            "format_version": payload.get("format_version", entry.get("format_version", LKIF_FORMAT_VERSION)),
            "content_hash": payload.get("content_hash", entry.get("content_hash", "")),
        }
        missing = [k for k in ("category", "question", "answer", "source_model") if not hydrated.get(k)]
        if missing:
            raise KnowledgeIntegrityError(
                f"Entrada compilada {entry.get('id')} em {module_name} não pode ser hidratada; "
                f"faltam campos: {', '.join(missing)}"
            )
        expected_hash = _content_hash(hydrated["category"], hydrated["question"], hydrated["answer"])
        if hydrated.get("content_hash") and hydrated["content_hash"] != expected_hash:
            raise KnowledgeIntegrityError(
                f"content_hash da entrada {hydrated['id']} diverge: "
                f"esperado {expected_hash}, recebido {hydrated['content_hash']}"
            )
        hydrated["content_hash"] = expected_hash
        return hydrated

    def _hydrate_category(self, category: str, entries: List[Dict]) -> List[Dict]:
        payload_cache: Dict[str, Dict[str, Dict]] = {}
        return [self._hydrate_entry(category, e, payload_cache) for e in entries]

    def read_category(self, category: str) -> List[Dict]:
        """Retorna todas as entradas de uma categoria — é isso que um
        modelo deve chamar antes de injetar, para checar o que já foi
        ensinado (item 3 do OIP: transparência para agentes)."""
        return self._hydrate_category(category, self._c._metadata["knowledge"].get(category, []))

    def read_all(self) -> Dict[str, List[Dict]]:
        return {
            cat: self._hydrate_category(cat, entries)
            for cat, entries in self._c._metadata["knowledge"].items()
        }

    def search(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """Busca simples por substring normalizada em question/answer/tags.
        Não é busca semântica — é um grep determinístico, suficiente para
        um modelo checar rapidamente se algo parecido já foi ensinado."""
        q = _normalize(query)
        results = []
        buckets = (
            {category: self.read_category(category)}
            if category
            else self.read_all()
        )
        for cat, entries in buckets.items():
            for e in entries:
                haystack = _normalize(e["question"] + " " + e["answer"] + " " + " ".join(e.get("tags", [])))
                if q in haystack:
                    results.append(e)
        return results

    def stats(self) -> Dict:
        knowledge = self.read_all()
        by_source: Dict[str, int] = {}
        total = 0
        for entries in knowledge.values():
            for e in entries:
                by_source[e["source_model"]] = by_source.get(e["source_model"], 0) + 1
                total += 1
        return {
            "categories": len(knowledge),
            "total_entries": total,
            "entries_by_source_model": by_source,
        }

    def compression_report(self) -> Dict:
        """Testado contra a alternativa 'cofre LSA' em escala real: a
        compressão simples ganhou em todos os tamanhos de corpus testados
        (7x-25x menor, sem nenhuma perda de exatidão). Este método reporta
        o ganho de comprimir a seção `knowledge` tal como está, sem
        precisar de nenhum parâmetro treinado."""
        raw = json.dumps(self.read_all(), ensure_ascii=False).encode("utf-8")
        compressed = zlib.compress(raw, level=9)
        return {
            "bytes_sem_compressao": len(raw),
            "bytes_com_zlib": len(compressed),
            "razao_de_compressao": round(len(raw) / max(len(compressed), 1), 2),
        }

    # -- exportação (formato de intercâmbio: JSONL aberto) --------------------
    def export_jsonl(
        self,
        path: Union[str, Path],
        category: Optional[str] = None,
        include_private: bool = False,
    ) -> Path:
        """Exporta conhecimento em LKIF/JSONL — o formato que qualquer
        outro modelo consegue ler sem precisar entender o container
        binário. Uma entrada JSON por linha.

        Por padrão (`include_private=False`), entradas com `scope`
        "private" (ex: preferências e fatos sobre o usuário aprendidos
        organicamente) são omitidas — essa é a fronteira entre "o que o
        agente sabe" e "o que pode sair para outro modelo". Passe
        `include_private=True` explicitamente para incluir tudo.
        """
        path = Path(path)
        buckets = (
            {category: self.read_category(category)}
            if category
            else self.read_all()
        )
        if not include_private:
            buckets = {
                cat: [e for e in entries if e.get("scope", "public") != "private"]
                for cat, entries in buckets.items()
            }
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "lkif_manifest": True,
                "format_version": LKIF_FORMAT_VERSION,
                "source_container": str(getattr(self._c, "path", "")),
                "exported_at": time.time(),
                "categories": list(buckets.keys()),
                "include_private": include_private,
            }, ensure_ascii=False) + "\n")
            for cat, entries in buckets.items():
                for e in entries:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
        return path

    def import_jsonl(self, path: Union[str, Path], allow_duplicate: bool = False) -> List[str]:
        """Importa um arquivo LKIF/JSONL (produzido por qualquer modelo)
        para dentro do container. Ignora a linha de manifesto se presente,
        valida cada entrada contra o schema antes de commitar."""
        path = Path(path)
        entries: List[KnowledgeEntry] = []
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    raise SchemaValidationError(f"Linha {lineno} não é JSON válido: {e}")
                if obj.get("lkif_manifest"):
                    continue  # cabeçalho, não é uma entrada
                try:
                    entries.append(KnowledgeEntry.from_dict(obj))
                except SchemaValidationError as e:
                    raise SchemaValidationError(f"Linha {lineno}: {e}") from e
        return self.inject_batch(entries, allow_duplicate=allow_duplicate)

    # -- exportação legível por humanos ---------------------------------------
    def export_markdown(self, category: Optional[str] = None) -> str:
        """Renderiza o conhecimento como Markdown — para auditoria humana,
        não para troca entre modelos (use `export_jsonl` para isso)."""
        buckets = (
            {category: self.read_category(category)}
            if category
            else self.read_all()
        )
        lines = ["# Conhecimento armazenado (.lira)\n"]
        for cat, entries in sorted(buckets.items()):
            lines.append(f"## {cat}  ({len(entries)} entradas)\n")
            for e in entries:
                lines.append(f"**P:** {e['question']}")
                lines.append(f"**R:** {e['answer']}")
                conf_pct = round(e.get("confidence", 1.0) * 100)
                lines.append(f"_fonte: {e['source_model']} · confiança: {conf_pct}% · id: {e['id']}_\n")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Schema aberto (para qualquer modelo/ferramenta validar seu próprio JSONL)
# ---------------------------------------------------------------------------

def lkif_json_schema() -> Dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://lira-format.org/schemas/lkif-1.0.json",
        "title": "Lira Knowledge Injection Format (LKIF) entry",
        "type": "object",
        "required": ["category", "question", "answer", "source_model"],
        "properties": {
            "id": {"type": "string", "description": "Identificador único da entrada (gerado se ausente)."},
            "category": {
                "type": "string",
                "description": "Categoria semântica hierárquica, ex: 'fisica/mecanica_quantica'.",
                "minLength": 1,
            },
            "question": {"type": "string", "minLength": 1},
            "answer": {"type": "string", "minLength": 1},
            "source_model": {
                "type": "string",
                "description": "Identificação do modelo/agente que injetou esta entrada (proveniência obrigatória).",
                "minLength": 1,
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 1.0},
            "tags": {"type": "array", "items": {"type": "string"}, "default": []},
            "evidence": {
                "type": ["string", "null"],
                "description": "Justificativa opcional, fonte ou raciocínio por trás da resposta.",
            },
            "created_at": {"type": "number", "description": "Unix timestamp de criação."},
            "scope": {
                "type": "string",
                "enum": ["public", "private"],
                "default": "public",
                "description": "Define se a entrada pode ser exportada por padrão.",
            },
            "format_version": {"type": "string", "const": LKIF_FORMAT_VERSION},
            "content_hash": {
                "type": "string",
                "description": "sha256(category + question normalizada + answer normalizada); usado para deduplicação determinística.",
            },
        },
        "additionalProperties": False,
    }


def write_schema(path: Union[str, Path]) -> Path:
    path = Path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lkif_json_schema(), f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------------------
# Demonstração
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    import numpy as np
    from lira_binary import LiraBinary

    base = {"layer.weight": np.ones((4, 4), dtype=np.float32)}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "agente.lira"
        lb = LiraBinary.create(path, base)
        oip = OpenInjectionProtocol(lb)

        print(">>> Claude lê a categoria antes de ensinar algo (evita redundância)")
        print(oip.read_category("fisica/mecanica_quantica"))

        print("\n>>> Claude injeta conhecimento novo")
        oip.inject(
            category="fisica/mecanica_quantica",
            question="O que é o princípio da incerteza de Heisenberg?",
            answer=(
                "Estabelece que não é possível conhecer simultaneamente, com "
                "precisão arbitrária, a posição e o momento de uma partícula."
            ),
            source_model="Claude Sonnet 5",
            confidence=0.95,
            tags=["fisica", "quantica", "principios"],
        )

        print("\n>>> GPT tenta injetar o mesmo conhecimento reformulado -> detecta duplicata")
        dup_id = oip.inject(
            category="fisica/mecanica_quantica",
            question="O que é o princípio da incerteza de Heisenberg?",
            answer=(
                "Estabelece que não é possível conhecer simultaneamente, com "
                "precisão arbitrária, a posição e o momento de uma partícula."
            ),
            source_model="GPT",
        )
        print("id retornado (igual ao anterior, sem duplicar):", dup_id)

        print("\n>>> Exportando em Markdown para auditoria humana:")
        print(oip.export_markdown())

        print(">>> Exportando em LKIF/JSONL para outro modelo consumir:")
        jsonl_path = oip.export_jsonl(Path(tmpdir) / "conhecimento.jsonl")
        print(jsonl_path.read_text())

        print(">>> Estatísticas:")
        print(oip.stats())

        lb.close()


if __name__ == "__main__":
    _demo()
