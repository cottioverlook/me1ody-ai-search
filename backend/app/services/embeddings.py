import hashlib
import os

import numpy as np

SentenceTransformer = None


class EmbeddingService:
    """基于 BGE-small-zh-v1.5 的中文 Embedding 服务。

    面试话术：
    - 为什么选 BGE 系列：在 MTEB 中文排行榜上表现优异，模型体积小（~90MB），
      推理速度快，适合本地部署的项目。
    - 为什么不用 OpenAI Embedding：调用 API 有延迟和成本，
      本地模型可以做到零成本、低延迟、数据不出本地。
    """

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5", backend: str | None = None):
        self.backend = backend or os.getenv("EMBEDDING_BACKEND", "sentence_transformers")
        self.model = None
        self.dim = 384
        if self.backend == "sentence_transformers":
            # 首次加载会自动从 HuggingFace 下载模型；Docker 可用 hash 后端避免重模型构建。
            global SentenceTransformer
            if SentenceTransformer is None:
                from sentence_transformers import SentenceTransformer as _SentenceTransformer
                SentenceTransformer = _SentenceTransformer
            self.model = SentenceTransformer(model_name)
        self._cache: dict[str, np.ndarray] = {}

    def encode(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        """批量编码文本为向量。

        Args:
            texts: 文本列表
            normalize: 是否归一化（归一化后点积=余弦相似度）

        Returns:
            shape=(n, dim) 的 numpy 数组
        """
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        # 检查缓存，避免重复编码
        results: list[np.ndarray | None] = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text, normalize)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        # 批量编码未缓存的文本
        if uncached_texts:
            embeddings = (
                self._encode_hash(uncached_texts, normalize)
                if self.backend == "hash"
                else self.model.encode(
                    uncached_texts,
                    normalize_embeddings=normalize,
                    show_progress_bar=False,
                    batch_size=32,
                )
            )
            for j, original_index in enumerate(uncached_indices):
                text = texts[original_index]
                vector = embeddings[j]
                cache_key = self._get_cache_key(text, normalize)
                self._cache[cache_key] = vector
                results[original_index] = vector

        # 按原始顺序排列
        return np.array(results)

    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """编码单个文本。"""
        return self.encode([text], normalize=normalize)[0]

    def _encode_hash(self, texts: list[str], normalize: bool) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = [text[i : i + 2] for i in range(max(1, len(text) - 1))]
            if not tokens:
                tokens = [text]
            for token in tokens:
                digest = hashlib.md5(token.encode()).digest()
                index = int.from_bytes(digest[:4], "little") % self.dim
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vectors[row, index] += sign
        if normalize:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / np.maximum(norms, 1e-8)
        return vectors

    @staticmethod
    def _get_cache_key(text: str, normalize: bool) -> str:
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{int(normalize)}:{text_hash}"
