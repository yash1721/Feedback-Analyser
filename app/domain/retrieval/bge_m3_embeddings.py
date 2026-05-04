from app.domain.retrieval.sentence_transformer_embeddings import SentenceTransformerEmbeddingModel


class BGEM3EmbeddingModel(SentenceTransformerEmbeddingModel):
    """BGE-M3 dense embedding provider.

    SentenceTransformer loading stays lazy in the parent class, so importing this
    module does not download or load the model.
    """
