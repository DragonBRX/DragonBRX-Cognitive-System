"""Knowledge Compiler — transforma texto (LKIF) em parâmetros reais.

O `lira_open_injection.py` guarda conhecimento como texto puro (pares
pergunta/resposta em JSON). Isso é ótimo pra auditoria e troca entre
modelos, mas tem um problema real: **palavras não são parâmetros**.
Texto cresce linearmente com a quantidade de fatos e nunca fica do
tamanho de um tensor; e nada nele "generaliza" — é só um banco de dados
anexado, não algo que o modelo aprendeu de fato.

Este módulo resolve a parte que dá pra resolver sem acesso aos pesos
internos de um LLM de verdade (não temos gradientes de Claude/GPT aqui,
então isso NÃO é fine-tuning do modelo em si). O que ele faz é genuíno,
só que num nível diferente: comprime um conjunto de pares
pergunta/resposta num **adaptador linear treinado por regressão de
Ridge (mínimos quadrados regularizados)** — matemática de treinamento
real, não number crunching decorativo — e guarda esse adaptador como um
tensor binário dentro do `.lira`, do mesmo jeito que um módulo LoRA ou
DELTA já é guardado.

Fluxo:
    1. Vetoriza cada pergunta e cada resposta com feature hashing
       (hashing trick, técnica real e determinística — sem precisar
       baixar nenhum modelo de embeddings).
    2. Treina W (matriz d x d) resolvendo
       W = argmin_W ||Q @ W - A||^2 + lambda ||W||^2
       em forma fechada (equivalente ao ponto de convergência de
       gradiente descendente nesse problema convexo).
    3. Guarda W como um tensor binário (parâmetro real, tamanho FIXO).
       O arquivo ainda cresce com `answer_vectors`, payloads e índices
       referentes ao conhecimento ativo.
    4. Guarda os textos de resposta comprimidos (zlib) e dedupados, só
       o necessário pra reconstruir a palavra final — isso ainda ocupa
       espaço (em algum lugar as palavras têm que existir pra gerar a
       resposta), mas comprimido, e não duplicado por consulta.
    5. Na hora de consultar, a pergunta nova é vetorizada e multiplicada
       pelo parâmetro W (isso É inferência sobre um parâmetro treinado,
       não grep em texto) para encontrar a resposta mais próxima.

Limitação que é preciso deixar clara: isto treina um adaptador de
recuperação associativa *auxiliar*, guardado dentro do arquivo `.lira`.
Não modifica os pesos internos de nenhum LLM real (Claude, GPT, etc.) —
isso exigiria acesso aos gradientes daquele modelo específico, algo que
nenhum sistema externo tem. O que fica genuinamente mais "parâmetro e
menos palavra" é a representação armazenada no arquivo.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import zlib
from typing import Dict, List, Optional, Tuple

import numpy as np


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

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


class KnowledgePayloadIntegrityError(Exception):
    """Raised when a compiled knowledge payload or tensor reference is invalid."""


# ---------------------------------------------------------------------------
# Vetorização determinística (hashing trick) — sem depender de nenhum
# modelo de embeddings externo.
# ---------------------------------------------------------------------------

def _tokens(text: str) -> List[str]:
    text = text.lower()
    words = _TOKEN_RE.findall(text)
    # unigramas + bigramas: dá contexto mínimo sem precisar de embeddings
    grams = list(words)
    grams += [f"{a}_{b}" for a, b in zip(words, words[1:])]
    return grams


def hash_vectorize(text: str, n_features: int = 256) -> np.ndarray:
    """Feature hashing determinístico (hashing trick), com sinal, para
    reduzir viés de colisão — mesma técnica usada em produção por
    ferramentas como Vowpal Wabbit / sklearn HashingVectorizer."""
    vec = np.zeros(n_features, dtype=np.float64)
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % n_features
        sign = 1.0 if (h // n_features) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.astype(np.float32)


# ---------------------------------------------------------------------------
# Treinamento real: regressão de Ridge em forma fechada
# ---------------------------------------------------------------------------

def train_adapter(
    questions: List[str], answers: List[str], n_features: int = 256, ridge_lambda: float = 1.0
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Treina W tal que Q @ W ~= A, minimizando erro quadrático + regularização.

    Retorna (W, answer_vectors, stats) onde `answer_vectors` são os
    vetores-alvo (necessários no momento da consulta para achar a
    resposta mais próxima) e `stats` traz o erro de treino de verdade
    (não é decorativo: é a métrica que prova que o parâmetro aprendeu
    algo além de ruído).
    """
    Q = np.stack([hash_vectorize(q, n_features) for q in questions]).astype(np.float64)
    A = np.stack([hash_vectorize(a, n_features) for a in answers]).astype(np.float64)

    d = n_features
    # forma fechada da regressão de Ridge: W = (Q^T Q + lambda I)^-1 Q^T A
    W = np.linalg.solve(Q.T @ Q + ridge_lambda * np.eye(d), Q.T @ A)

    predicted = Q @ W
    # similaridade de cosseno entre previsto e real, por exemplo — métrica
    # de treino real, não maquiada
    num = np.sum(predicted * A, axis=1)
    den = np.linalg.norm(predicted, axis=1) * np.linalg.norm(A, axis=1) + 1e-9
    cos_sim = num / den
    stats = {
        "n_examples": len(questions),
        "n_features": n_features,
        "ridge_lambda": ridge_lambda,
        "mean_cosine_fit": float(np.mean(cos_sim)),
        "min_cosine_fit": float(np.min(cos_sim)),
    }
    return W.astype(np.float32), A.astype(np.float32), stats


# ---------------------------------------------------------------------------
# Compilador: liga o texto (OpenInjectionProtocol) ao binário (LiraBinary)
# ---------------------------------------------------------------------------

class KnowledgeCompiler:
    """Compacta o conhecimento textual de uma categoria em um módulo
    binário real (parâmetro W + payload de respostas comprimido),
    apendado ao container via o mecanismo de módulos já existente."""

    def __init__(self, container, n_features: int = 256, ridge_lambda: float = 1.0) -> None:
        self._c = container
        self.n_features = n_features
        self.ridge_lambda = ridge_lambda

    def compile_category(self, category: str, oip, force_recompile: bool = False) -> Dict:
        """Treina (ou retreina) o adaptador para `category`.

        A biblioteca evolui: chegam fatos novos depois que uma categoria
        já foi compilada uma vez. Para incorporá-los sem perder o que já
        tinha sido treinado, este método:

        1. Separa as entradas atuais da categoria em "cruas" (nunca
           compiladas, ainda têm `question`/`answer` de verdade) e
           "já compiladas" (viraram índice compacto — ver abaixo).
        2. Recupera o texto original das entradas já compiladas a partir
           do payload comprimido gravado na última compilação (guardamos
           pergunta *e* resposta, não só resposta, exatamente para viabilizar
           isso).
        3. Retreina o adaptador com o conjunto combinado (antigas
           recuperadas + novas), produzindo um parâmetro W que reflete
           TODO o conhecimento acumulado, não perdendo o que já existia.

        Se a categoria já está compilada e não chegou nenhuma entrada
        crua nova, não há nada a aprender de diferente — recompilar
        custaria I/O e CPU para produzir exatamente o mesmo parâmetro.
        Por isso levanta `ValueError` nesse caso, a menos que
        `force_recompile=True` (útil se você mudou `n_features`/
        `ridge_lambda` e quer retreinar mesmo sem dados novos).

        Retorna um relatório com o antes/depois em bytes e com a
        contabilidade da recompilação incremental (`n_novas_entradas`,
        `n_reaproveitadas`, `entradas_antigas_perdidas`).
        """
        entries = (
            oip._read_category_internal(category)
            if hasattr(oip, "_read_category_internal")
            else oip.read_category(category)
        )
        if not entries:
            raise ValueError(f"Categoria '{category}' não tem entradas para compilar")

        module_name = f"knowledge_adapter::{category}"
        existing_module = self._c._metadata["modules"].get(module_name)

        raw_entries = [e for e in entries if "compiled_into" not in e]
        indexed_entries = [e for e in entries if "compiled_into" in e]

        old_full_by_id: Dict[str, Dict] = (
            self._load_compiled_payload(existing_module) if existing_module is not None else {}
        )

        reaproveitadas: List[Dict] = []
        perdidas: List[Dict] = []
        for e in indexed_entries:
            full = old_full_by_id.get(e["id"])
            if full is not None:
                # o índice pode ter uma confidence/scope mais recente que
                # o payload congelado da última compilação (não deveria,
                # mas por segurança prevalece o índice para esses campos)
                merged = {**full, "confidence": e.get("confidence", full.get("confidence", 1.0)),
                          "scope": e.get("scope", full.get("scope", "public"))}
                reaproveitadas.append(merged)
            else:
                perdidas.append(e)

        n_novas = len(raw_entries)
        n_reaproveitadas = len(reaproveitadas)
        n_perdidas = len(perdidas)

        if existing_module is not None and n_novas == 0 and not force_recompile:
            raise ValueError(
                f"Categoria '{category}' já está compilada e não chegou nenhuma entrada "
                f"nova desde a última compilação — recompilar produziria o mesmo "
                f"parâmetro. Use force_recompile=True (CLI: --force) para retreinar "
                f"mesmo assim (ex: depois de mudar n_features/ridge_lambda)."
            )

        training_entries = reaproveitadas + raw_entries
        if not training_entries:
            raise ValueError(
                f"Categoria '{category}' não tem entradas recuperáveis para compilar "
                f"({n_perdidas} entrada(s) antiga(s) perdida(s) — payload ausente/corrompido)."
            )

        questions = [e["question"] for e in training_entries]
        answers = [e["answer"] for e in training_entries]

        raw_json_before = self._category_raw_size(category)

        W, answer_vectors, stats = train_adapter(
            questions, answers, n_features=self.n_features, ridge_lambda=self.ridge_lambda
        )

        # payload comprimido com pergunta E resposta (não só resposta):
        # é o que permite recompilar incrementalmente mais tarde sem
        # perder o texto de treino das entradas já compiladas.
        payload_obj = [{k: copy.deepcopy(e.get(k)) for k in LKIF_FIELDS} for e in training_entries]
        compressed_payload = zlib.compress(json.dumps(payload_obj, ensure_ascii=False).encode("utf-8"), level=9)
        payload_sha = hashlib.sha256(compressed_payload).hexdigest()
        W_arr = np.ascontiguousarray(W)
        answer_vectors_arr = np.ascontiguousarray(answer_vectors)
        W_raw = W_arr.tobytes()
        answer_vectors_raw = answer_vectors_arr.tobytes()
        original_file_size = os.path.getsize(self._c.path)
        (payload_offset, payload_length), (w_offset, w_length), (av_offset, av_length) = self._c._append_raw_batch(
            [compressed_payload, W_raw, answer_vectors_raw]
        )

        # W tem tamanho fixo; answer_vectors e payload crescem com o
        # número de conhecimentos ativos e são compactados após o commit.
        tensors_meta = {
            f"adapter_W::{category}": {
                "shape": list(W_arr.shape),
                "dtype": str(W_arr.dtype),
                "offset": w_offset,
                "length": w_length,
                "sha256": hashlib.sha256(W_raw).hexdigest(),
            },
            f"answer_vectors::{category}": {
                "shape": list(answer_vectors_arr.shape),
                "dtype": str(answer_vectors_arr.dtype),
                "offset": av_offset,
                "length": av_length,
                "sha256": hashlib.sha256(answer_vectors_raw).hexdigest(),
            },
        }

        module_entry = {
            "type": "DELTA",
            "domain": category,
            "metadata": {
                "kind": "knowledge_adapter",
                "n_examples": stats["n_examples"],
                "mean_cosine_fit": stats["mean_cosine_fit"],
                "knowledge_payload_offset": payload_offset,
                "knowledge_payload_length": payload_length,
                "knowledge_payload_sha256": payload_sha,
                "answer_order": [e["id"] for e in training_entries],
                "n_features": self.n_features,
            },
            "tensors": tensors_meta,
        }

        new_metadata = copy.deepcopy(self._c._metadata)
        is_new_module = module_name not in new_metadata["modules"]
        new_metadata["modules"][module_name] = module_entry

        if is_new_module:
            cat = new_metadata["categories"].get(category, {"modules": [], "skills": []})
            cat.setdefault("modules", []).append(module_name)
            new_metadata["categories"][category] = cat
            hist = new_metadata["history"]
            cur = hist["current"]
            active_modules = list(hist["generations"][cur]["modules"]) if cur >= 0 else []
            active_skills = list(hist["generations"][cur].get("skills", [])) if cur >= 0 else []
            active_modules.append(module_name)
            hist["generations"].append({"modules": active_modules, "skills": active_skills})
            hist["current"] = len(hist["generations"]) - 1

        # substitui o texto cru por um índice compacto (mantém proveniência,
        # ids e scope, mas larga o corpo verboso — pergunta e resposta agora
        # "moram" no parâmetro + payload comprimido, não em JSON solto)
        new_metadata["knowledge"][category] = [
            {
                "id": e["id"],
                "source_model": e["source_model"],
                "confidence": e.get("confidence", 1.0),
                "content_hash": e.get("content_hash", ""),
                "scope": e.get("scope", "public"),
                "compiled_into": module_name,
            }
            for e in training_entries
        ]
        try:
            self._c._commit(new_metadata)
        except Exception:
            self._c.close()
            with open(self._c.path, "r+b") as f:
                f.truncate(original_file_size)
                f.flush()
                os.fsync(f.fileno())
            self._c._open_existing()
            raise

        compaction_report = self._c.compact() if hasattr(self._c, "compact") else None

        raw_json_after = self._category_raw_size(category)
        w_bytes = W.nbytes
        av_bytes = answer_vectors.nbytes

        return {
            "category": category,
            "n_examples": stats["n_examples"],
            "n_novas_entradas": n_novas,
            "n_reaproveitadas": n_reaproveitadas,
            "entradas_antigas_perdidas": n_perdidas,
            "mean_cosine_fit": stats["mean_cosine_fit"],
            "bytes_texto_cru_antes": raw_json_before,
            "bytes_indice_compacto_depois": raw_json_after,
            "bytes_parametro_W": w_bytes,
            "bytes_answer_vectors": av_bytes,
            "bytes_payload_comprimido": len(compressed_payload),
            "bytes_total_pos_compilacao": raw_json_after + w_bytes + av_bytes + len(compressed_payload),
            "storage_compaction": compaction_report,
        }

    def _write_delta_tensors(self, tensors: Dict[str, np.ndarray]) -> Dict:
        """Grava tensores crus no container e devolve os metadados de
        referência (offset/length/sha256), no mesmo formato usado por
        `LiraBinary.append_module` para módulos DELTA. Feito diretamente
        (em vez de via `append_module`) porque a recompilação precisa
        poder SUBSTITUIR um módulo já existente com o mesmo nome, o que
        `append_module` recusa de propósito (`ModuleAlreadyExistsError`)
        para módulos comuns."""
        tensors_meta: Dict[str, Dict] = {}
        for tname, value in tensors.items():
            arr = np.ascontiguousarray(value)
            raw = arr.tobytes()
            offset, length = self._c._append_raw(raw)
            tensors_meta[tname] = {
                "shape": list(arr.shape),
                "dtype": str(arr.dtype),
                "offset": offset,
                "length": length,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        return tensors_meta

    def _load_compiled_payload(self, module_entry: Dict) -> Dict[str, Dict]:
        """Decodifica o payload comprimido (pergunta+resposta+proveniência)
        de uma compilação anterior, indexado por id. Retorna {} se o
        módulo for de um formato antigo (só respostas, sem pergunta) —
        nesse caso as entradas antigas contam como 'perdidas', pois o
        texto de treino da pergunta não pode ser reconstruído."""
        meta = module_entry["metadata"]
        if "knowledge_payload_offset" not in meta:
            return {}
        raw = self._read_payload_bytes(meta, "compiled payload")
        try:
            decompressed = zlib.decompress(raw)
            payload_obj = json.loads(decompressed.decode("utf-8"))
        except (zlib.error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KnowledgePayloadIntegrityError(f"Payload compilado inválido: {exc}") from exc
        if not isinstance(payload_obj, list):
            raise KnowledgePayloadIntegrityError("Payload compilado não é uma lista")
        return {e["id"]: e for e in payload_obj}

    def _category_raw_size(self, category: str) -> int:
        return len(json.dumps(self._c._metadata["knowledge"].get(category, [])).encode("utf-8"))

    # -- consulta usando o PARÂMETRO treinado, não busca em texto --------
    def query(self, category: str, question: str, top_k: int = 1) -> List[Dict]:
        """Responde consultando o parâmetro treinado (W), não fazendo
        grep no texto. Isso é o que separa 'ter um parâmetro' de 'ter um
        arquivo de texto anexado'."""
        module_name = f"knowledge_adapter::{category}"
        entry = self._c._metadata["modules"].get(module_name)
        if entry is None:
            raise KeyError(f"Categoria '{category}' ainda não foi compilada em parâmetros")

        meta = entry["metadata"]
        n_features = meta["n_features"]
        tname_W = f"adapter_W::{category}"
        tname_AV = f"answer_vectors::{category}"

        W = self._load_module_tensor(module_name, tname_W)
        answer_vectors = self._load_module_tensor(module_name, tname_AV)

        q_vec = hash_vectorize(question, n_features)
        predicted = q_vec @ W  # <- inferência sobre o parâmetro treinado

        sims = answer_vectors @ predicted
        norms = np.linalg.norm(answer_vectors, axis=1) * (np.linalg.norm(predicted) + 1e-9)
        cos_sim = sims / (norms + 1e-9)
        order = np.argsort(-cos_sim)[:top_k]

        # decodifica o payload comprimido (pergunta+resposta+proveniência) —
        # desde a recompilação incremental este payload é um JSON array de
        # objetos (não mais respostas concatenadas por \x00), na mesma
        # ordem de `answer_order` / `answer_vectors`, então dá pra extrair
        # só as respostas por posição.
        raw = self._read_payload_bytes(meta, module_name)
        try:
            decompressed = zlib.decompress(raw).decode("utf-8")
            payload_obj = json.loads(decompressed)
        except (zlib.error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KnowledgePayloadIntegrityError(f"Payload de {module_name} inválido: {exc}") from exc
        self._validate_payload_and_tensors(meta, payload_obj, W, answer_vectors)
        answers = [e["answer"] for e in payload_obj]

        results = []
        for idx in order:
            results.append({
                "id": payload_obj[idx]["id"],
                "question": payload_obj[idx]["question"],
                "answer": answers[idx],
                "cosine_similarity": float(cos_sim[idx]),
                "answer_id": meta["answer_order"][idx],
            })
        return results

    def _read_payload_bytes(self, meta: Dict, label: str) -> bytes:
        required = ("knowledge_payload_offset", "knowledge_payload_length", "knowledge_payload_sha256")
        missing = [k for k in required if k not in meta]
        if missing:
            raise KnowledgePayloadIntegrityError(f"{label}: campos ausentes: {', '.join(missing)}")
        offset = meta["knowledge_payload_offset"]
        length = meta["knowledge_payload_length"]
        if not isinstance(offset, int) or not isinstance(length, int) or offset < 0 or length <= 0:
            raise KnowledgePayloadIntegrityError(f"{label}: offset/comprimento inválido: {offset}/{length}")
        file_size = os.path.getsize(self._c.path)
        if offset + length > file_size:
            raise KnowledgePayloadIntegrityError(
                f"{label}: leitura além do arquivo (offset={offset}, length={length}, file_size={file_size})"
            )
        raw = self._read_raw_no_hash(offset, length)
        actual = hashlib.sha256(raw).hexdigest()
        expected = meta["knowledge_payload_sha256"]
        if actual != expected:
            raise KnowledgePayloadIntegrityError(
                f"{label}: hash do payload divergente; esperado {expected}, obtido {actual}"
            )
        return raw

    def _validate_payload_and_tensors(
        self, meta: Dict, payload_obj: List[Dict], W: np.ndarray, answer_vectors: np.ndarray
    ) -> None:
        if not isinstance(payload_obj, list) or not all(isinstance(e, dict) for e in payload_obj):
            raise KnowledgePayloadIntegrityError("Payload deve ser uma lista de objetos")
        answer_order = meta.get("answer_order")
        if not isinstance(answer_order, list):
            raise KnowledgePayloadIntegrityError("answer_order ausente ou inválido")
        payload_ids = [e.get("id") for e in payload_obj]
        if answer_order != payload_ids:
            raise KnowledgePayloadIntegrityError(
                f"answer_order diverge dos IDs do payload: {answer_order} != {payload_ids}"
            )
        if len(answer_order) != len(answer_vectors):
            raise KnowledgePayloadIntegrityError(
                f"Quantidade de respostas ({len(answer_order)}) difere dos vetores ({len(answer_vectors)})"
            )
        n_features = meta.get("n_features")
        if not isinstance(n_features, int) or n_features <= 0:
            raise KnowledgePayloadIntegrityError(f"n_features inválido: {n_features}")
        if W.dtype != np.float32 or answer_vectors.dtype != np.float32:
            raise KnowledgePayloadIntegrityError(
                f"Tensores devem ser float32; W={W.dtype}, answer_vectors={answer_vectors.dtype}"
            )
        if W.shape != (n_features, n_features):
            raise KnowledgePayloadIntegrityError(f"W tem shape inválido: {W.shape}")
        if answer_vectors.ndim != 2 or answer_vectors.shape[1] != n_features:
            raise KnowledgePayloadIntegrityError(f"answer_vectors tem shape inválido: {answer_vectors.shape}")

    def _load_module_tensor(self, module_name: str, tensor_name: str) -> np.ndarray:
        entry = self._c._metadata["modules"][module_name]
        ref = entry["tensors"][tensor_name]
        self._validate_tensor_ref(ref, f"{module_name}/{tensor_name}")
        return self._c._ref_to_array(ref, f"{module_name}/{tensor_name}")

    def _validate_tensor_ref(self, ref: Dict, label: str) -> None:
        for key in ("shape", "dtype", "offset", "length", "sha256"):
            if key not in ref:
                raise KnowledgePayloadIntegrityError(f"{label}: referência sem {key}")
        shape = ref["shape"]
        if not isinstance(shape, list) or not shape or not all(isinstance(x, int) and x >= 0 for x in shape):
            raise KnowledgePayloadIntegrityError(f"{label}: shape inválido: {shape}")
        try:
            dtype = np.dtype(ref["dtype"])
        except TypeError as exc:
            raise KnowledgePayloadIntegrityError(f"{label}: dtype inválido: {ref['dtype']}") from exc
        expected_length = int(np.prod(shape)) * dtype.itemsize
        if ref["length"] != expected_length:
            raise KnowledgePayloadIntegrityError(
                f"{label}: length inválido; esperado {expected_length}, recebido {ref['length']}"
            )
        offset = ref["offset"]
        length = ref["length"]
        if not isinstance(offset, int) or not isinstance(length, int) or offset < 0 or length < 0:
            raise KnowledgePayloadIntegrityError(f"{label}: offset/length inválido: {offset}/{length}")
        if offset + length > os.path.getsize(self._c.path):
            raise KnowledgePayloadIntegrityError(f"{label}: referência lê além do fim do arquivo")

    def _read_raw_no_hash(self, offset: int, length: int) -> bytes:
        if not isinstance(offset, int) or not isinstance(length, int) or offset < 0 or length < 0:
            raise KnowledgePayloadIntegrityError(f"Offset/length inválido: {offset}/{length}")
        file_size = os.path.getsize(self._c.path)
        if offset + length > file_size:
            raise KnowledgePayloadIntegrityError(
                f"Leitura além do final do arquivo: offset={offset}, length={length}, file_size={file_size}"
            )
        mm = self._c._ensure_mmap()
        return bytes(mm[offset: offset + length])


def _demo() -> None:
    import tempfile
    from pathlib import Path
    from lira_binary import LiraBinary
    from lira_open_injection import OpenInjectionProtocol

    base = {"attn.weight": np.random.rand(8, 8).astype(np.float32)}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "agente.lira"
        lb = LiraBinary.create(path, base)
        oip = OpenInjectionProtocol(lb)

        oip.inject(category="programacao/python", question="O que é um generator em Python?",
                    answer="Uma função que usa yield em vez de return, produzindo valores sob demanda.",
                    source_model="Claude Sonnet 5", confidence=0.96)
        oip.inject(category="programacao/python", question="Para que serve o GIL?",
                    answer="Um mutex que permite só uma thread rodando bytecode Python por vez.",
                    source_model="Claude Sonnet 5", confidence=0.9)

        compiler = KnowledgeCompiler(lb, n_features=64)
        report = compiler.compile_category("programacao/python", oip)
        print("Relatório de compilação:", report)

        print("\nConsultando com uma PERGUNTA REFORMULADA (não é o texto exato de treino):")
        results = compiler.query("programacao/python", "explica o que é generator", top_k=1)
        print(results)

        lb.close()


if __name__ == "__main__":
    _demo()
