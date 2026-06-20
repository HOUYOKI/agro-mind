# src/retrieval_tool.py - LangChain compatible version
"""Retrieval tool for AgroMind - LangChain compatible"""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.config import config
from src.embeddings import ollama_embeddings


class OllamaEmbeddingsWrapper(Embeddings):
    """
    Wrapper to make the local Ollama embedding function compatible with LangChain.
    """

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """LangChain calls this for document embeddings."""
        return ollama_embeddings(texts)

    def embed_query(self, text: str) -> List[float]:
        """LangChain calls this for query embeddings."""
        return ollama_embeddings.embed_query(text)


class AgroMindRetriever:
    """
    Hybrid retriever for Agro-Mind.

    Supports:
    - exact product ID lookup
    - exact crop/disease/symptom keyword matching from clean_entities.json
    - vector search through ChromaDB
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        collection_name: Optional[str] = None,
        entities_path: Optional[str] = None,
    ):
        db_path = db_path or config.chromadb_path
        collection_name = collection_name or config.retrieval.full_collection
        entities_path = entities_path or str(Path(config.data_path) / "clean_entities.json")

        self.db_path = db_path
        self.collection_name = collection_name
        self.entities_path = Path(entities_path)

        self.embeddings = OllamaEmbeddingsWrapper()

        self.vectorstore = Chroma(
            persist_directory=self.db_path,
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
        )

        self._load_entities()
        self._cache: Dict[str, List[Tuple[Document, float]]] = {}

    def _load_entities(self) -> None:
        """Load product entities for exact and structured matching."""
        if self.entities_path.exists():
            with open(self.entities_path, "r", encoding="utf-8") as file:
                entities = json.load(file)

            self.product_by_id = {
                entity["product_id"].upper(): entity
                for entity in entities
                if entity.get("product_id")
            }

            self.product_names = {
                entity["product_id"].upper(): entity.get(
                    "name_cn",
                    entity.get("name_en", entity.get("name", "")),
                )
                for entity in entities
                if entity.get("product_id")
            }

            self.product_diseases: Dict[str, List[str]] = {}

            for entity in entities:
                product_id = entity.get("product_id", "").upper()
                diseases = entity.get("target_diseases", [])

                for disease in diseases:
                    if disease not in self.product_diseases:
                        self.product_diseases[disease] = []
                    self.product_diseases[disease].append(product_id)

        else:
            print(f"Warning: Entities file not found at {self.entities_path}")
            self.product_by_id = {}
            self.product_names = {}
            self.product_diseases = {}

    def _extract_structured_terms(self, query: str) -> Dict[str, List[str]]:
        """
        Convert common English agriculture terms into the Chinese terms used
        inside clean_entities.json.

        This improves queries like:
        - citrus root rot
        - tomato blight
        - cucumber downy mildew
        - aphids on cabbage
        """
        q = query.lower()

        crop_map = {
            "citrus": ["柑橘"],
            "orange": ["柑橘"],
            "tomato": ["番茄", "西红柿"],
            "pepper": ["辣椒"],
            "chili": ["辣椒"],
            "rice": ["水稻"],
            "wheat": ["小麦"],
            "corn": ["玉米"],
            "maize": ["玉米"],
            "cucumber": ["黄瓜"],
            "strawberry": ["草莓"],
            "cabbage": ["白菜", "甘蓝"],
            "kale": ["甘蓝"],
            "garlic": ["大蒜"],
            "ginger": ["生姜"],
            "onion": ["大葱"],
            "eggplant": ["茄子"],
            "watermelon": ["西瓜"],
            "melon": ["甜瓜", "哈密瓜"],
            "apple": ["苹果"],
            "pear": ["梨"],
            "peach": ["桃"],
            "grape": ["葡萄"],
            "cotton": ["棉花"],
            "soybean": ["大豆"],
            "peanut": ["花生"],
            "tea": ["茶树", "茶叶"],
        }

        disease_map = {
            "root rot": ["根腐病", "根腐"],
            "rotten root": ["根腐病", "烂根"],
            "rot": ["腐烂", "软腐病", "根腐病"],
            "canker": ["溃疡病"],
            "anthracnose": ["炭疽病"],
            "powdery mildew": ["白粉病"],
            "downy mildew": ["霜霉病"],
            "gray mold": ["灰霉病"],
            "grey mold": ["灰霉病"],
            "leaf spot": ["叶斑病"],
            "blight": ["疫病", "早晚疫病"],
            "late blight": ["晚疫病", "早晚疫病", "疫病"],
            "early blight": ["早疫病", "早晚疫病", "疫病"],
            "wilt": ["枯萎病", "青枯病", "黄萎病"],
            "fusarium": ["枯萎病"],
            "soft rot": ["软腐病"],
            "bacterial": ["细菌病害"],
            "bacteria": ["细菌病害"],
            "fungal": ["真菌病害"],
            "fungus": ["真菌病害"],
            "virus": ["病毒"],
            "viral": ["病毒"],
            "rust": ["锈病"],
            "rice blast": ["稻瘟病"],
            "scab": ["疮痂病"],
            "leaf spot": ["叶斑病"],
            "black spot": ["黑斑病", "叶斑病"],
            "black spots": ["黑斑病", "叶斑病"],
            "brown spot": ["褐斑病", "叶斑病"],
            "brown spots": ["褐斑病", "叶斑病"],
            "blight": ["疫病", "早晚疫病"],
        }

        pest_map = {
            "aphid": ["蚜虫"],
            "aphids": ["蚜虫"],
            "whitefly": ["白粉虱", "粉虱"],
            "whiteflies": ["白粉虱", "粉虱"],
            "thrips": ["蓟马"],
            "spider mite": ["红蜘蛛", "螨虫"],
            "spider mites": ["红蜘蛛", "螨虫"],
            "mite": ["螨虫", "红蜘蛛"],
            "mites": ["螨虫", "红蜘蛛"],
            "leaf miner": ["潜叶蝇", "斑潜蝇"],
            "caterpillar": ["菜青虫", "小菜蛾"],
            "caterpillars": ["菜青虫", "小菜蛾"],
            "borer": ["螟虫"],
            "planthopper": ["飞虱"],
            "snail": ["蜗牛"],
            "slug": ["蛞蝓"],
            "nematode": ["根结线虫", "胞囊线虫", "茎线虫"],
            "nematodes": ["根结线虫", "胞囊线虫", "茎线虫"],
        }

        symptom_map = {
            "yellow leaves": ["黄叶", "叶片黄化"],
            "yellow leaf": ["黄叶", "叶片黄化"],
            "yellowing": ["黄叶", "叶片黄化"],
            "chlorosis": ["黄叶", "叶片黄化"],
            "wither": ["萎蔫"],
            "wilting": ["萎蔫"],
            "dead seedling": ["死苗", "死棵"],
            "dead seedlings": ["死苗", "死棵"],
            "rotten root": ["烂根"],
            "rotten roots": ["烂根"],
            "black root": ["黑根"],
            "black roots": ["黑根"],
            "weak seedling": ["弱苗"],
            "weak seedlings": ["弱苗"],
            "stunted": ["矮化", "僵苗"],
            "dwarf": ["矮化"],
            "curled leaves": ["卷叶"],
            "curling leaves": ["卷叶"],
            "leaf curl": ["卷叶"],
            "spots": ["叶斑病"],
            "leaf spots": ["叶斑病"],
            "black spot": ["黑斑病", "叶斑病"],
            "black spots": ["黑斑病", "叶斑病"],
            "brown spot": ["褐斑病", "叶斑病"],
            "brown spots": ["褐斑病", "叶斑病"],
            "leaf lesion": ["叶斑病"],
            "leaf lesions": ["叶斑病"],
            "dark spots": ["黑斑病", "叶斑病"],
            "black patches": ["黑斑病"],
        }

        crops = []
        diseases = []
        pests = []
        symptoms = []

        for english, chinese_terms in crop_map.items():
            if english in q:
                crops.extend(chinese_terms)

        for english, chinese_terms in disease_map.items():
            if english in q:
                diseases.extend(chinese_terms)

        for english, chinese_terms in pest_map.items():
            if english in q:
                pests.extend(chinese_terms)

        for english, chinese_terms in symptom_map.items():
            if english in q:
                symptoms.extend(chinese_terms)

        return {
            "crops": list(set(crops)),
            "diseases": list(set(diseases)),
            "pests": list(set(pests)),
            "symptoms": list(set(symptoms)),
        }

    def _structured_keyword_search(self, query: str, k: int) -> List[Tuple[Document, float]]:
        """
        Search clean_entities.json directly using structured fields:
        - target_crops
        - target_diseases
        - target_pests
        - symptoms_addressed

        We use negative scores so stronger structured matches appear before vector scores.
        """
        terms = self._extract_structured_terms(query)



        if (
           not terms["crops"]
           and not terms["diseases"]
           and not terms["pests"]
           and not terms["symptoms"]
       ):
          return []

        scored_results = []

        for product_id, entity in self.product_by_id.items():
            score = 0

            crops = entity.get("target_crops", [])
            diseases = entity.get("target_diseases", [])
            pests = entity.get("target_pests", [])
            symptoms = entity.get("symptoms_addressed", [])

            for crop in terms["crops"]:
                if crop in crops:
                    score += 2

            for disease in terms["diseases"]:
                if disease in diseases:
                    score += 10

            for pest in terms["pests"]:
                if pest in pests:
                    score += 10

            for symptom in terms["symptoms"]:
                if symptom in symptoms:
                    score += 4

            if score > 0:
                # Prefer products that actually target diseases/pests.
                if terms["diseases"] and entity.get("has_diseases"):
                    score += 1

                if terms["pests"] and entity.get("has_pests"):
                    score += 1

                # Prefer pesticide/microbial products when asking disease/pest treatment.
                if (terms["diseases"] or terms["pests"]) and (
                    entity.get("is_pesticide") or entity.get("is_microbial")
                ):
                    score += 1

                # Slightly penalize fertilizer-only products when the user asks disease/pest treatment.
                if (terms["diseases"] or terms["pests"]) and entity.get("is_fertilizer"):
                    score -= 1

                doc = self._create_document_from_entity(entity)

                # Negative = better than vector distance in merged sorting.
                scored_results.append((doc, -float(score)))

        scored_results.sort(key=lambda item: item[1])
        return scored_results[:k]

    def search(
        self,
        query: str,
        k: int = 10,
        use_hybrid: bool = True,
    ) -> List[Tuple[Document, float]]:
        """
        Hybrid search:
        1. Exact product ID lookup
        2. Structured crop/disease/pest/symptom match from clean_entities.json
        3. Vector search from ChromaDB
        4. Merge results without duplicates
        """
        query = query.strip()
        cache_key = f"{query}_{k}_{use_hybrid}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        results: List[Tuple[Document, float]] = []
        seen_ids = set()

        query_upper = query.upper()

        # 1. Exact product ID match.
        if use_hybrid and query_upper in self.product_by_id:
            product = self.product_by_id[query_upper]
            exact_doc = self._create_document_from_entity(product)

            results.append((exact_doc, 1.0))
            seen_ids.add(query_upper)

        # 2. Structured keyword match from clean_entities.json.
        if use_hybrid:
            structured_results = self._structured_keyword_search(query, k=k)

            for doc, score in structured_results:
                product_id = str(doc.metadata.get("product_id", "")).upper()

                if product_id and product_id not in seen_ids:
                    results.append((doc, score))
                    seen_ids.add(product_id)

                if len(results) >= k:
                    self._cache[cache_key] = results
                    return results

        # 3. Vector search from ChromaDB.
        vector_results = self.vectorstore.similarity_search_with_score(query, k=k * 2)

        for doc, score in vector_results:
            product_id = str(doc.metadata.get("product_id", "")).upper()

            if product_id and product_id not in seen_ids:
                results.append((doc, score))
                seen_ids.add(product_id)

            if len(results) >= k:
                break

        self._cache[cache_key] = results
        return results

    def search_by_disease(
        self,
        disease: str,
        k: int = 10,
    ) -> List[Tuple[Document, float]]:
        """Search for products that control a specific disease."""
        disease = disease.strip()

        if disease in self.product_diseases:
            exact_products = self.product_diseases[disease]
            results: List[Tuple[Document, float]] = []
            seen_ids = set()

            for product_id in exact_products[:k]:
                product_id = product_id.upper()

                if product_id in self.product_by_id:
                    doc = self._create_document_from_entity(self.product_by_id[product_id])
                    results.append((doc, 1.0))
                    seen_ids.add(product_id)

            remaining = k - len(results)

            if remaining > 0:
                vector_results = self.vectorstore.similarity_search_with_score(
                    f"Controls {disease}",
                    k=remaining * 2,
                )

                for doc, score in vector_results:
                    product_id = str(doc.metadata.get("product_id", "")).upper()

                    if product_id not in seen_ids:
                        results.append((doc, score))
                        seen_ids.add(product_id)

                    if len(results) >= k:
                        break

            return results[:k]

        return self.vectorstore.similarity_search_with_score(
            f"Controls {disease}",
            k=k,
        )

    def search_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product by exact ID."""
        product_id = product_id.strip().upper()
        return self.product_by_id.get(product_id)

    def get_product_info(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed product information by ID."""
        return self.search_by_id(product_id)

    def search_by_ingredient(
        self,
        ingredient: str,
        k: int = 10,
    ) -> List[Tuple[Document, float]]:
        """Search for products containing a specific ingredient."""
        return self.vectorstore.similarity_search_with_score(
            f"Ingredients: {ingredient}",
            k=k,
        )

    def search_by_crop(
        self,
        crop: str,
        k: int = 10,
    ) -> List[Tuple[Document, float]]:
        """Search for products that work on a specific crop."""
        return self.vectorstore.similarity_search_with_score(
            f"Crops: {crop}",
            k=k,
        )

    def _create_document_from_entity(self, entity: Dict[str, Any]) -> Document:
        """Create a LangChain Document from an entity dictionary."""
        product_id = entity.get("product_id", "")
        name_cn = entity.get("name_cn", "")
        name_en = entity.get("name_en", "")
        diseases = entity.get("target_diseases", [])
        crops = entity.get("target_crops", [])
        pests = entity.get("target_pests", [])
        ingredients = entity.get("active_ingredients", [])
        symptoms = entity.get("symptoms_addressed", [])

        text_parts = [
            f"Product ID: {product_id}",
            f"Chinese Name: {name_cn}",
            f"English Name: {name_en}",
        ]

        if crops:
            text_parts.append(f"Crops: {', '.join(crops)}")

        if diseases:
            text_parts.append(f"Diseases: {', '.join(diseases)}")

        if pests:
            text_parts.append(f"Pests: {', '.join(pests)}")

        if ingredients:
            text_parts.append(f"Ingredients: {', '.join(ingredients)}")

        if symptoms:
            text_parts.append(f"Symptoms addressed: {', '.join(symptoms)}")

        return Document(
            page_content="\n".join(text_parts),
            metadata={
                "product_id": product_id,
                "name_cn": name_cn,
                "name_en": name_en,
                "diseases": diseases,
                "crops": crops,
                "pests": pests,
                "ingredients": ingredients,
                "symptoms": symptoms,
            },
        )

    def clear_cache(self) -> None:
        """Clear the search cache."""
        self._cache.clear()


def create_rag_tool(retriever: AgroMindRetriever):
    """Create a LangChain tool from the retriever."""

    try:
        from langchain_core.tools import Tool
    except ImportError:
        from langchain.tools import Tool

    def search_func(query: str) -> str:
        results = retriever.search(query, k=3)

        if not results:
            return "No relevant products found in the AgroMind knowledge base."

        context = "Relevant products from AgroMind knowledge base:\n\n"

        for index, (doc, score) in enumerate(results, 1):
            metadata = doc.metadata or {}

            name_cn = metadata.get("name_cn", "Unknown Chinese name")
            name_en = metadata.get("name_en", "Unknown English name")
            product_id = metadata.get("product_id", "Unknown ID")

            context += f"{index}. {name_cn} / {name_en} (ID: {product_id})\n"
            context += f"{doc.page_content}\n"
            context += f"Retrieval score: {score:.4f}\n\n"

        return context

    return Tool(
        name="AgroMind_Product_Search",
        func=search_func,
        description=(
            "Search the AgroMind agricultural product database. "
            "Use this tool when farmers ask about disease treatments, pest control, "
            "product information by ID, crop-specific treatments, symptoms, or active ingredients. "
            "Input should be a natural language query about agricultural products or diseases. "
            "Output is a list of relevant products with details and retrieval scores."
        ),
    )


if __name__ == "__main__":
    print("=" * 60)
    print("TESTING AGROMIND RETRIEVER (LangChain Compatible)")
    print("=" * 60)

    print(f"ChromaDB path: {config.chromadb_path}")
    print(f"Collection: {config.retrieval.full_collection}")
    print(f"Data path: {config.data_path}")

    retriever = AgroMindRetriever()

    print(f"Entities: {retriever.entities_path}")

    test_queries = [
        "citrus root rot treatment",
        "What treats citrus canker?",
        "tomato blight treatment",
        "aphids on cabbage",
        "AF0001",
    ]

    for test_query in test_queries:
        print(f"\nSearch: {test_query}")
        results = retriever.search(test_query, k=3)

        if not results:
            print("   No results found.")
            continue

        for doc, score in results:
            print(
                f"   {doc.metadata.get('product_id')}: "
                f"{doc.metadata.get('name_cn')} / {doc.metadata.get('name_en')} "
                f"(score: {score:.4f})"
            )

    print("\nExact product lookup 'AF0001':")
    product = retriever.get_product_info("AF0001")

    if product:
        print(
            f"   {product.get('product_id')}: "
            f"{product.get('name_cn')} / {product.get('name_en')}"
        )
    else:
        print("   Product not found.")

    print("\nTesting LangChain Tool:")
    tool = create_rag_tool(retriever)
    result = tool.func("What treats citrus canker?")
    print(result[:500] + "...")

    print("\n✅ Retriever ready for LangChain agent!")