"""
AgroMind Vision Configuration Loader.

This file is adapted for our backend structure:

backend/
├── config.yaml
├── vision/
│   └── config.py
└── vision_chromadb/
"""

from pathlib import Path
from functools import lru_cache
import os
from typing import Optional, Any, Dict

import yaml
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv


load_dotenv()


class ImageConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str
    normalize: bool = True


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: str
    model: str
    temperature: float
    max_tokens: int


class EmbeddingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: str
    model: str
    dimensions: int
    query_prefix: str
    doc_prefix: str
    normalize: bool = True


class RetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    structured_collection: str
    full_collection: str
    image_collection: str
    top_k: int = 5
    confidence_threshold: float = 0.85
    bm25_weight: float = 0.4
    vector_weight: float = 0.6
    hybrid_search: Optional[Dict[str, Any]] = None


class PathsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chromadb: str
    data: str
    logs: str
    escalations_log: str
    image_cache: str


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_retries: int = 2
    faithfulness_threshold: float = 0.75
    conversation_window: int = 4
    multimodal: Optional[Dict[str, Any]] = None


class LangSmithConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project: str
    endpoint: str = "https://api.smith.langchain.com"
    tracing_enabled: bool = True
    api_key: Optional[str] = None


class AgroMindConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    llm: LLMConfig
    embedding: EmbeddingConfig
    image: ImageConfig
    retrieval: RetrievalConfig
    paths: PathsConfig
    agent: AgentConfig
    langsmith: LangSmithConfig

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def chromadb_path(self) -> str:
        return str(self.backend_root / self.paths.chromadb)

    @property
    def data_path(self) -> str:
        return str(self.backend_root / self.paths.data)

    @property
    def logs_path(self) -> str:
        path = self.backend_root / self.paths.logs
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def escalations_log_path(self) -> str:
        return str(self.backend_root / self.paths.escalations_log)


@lru_cache(maxsize=1)
def load_config() -> AgroMindConfig:
    config_path = Path(__file__).resolve().parents[1] / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")

    with open(config_path, encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    loaded_config = AgroMindConfig(**raw)

    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    if api_key:
        loaded_config.langsmith.api_key = api_key

    tracing = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
    loaded_config.langsmith.tracing_enabled = tracing

    return loaded_config


config = load_config()