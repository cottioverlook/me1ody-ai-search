import numpy as np
import faiss

from app.services.embeddings import EmbeddingService


class VectorStore:
    """基于 FAISS 的内存向量库，用于搜索结果的向量检索。

    面试话术：
    - 为什么选 FAISS：Facebook 开源的向量检索库，纯本地运行，
      支持高效的近似最近邻搜索（ANN），不需要额外的数据库服务。
    - 为什么不用 Pinecone/Weaviate：考研项目不需要云端向量数据库，
      FAISS 零部署成本，而且 IVFFlat 索引在万级数据量下性能完全够用。
    - 索引选型：数据量小（几十到几百条）用 Flat 暴力搜索，
      数据量大（万级以上）用 IVFFlat 分区加速。
    """

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.index: faiss.IndexFlatIP | None = None
        self.texts: list[str] = []
        self.metadata: list[dict] = []

    def add(self, texts: list[str], metadata: list[dict] | None = None):
        """添加文本到向量库。

        Args:
            texts: 文本列表
            metadata: 每条文本对应的元数据（标题、URL 等）
        """
        if not texts:
            return
        if metadata is not None and len(metadata) != len(texts):
            raise ValueError("metadata length must match texts length")

        embeddings = self.embedding_service.encode(texts)
        if embeddings.ndim != 2 or embeddings.shape[0] != len(texts):
            raise ValueError("embedding service returned an invalid shape")

        if self.index is None:
            dim = embeddings.shape[1]
            # IndexFlatIP = 内积索引（向量已归一化，内积=余弦相似度）
            self.index = faiss.IndexFlatIP(dim)

        self.index.add(embeddings.astype(np.float32))
        self.texts.extend(texts)
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{}] * len(texts))

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """检索与查询最相似的文本。

        Returns:
            [{"text": ..., "score": ..., "metadata": ...}, ...]
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        query_embedding = self.embedding_service.encode_single(query)
        query_vec = query_embedding.reshape(1, -1).astype(np.float32)

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append({
                "text": self.texts[idx],
                "score": float(score),
                "metadata": self.metadata[idx],
            })

        return results

    def clear(self):
        """清空向量库，释放内存。"""
        self.index = None
        self.texts = []
        self.metadata = []

    @property
    def size(self) -> int:
        return self.index.ntotal if self.index else 0
