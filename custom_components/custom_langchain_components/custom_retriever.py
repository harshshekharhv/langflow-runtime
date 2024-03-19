from langchain.schema.retriever import BaseRetriever
from langchain.docstore.document import Document
from typing import List, Optional
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from custom_components.embedding_svc_client import EmbeddingSVC


class CustomRetriever(BaseRetriever, EmbeddingSVC):
    base_url: str
    endpoint: Optional[str] = "get-embeddings"
    score_threshold: Optional[float] = None
    filter_options: Optional[dict] = {},
    collection_name: str
    top_k: int
    user_collection_name: str
    master_collection_name: str

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        """
        _get_relevant_documents is function of BaseRetriever implemented here

        :param query: String value of the query

        """

        response = self.query_db(
            endpoint=self.endpoint,
            query=query,
            filter_options=self.filter_options,
            collection_name=self.collection_name,
            limit=self.top_k,
            user_collection_name=self.user_collection_name,
            master_collection_name=self.master_collection_name,
            score_threshold=self.score_threshold)

        result_docs = list()
        for c, i in enumerate(response['embeddings']):
            doc = Document(page_content=i["page_content"], metadata=i["metadata"])
            result_docs.append(doc)
        return result_docs


if __name__ == "__main__":
    retriever = CustomRetriever(
        base_url="https://genai-embedding-svc.genai.sc.eng.hitachivantara.com/api/v1",
        score_threshold=0.4,
        filter_options={},
        collection_name='demo_hcp_master',
        top_k=10,
        user_collection_name='demo_hcp_master',
        master_collection_name='demo_hcp_master'
    )

    result = retriever.get_relevant_documents(query="How to delete S series node?")
