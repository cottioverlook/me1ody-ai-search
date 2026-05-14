from sentence_transformers import CrossEncoder


class RerankerService:
    """基于 Cross-Encoder 的精排服务。

    面试话术：
    - 为什么需要 Reranker：Bi-Encoder（Embedding）做粗排速度快但精度有限，
      Cross-Encoder 将 query 和 document 拼接后一起编码，能捕获更细粒度的语义交互。
    - 两级召回策略：粗排（Embedding + FAISS）从全量候选中快速筛选 Top-N，
      精排（Cross-Encoder）对 Top-N 做精细打分，取 Top-K。
    - 这是工业界信息检索的标准做法（Google/Bing 的多阶段排序也是如此）。
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        # 首次加载会自动下载模型
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """对候选文档做精排重排序。

        Args:
            query: 用户查询
            documents: 候选文档列表，每个 dict 需包含 "text" 字段
            top_k: 返回 top_k 个结果

        Returns:
            按精排分数降序排列的文档列表，每个 dict 增加 "rerank_score" 字段
        """
        if not documents:
            return []

        # 构造 (query, document) 对
        pairs = [(query, doc["text"]) for doc in documents]

        # Cross-Encoder 打分
        scores = self.model.predict(pairs)

        # 将分数附加到文档上
        scored_docs = []
        for doc, score in zip(documents, scores):
            scored_docs.append({
                **doc,
                "rerank_score": float(score),
            })

        # 按精排分数降序排列
        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored_docs[:top_k]
