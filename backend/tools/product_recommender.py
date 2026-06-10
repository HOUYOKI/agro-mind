
from .rag_retriever import retrieve_agronomy_knowledge

def recommend_product(message: str) -> dict:
    knowledge = retrieve_agronomy_knowledge(message)
    
    if knowledge and knowledge != "NO_DATA" and "No relevant" not in knowledge:
        return {
            "recommended_product": "Agricultural Solution Found",
            "reason": knowledge,
            "safety_note": "Please follow the dilution ratios mentioned in the product instructions.",
            "detected_crop": "Extracted from query",
            "detected_issue": "Extracted from query"
        }
    
    return {
        "recommended_product": "Consult an agricultural expert",
        "reason": "Feature under development or no product match found.",
        "safety_note": "Please check product label instructions before use.",
        "detected_crop": None,
        "detected_issue": None
    }