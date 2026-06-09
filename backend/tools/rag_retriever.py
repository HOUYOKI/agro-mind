def retrieve_agronomy_knowledge(query: str, intent: str = None) -> dict:
    """
    Placeholder RAG retriever for Agro-Mind MVP.

    Current purpose:
    - Give main.py a stable RAG function to call.
    - Return a predictable dictionary.
    - Later, this function can be replaced with real FAISS/Chroma retrieval.

    Future real RAG flow:
    query -> embeddings -> vector database search -> relevant chunks -> sources
    """

    text = query.lower().strip()

    # Basic placeholder knowledge until real RAG is connected
    if "eat" in text and ("spray" in text or "spraying" in text or "pesticide" in text):
        return {
            "rag_used": True,
            "found": True,
            "summary": (
                "Food safety after pesticide spraying depends on the exact product label "
                "and its pre-harvest interval. The system should not guess a waiting period "
                "without label-specific information."
            ),
            "sources": ["Placeholder pesticide safety guidance"],
            "confidence": 0.75,
            "status": "placeholder"
        }

    if "tomato" in text and ("yellow" in text or "curling" in text or "spots" in text):
        return {
            "rag_used": True,
            "found": True,
            "summary": (
                "Yellowing, curling, or spotted tomato leaves may be linked to watering stress, "
                "nutrient deficiency, pests, or fungal disease. Diagnosis should be confirmed "
                "with images, symptom details, and local growing conditions."
            ),
            "sources": ["Placeholder tomato crop guidance"],
            "confidence": 0.65,
            "status": "placeholder"
        }

    if "aphid" in text or "aphids" in text:
        return {
            "rag_used": True,
            "found": True,
            "summary": (
                "Aphids are small sap-sucking pests that can weaken plants and cause curling, "
                "yellowing, or sticky residue on leaves. Treatment depends on crop type, severity, "
                "and product label suitability."
            ),
            "sources": ["Placeholder aphid pest guidance"],
            "confidence": 0.70,
            "status": "placeholder"
        }

    return {
        "rag_used": True,
        "found": False,
        "summary": "No relevant agronomy knowledge was found in the placeholder RAG system.",
        "sources": [],
        "confidence": 0.0,
        "status": "placeholder"
    }