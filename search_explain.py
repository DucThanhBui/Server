from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.core import Settings
import os
from sentence_transformers import SentenceTransformer
from llama_index.core import VectorStoreIndex
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.prompts import PromptTemplate

from llama_index.core import get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine




# Setting global parameter
#Settings.embed_model = HuggingFaceEmbedding('BAAI/bge-large-en-v1.5', trust_remote_code=True)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")
#Settings.llm = Gemini(model_name="models/gemini-pro")
Settings.llm = OpenAI(model="gpt-4o-mini")




def load_and_storage(fileName: str):
    documents = SimpleDirectoryReader(input_files=[f'uploads/{fileName}.epub']).load_data()
    text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=10)
    Settings.text_splitter = text_splitter
    index = VectorStoreIndex.from_documents(documents, transformations=[text_splitter])
    index.storage_context.persist(persist_dir=f"/{fileName}")




def search(fileName: str, input: str):
    # rebuild storage context
    print(f"search from storage fileName: {fileName}")
    storage_context = StorageContext.from_defaults(persist_dir=f"/{fileName}")

    # load index
    index = load_index_from_storage(storage_context)

    template = """
    Use the provided context to answer the query. If no context is provided, answer the question using your internal knowledge to the best of your ability.

    This is question and context for you.

    Do not provide additional instructions or explanations.\n\n

    \\Câu hỏi: {question} \nContext: {context} \nAnswer:"""



    prompt_tmpl = PromptTemplate(
        template=template,
        template_var_mappings={"query_str": "question", "context_str": "context"},
    )
    # configure retriever
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=3,
        verbose=True
    )
    # configure response synthesizer
    response_synthesizer = get_response_synthesizer()

    # assemble query engine
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )

    query_engine.update_prompts(
        {"response_synthesizer:text_qa_template":prompt_tmpl}
    )


    ## Input
    query = ""
    # if len(input) < 15
    response = query_engine.query(f"tìm thông tin về {input}")
    # print("res is: ")
    # print(response)

    # print("+++++++++++++++++")
    # context = " ".join([node.dict()['node']['text'] for node in response.source_nodes])
    # print(context)
    return str(response)


if __name__ == "__main__":
    fileName = "Ác Ý - Higashino Keigo"
    load_and_storage(fileName)
    print(search(fileName))