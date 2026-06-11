
import os
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    import retrieve_agronomy_knowledge_local as rag_local
except ImportError:
    from tools import retrieve_agronomy_knowledge_local as rag_local

def recommend_product(message: str) -> dict:
    try:
        results = rag_local.retrieve_agronomy_knowledge(message)
    except Exception as e:
        return {
            "recommended_product": "CRITICAL: RAG Engine Error",
            "reason": f"An unexpected exception occurred inside 'retrieve_agronomy_knowledge_local.py'. Technical details: {str(e)}",
            "safety_note": "DATABASE OFFLINE: Please check your vector database connections.",
            "detected_crop": "Error State",
            "detected_issue": "Error State"
        }
    
    if results and len(results) > 0:
        best_match = results[0].get('document', 'No explicit documentation found.')
        product_name = results[0].get('product_name', 'Agricultural Solution')
        detected_crop = results[0].get('detected_crop', 'Extracted from query')
        detected_issue = results[0].get('detected_issue', 'Extracted from query')
        
        return {
            "recommended_product": product_name,
            "reason": best_match,
            "safety_note": "Please strictly follow the professional dilution ratios and chemical safety guidelines in the official product manual.",
            "detected_crop": detected_crop,
            "detected_issue": detected_issue
        }
    
    return {
        "recommended_product": "Consult an agricultural expert",
        "reason": "No relevant product or matching agronomic record was found in our database for this specific query.",
        "safety_note": "Please check product label instructions and regional safety regulations before speculative use.",
        "detected_crop": "Unknown",
        "detected_issue": "Unknown"
    }