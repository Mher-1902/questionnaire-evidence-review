"""Query-dependent FTS5 retrieval with explicit replacement-family expansion."""

import re
import sqlite3
import time

from .domain import Authority, Dataset, Question

# Generic query words, never product names or question-specific answers.
STOPWORDS = frozenset(
    "a an the is are was were do does can how what who when which "
    "and or of for to in on with available offered often".split()
)


def retrieve(data: Dataset, question: Question, strategy="retrieval", top_k=3):
    started = time.perf_counter()
    all_passages = data.passage_map()
    ranked = []
    fallback = None
    if strategy == "full_context":
        document_ids = set(data.document_map())
    elif strategy == "retrieval":
        tokens = list(dict.fromkeys(re.findall(r"[^\W_]+", question.text.lower())))
        tokens = [token for token in tokens if token not in STOPWORDS][:64]
        expression = " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)
        with sqlite3.connect(":memory:") as conn:
            conn.execute(
                "CREATE VIRTUAL TABLE passages USING fts5("
                "passage_id UNINDEXED, text, tokenize='porter unicode61')"
            )
            conn.executemany(
                "INSERT INTO passages VALUES(?,?)",
                [(p.id, p.text) for d in data.documents for p in d.passages],
            )
            if expression:
                ranked = [
                    {"passage_id": row[0], "score": row[1]}
                    for row in conn.execute(
                        "SELECT passage_id, bm25(passages) FROM passages WHERE passages MATCH ? "
                        "ORDER BY bm25(passages), passage_id LIMIT ?",
                        (expression, top_k),
                    )
                ]
        if ranked:
            selected_docs = {all_passages[r["passage_id"]][0].id for r in ranked}
            document_ids = Authority(data).family(selected_docs)
        else:
            # No lexical match cannot establish absence across the collection.
            document_ids = set(data.document_map())
            fallback = "No lexical matches: explicitly used full-context evidence"
    else:
        raise ValueError("Unknown retrieval strategy")
    documents = [
        d.model_dump(mode="json")
        for d in sorted(data.documents, key=lambda d: d.id)
        if d.id in document_ids
    ]
    return documents, {
        "strategy": strategy,
        "top_k": top_k,
        "ranked_hits": ranked,
        "included_passages": [p["id"] for d in documents for p in d["passages"]],
        "authority_expansion": sorted(
            document_ids - {all_passages[r["passage_id"]][0].id for r in ranked}
        ),
        "fallback": fallback,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
    }
