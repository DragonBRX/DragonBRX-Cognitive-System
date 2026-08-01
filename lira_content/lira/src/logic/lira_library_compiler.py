"""Knowledge Compiler v2 — LSA real (TF-IDF + SVD) + arquitetura de biblioteca.

Depois de testar honestamente: feature hashing (v1) é fraco pra
generalizar (errou uma pergunta parafraseada). Análise Semântica
Latente (LSA — Deerwester et al., 1990, técnica real e estabelecida,
não é modismo) capturou o sentido melhor, com um parâmetro MENOR.

Isso confirma a intuição da "biblioteca" que motivou este módulo: uma
biblioteca de verdade não tenta fazer um único objeto ser ao mesmo
tempo o livro (denso, específico) e o catálogo (esparso, navegável).
Ela SEPARA os dois:

  * Formato "Cofre" (Vault): os parâmetros densos — a matriz de tópicos
    latentes (Vt truncada) e os vetores de cada documento. Isso é
    o mais próximo de "parâmetro real" que dá pra treinar sem
    depender de um modelo neural externo: é álgebra linear genuína
    (SVD), não decoração.
  * Formato "Catálogo" (Catalog): o índice legível — quais tópicos
    existem, quais documentos pertencem a cada categoria, proveniência,
    confiança. Isso é o que já existe em `lira_open_injection.py`
    (a seção `knowledge`), mantido comprimido.

Nenhum dos dois pretende ser "melhor que os pesos de um LLM treinado".
LSA é uma técnica de décadas atrás, honesta sobre suas limitações:
captura co-ocorrência de palavras, não sentido profundo. Ela generaliza
melhor que hashing cru porque explora estrutura estatística real do
corpus (quais palavras aparecem juntas), mas ainda depende de as
palavras se sobreporem o suficiente entre pergunta e resposta.
"""

from __future__ import annotations

import copy
import hashlib
import re
import zlib
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class LSAEncoder:
    """TF-IDF + SVD truncado. Treina o espaço latente uma vez sobre o
    corpus inteiro da categoria; depois projeta perguntas novas nesse
    mesmo espaço (fold-in), sem precisar retreinar."""

    def __init__(self, k: int = 8) -> None:
        self.k = k
        self.vocab: Dict[str, int] = {}
        self.idf: np.ndarray = None
        self.Vt_k: np.ndarray = None  # (k, |vocab|) -- é o "parâmetro" treinado

    def fit(self, documents: List[str]) -> np.ndarray:
        """Treina no corpus e retorna os vetores latentes de cada documento."""
        tokenized = [_tokenize(d) for d in documents]
        vocab = sorted(set(w for doc in tokenized for w in doc))
        self.vocab = {w: i for i, w in enumerate(vocab)}

        n_docs, n_vocab = len(documents), len(vocab)
        tf = np.zeros((n_docs, n_vocab))
        for i, doc in enumerate(tokenized):
            for w, cnt in Counter(doc).items():
                tf[i, self.vocab[w]] = cnt
        df = (tf > 0).sum(axis=0)
        self.idf = np.log(n_docs / (df + 1)) + 1
        tfidf = tf * self.idf

        k = min(self.k, min(tfidf.shape) - 1) if min(tfidf.shape) > 1 else 1
        self.k = max(k, 1)
        U, S, Vt = np.linalg.svd(tfidf, full_matrices=False)
        self.Vt_k = Vt[: self.k]  # o parâmetro treinado real
        doc_vectors = U[:, : self.k] * S[: self.k]
        return doc_vectors

    def transform(self, text: str) -> np.ndarray:
        """Projeta um texto novo no espaço latente já treinado (fold-in),
        sem re-treinar o modelo -- é o mesmo princípio de embedding
        lookup em qualquer sistema neural, só que com álgebra linear
        clássica em vez de uma rede."""
        toks = _tokenize(text)
        v = np.zeros(len(self.vocab))
        for w, cnt in Counter(toks).items():
            if w in self.vocab:
                v[self.vocab[w]] = cnt * self.idf[self.vocab[w]]
        return v @ self.Vt_k.T

    def to_tensor(self) -> np.ndarray:
        return self.Vt_k.astype(np.float32)

    @classmethod
    def from_tensor(cls, Vt_k: np.ndarray, vocab: Dict[str, int], idf: np.ndarray, k: int) -> "LSAEncoder":
        enc = cls(k=k)
        enc.vocab = vocab
        enc.idf = idf
        enc.Vt_k = Vt_k
        return enc


class LibraryCompiler:
    """Implementa a arquitetura de dois formatos ('Cofre' + 'Catálogo')
    sobre um container `.lira`, usando LSA como técnica de compressão
    semântica real (não hashing cego)."""

    def __init__(self, container, k: int = 8) -> None:
        self._c = container
        self.k = k

    def compile_category(self, category: str, oip) -> Dict:
        entries = oip.read_category(category)
        if not entries:
            raise ValueError(f"Categoria '{category}' não tem entradas para compilar")

        questions = [e["question"] for e in entries]
        answers = [e["answer"] for e in entries]
        documents = [q + " " + a for q, a in zip(questions, answers)]

        raw_before = self._category_raw_size(category)

        encoder = LSAEncoder(k=self.k)
        doc_vectors = encoder.fit(documents)

        # avaliação honesta: o quanto cada pergunta (sozinha) aponta pro
        # próprio documento quando projetada no espaço já treinado
        correct = 0
        for i, q in enumerate(questions):
            qv = encoder.transform(q)
            sims = doc_vectors @ qv
            norms = np.linalg.norm(doc_vectors, axis=1) * (np.linalg.norm(qv) + 1e-9)
            sims = sims / (norms + 1e-9)
            if int(np.argmax(sims)) == i:
                correct += 1
        retrieval_accuracy = correct / len(questions)

        joined = "\x00".join(answers).encode("utf-8")
        compressed_payload = zlib.compress(joined, level=9)
        payload_offset, payload_length = self._c._append_raw(compressed_payload)

        from lira_final_demo import Module

        Vt_tensor = encoder.to_tensor()
        module = Module(
            name=f"lsa_vault::{category}",
            module_type="DELTA",
            tensors={
                f"Vt::{category}": Vt_tensor,
                f"doc_vectors::{category}": doc_vectors.astype(np.float32),
            },
            domain=category,
            metadata={
                "kind": "lsa_vault",
                "technique": "TF-IDF + truncated SVD (LSA)",
                "n_examples": len(entries),
                "k": encoder.k,
                "vocab": encoder.vocab,
                "idf": encoder.idf.tolist(),
                "retrieval_accuracy_on_training_set": retrieval_accuracy,
                "answers_payload_offset": payload_offset,
                "answers_payload_length": payload_length,
                "answers_payload_sha256": hashlib.sha256(compressed_payload).hexdigest(),
                "answer_order": [e["id"] for e in entries],
            },
        )
        self._c.append_module(module)

        # Catálogo: índice compacto e legível, sem o corpo do texto
        new_metadata = copy.deepcopy(self._c._metadata)
        new_metadata["knowledge"][category] = [
            {
                "id": e["id"],
                "source_model": e["source_model"],
                "confidence": e["confidence"],
                "content_hash": e["content_hash"],
                "compiled_into": module.name,
            }
            for e in entries
        ]
        self._c._commit(new_metadata)

        raw_after = self._category_raw_size(category)
        vault_bytes = Vt_tensor.nbytes + doc_vectors.nbytes + len(compressed_payload)

        return {
            "category": category,
            "tecnica": "LSA (TF-IDF + SVD truncado)",
            "n_examples": len(entries),
            "retrieval_accuracy_on_training_set": retrieval_accuracy,
            "bytes_catalogo_antes": raw_before,
            "bytes_catalogo_depois": raw_after,
            "bytes_cofre_Vt": Vt_tensor.nbytes,
            "bytes_cofre_doc_vectors": doc_vectors.nbytes,
            "bytes_payload_comprimido": len(compressed_payload),
            "bytes_total_cofre_mais_catalogo": raw_after + vault_bytes,
        }

    def query(self, category: str, question: str, top_k: int = 1) -> List[Dict]:
        module_name = f"lsa_vault::{category}"
        entry = self._c._metadata["modules"].get(module_name)
        if entry is None:
            raise KeyError(f"Categoria '{category}' ainda não foi compilada")
        meta = entry["metadata"]

        Vt = self._load_tensor(module_name, f"Vt::{category}")
        doc_vectors = self._load_tensor(module_name, f"doc_vectors::{category}")

        vocab = meta["vocab"]
        idf = np.array(meta["idf"])
        toks = _tokenize(question)
        v = np.zeros(len(vocab))
        for w, cnt in Counter(toks).items():
            if w in vocab:
                v[vocab[w]] = cnt * idf[vocab[w]]
        qv = v @ Vt.T

        sims = doc_vectors @ qv
        norms = np.linalg.norm(doc_vectors, axis=1) * (np.linalg.norm(qv) + 1e-9)
        cos_sim = sims / (norms + 1e-9)
        order = np.argsort(-cos_sim)[:top_k]

        offset, length = meta["answers_payload_offset"], meta["answers_payload_length"]
        raw = self._read_raw(offset, length)
        answers = zlib.decompress(raw).decode("utf-8").split("\x00")

        return [
            {
                "answer": answers[i],
                "cosine_similarity": float(cos_sim[i]),
                "answer_id": meta["answer_order"][i],
            }
            for i in order
        ]

    def _load_tensor(self, module_name: str, tensor_name: str) -> np.ndarray:
        entry = self._c._metadata["modules"][module_name]
        ref = entry["tensors"][tensor_name]
        return self._c._ref_to_array(ref, f"{module_name}/{tensor_name}")

    def _read_raw(self, offset: int, length: int) -> bytes:
        mm = self._c._ensure_mmap()
        return bytes(mm[offset: offset + length])

    def _category_raw_size(self, category: str) -> int:
        import json
        return len(json.dumps(self._c._metadata["knowledge"].get(category, [])).encode("utf-8"))


def _demo() -> None:
    import tempfile
    from pathlib import Path
    from lira_binary import LiraBinary
    from lira_open_injection import OpenInjectionProtocol

    perguntas_respostas = [
        ("O que é uma lista em Python?", "Uma estrutura de dados ordenada e mutável que guarda uma sequência de elementos."),
        ("O que é uma tupla em Python?", "Uma estrutura de dados ordenada e imutável, similar a lista mas que nao pode ser alterada depois de criada."),
        ("O que é um dicionário em Python?", "Uma estrutura de dados que mapeia chaves unicas para valores, com acesso rapido por chave."),
        ("O que é um set em Python?", "Uma coleção nao ordenada de elementos unicos, util para remover duplicatas e testar pertencimento."),
        ("O que é recursão?", "Uma técnica onde uma função chama a si mesma para resolver um problema dividindo em subproblemas menores."),
        ("O que é complexidade O(n)?", "Significa que o tempo de execução cresce linearmente com o tamanho da entrada."),
        ("O que é complexidade O(1)?", "Significa tempo constante, independente do tamanho da entrada."),
        ("O que é um closure?", "Uma função que captura e lembra variáveis do escopo onde foi definida, mesmo depois desse escopo terminar."),
        ("O que é herança em POO?", "Um mecanismo onde uma classe filha reaproveita atributos e métodos de uma classe pai."),
        ("O que é polimorfismo?", "A capacidade de objetos de classes diferentes responderem à mesma interface de formas diferentes."),
    ]

    base = {"attn.weight": np.random.rand(8, 8).astype(np.float32)}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "agente.lira"
        lb = LiraBinary.create(path, base)
        oip = OpenInjectionProtocol(lb)
        for q, a in perguntas_respostas:
            oip.inject(category="programacao/python", question=q, answer=a, source_model="Claude Sonnet 5", confidence=0.9)

        compiler = LibraryCompiler(lb, k=8)
        report = compiler.compile_category("programacao/python", oip)
        print("Relatório:", report)

        print("\nConsulta com pergunta reformulada (não é o texto de treino):")
        r = compiler.query("programacao/python", "pra que serve encapsulamento e reaproveitar codigo de uma classe mae", top_k=2)
        for item in r:
            print(f"  sim={item['cosine_similarity']:.3f} -> {item['answer'][:90]}")

        lb.close()


if __name__ == "__main__":
    _demo()
