from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter
from dotenv import load_dotenv
import os

load_dotenv()




## Read markdown file and split by headers
def read_markdown_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        markdown_text = file.read()
    return markdown_text

def populate_db():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vector_store = Chroma(
    collection_name="ModSecurity_documentation",
    embedding_function=embeddings,
    persist_directory="/chromadb",  # Where to save data locally, remove if not necessary
    )


    markdown_document = read_markdown_file("doc.md")
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(markdown_document)
    vector_store.add_documents(md_header_splits)

#check if the database is populated if the folder /chromadb contains data
if not os.path.exists("/chromadb/chroma.sqlite3"):
    print("Database does not exist, populating...")
    populate_db()
else:
    print("Database already exists")