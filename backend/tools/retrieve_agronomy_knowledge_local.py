"""
retrieve_agronomy_knowledge — RAG tool for Agro-Mind agent
Generated from Phase 7 retrieval testing results.
 
Usage:
    results = retrieve_agronomy_knowledge(
        query="what treats root rot in citrus",
        query_type="disease",        # disease/pest/ingredient/crop/symptom/
                                     # dosage/safety/product_name/general
        n_results=3,
        use_full_docs=False          # True for semantic/Chinese queries
    )
"""
import os
import sys
import ollama
import chromadb

EMBED_MODEL  = "text-embedding-3-large"
CHROMA_PATH  = r"D:\agro-mind\backend\data\chromadb"

_client      = None
_col_struct  = None
_col_full    = None

def _init():
    global _client, _col_struct, _col_full
    if _client is None:
        _client     = chromadb.PersistentClient(path=CHROMA_PATH)
        _col_struct = _client.get_collection('collection_structured')
        _col_full   = _client.get_collection('collection_full')

QUERY_TYPE_FILTERS = {
    'disease':      {'has_diseases':    True},
    'pest':         {'has_pests':       True},
    'ingredient':   {'has_ingredients': True},
    'safety':       {'is_pesticide':    True},
    'microbial':    {'is_microbial':    True},
    'fertilizer':   {'is_fertilizer':   True},
    'crop':         None,
    'symptom':      None,
    'dosage':       None,
    'product_name': None,
    'chinese':      None,
    'general':      None,
}

FULL_DOC_TYPES = {'symptom', 'chinese', 'general', 'safety'}

def retrieve_agronomy_knowledge(
    query: str,
    query_type: str = 'general',
    n_results: int = 3,
    use_full_docs: bool = None,
) -> list[dict]:
    _init()

    if use_full_docs is None:
        use_full_docs = query_type in FULL_DOC_TYPES

    collection = _col_full if use_full_docs else _col_struct
    where      = QUERY_TYPE_FILTERS.get(query_type, None)

    q_vector = ollama.embeddings(model=EMBED_MODEL, prompt=query[:2000]).embedding

    kwargs = {
        'query_embeddings': [q_vector],
        'n_results':        n_results,
        'include':          ['documents', 'metadatas', 'distances'],
    }
    if where:
        kwargs['where'] = where

    raw = collection.query(**kwargs)

    results = []
    if raw and "ids" in raw and len(raw["ids"]) > 0:
        for i in range(len(raw["ids"][0])):
            metadata = raw["metadatas"][0][i] if raw["metadatas"] else {}
            results.append({
                'product_id':      raw['ids'][0][i],
                'product_name':    metadata.get('product_name', 'Agricultural Solution'),
                'product_name_cn': metadata.get('product_name_cn', 'N/A'),
                'detected_crop':   metadata.get('crop', 'Extracted from query'),
                'detected_issue':  metadata.get('disease', metadata.get('pest', 'Extracted from query')),
                'document':        raw['documents'][0][i] if raw['documents'] else '',
                'distance':        round(raw['distances'][0][i], 2) if raw['distances'] else 0.0,
                'collection':      'full' if use_full_docs else 'structured',
            })
    return results


if __name__ == '__main__':
    print('=== RETRIEVAL TOOL TEST ===\n')
    tests = [
        ('citrus yellowing leaves', 'symptom'),
        ('what treats root rot',    'disease'),
    ]
    for query, qtype in tests:
        try:
            results = retrieve_agronomy_knowledge(query, query_type=qtype, n_results=2)
            print(f'[{qtype}] "{query}"')
            for r in results:
                print(f'  → {r["product_id"]} | {r["product_name"]} | dist={r["distance"]}')
        except Exception as e:
            print(f' Error during testing query "{query}": {str(e)}')
        print()