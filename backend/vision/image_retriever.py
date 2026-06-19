"""
Image retriever for similar crop disease images from ChromaDB.
"""

from pathlib import Path
from typing import Dict, Any

import chromadb

from backend.vision.config import config
from backend.vision.image_embeddings import clip_embeddings


class ImageRetriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=config.chromadb_path
        )

        try:
            self.collection = self.client.get_collection(
                config.retrieval.image_collection
            )

        except Exception as error:
            raise RuntimeError(
                f"Image collection not found: {config.retrieval.image_collection}"
            ) from error

    def search_by_image(self, image_path: str, k: int = 5) -> Dict[str, Any]:
        image_path_object = Path(image_path)

        if not image_path_object.exists():
            return {
                "success": False,
                "message": f"Image file not found: {image_path}",
                "results": None,
            }

        embedding = clip_embeddings.embed_image(image_path_object)

        results = self.collection.query(
            query_embeddings=[embedding.tolist()],
            n_results=k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        return {
            "success": True,
            "matches": len(results["ids"][0]) if results.get("ids") else 0,
            "results": results,
        }

    def diagnose(self, image_path: str, k: int = 5) -> Dict[str, Any]:
        search = self.search_by_image(
            image_path=image_path,
            k=k,
        )

        if not search["success"]:
            return search

        results = search["results"]

        if not results["ids"] or not results["ids"][0]:
            return {
                "success": False,
                "message": "No similar images found.",
            }

        best_metadata = results["metadatas"][0][0]
        best_id = results["ids"][0][0]
        best_distance = results["distances"][0][0]

        similarity_score = max(
            0.0,
            min(1.0, 1 - float(best_distance)),
        )

        top_matches = []

        for index in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][index]
            distance = results["distances"][0][index]

            score = max(
                0.0,
                min(1.0, 1 - float(distance)),
            )

            top_matches.append(
                {
                    "image_id": results["ids"][0][index],
                    "crop": metadata.get("crop"),
                    "disease": metadata.get("disease"),
                    "disease_type": metadata.get("disease_type"),
                    "confidence": round(score, 4),
                    "distance": round(float(distance), 4),
                }
            )

        return {
            "success": True,
            "image_id": best_id,
            "crop": best_metadata.get("crop"),
            "disease": best_metadata.get("disease"),
            "disease_type": best_metadata.get("disease_type"),
            "confidence": round(similarity_score, 4),
            "matches": len(results["ids"][0]),
            "top_matches": top_matches,
        }


image_retriever = ImageRetriever()