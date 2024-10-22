import os
import bs4
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()
os.environ['OPENAI_API_KEY']=os.getenv("OPENAI_API_KEY")


#inserting the DATA into the Vectored database after converting it to embeddings 
loader=TextLoader("data.txt")
text_documents=loader.load()
text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
documents=text_splitter.split_documents(text_documents)
documents[:5]
db = Chroma.from_documents(documents,OpenAIEmbeddings())

loader=WebBaseLoader(web_paths=("https://lilianweng.github.io/posts/2023-06-23-agent/",),
                     bs_kwargs=dict(parse_only=bs4.SoupStrainer(
                         class_=("post-title","post-content","post-header")
                     )))
text_documents=loader.load()
text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
documents=text_splitter.split_documents(text_documents)
documents[:5]
db = Chroma.from_documents(documents,OpenAIEmbeddings())


loader=PyPDFLoader('data.pdf')
text_documents=loader.load()
text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
documents=text_splitter.split_documents(text_documents)
documents[:5]
db = Chroma.from_documents(documents,OpenAIEmbeddings())


query = "???????????????????????????????????"
retireved_results=db.similarity_search(query)
print(retireved_results[0].page_content)