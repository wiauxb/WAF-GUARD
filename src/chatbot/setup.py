from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT



# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB_CWAF = os.getenv("POSTGRES_DB_CWAF", "cwaf")
POSTGRES_DB_CHATBOT = os.getenv("POSTGRES_DB_CHATBOT", "chatbot")



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



def ensure_database_exists(
    db_name,
    user='postgres',
    password='your_password',
    host='localhost',
    port=5432
):
    # Connect to the default 'postgres' database with environment-based SSL
    if ENVIRONMENT == "prod":
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=POSTGRES_DB_CWAF,
            sslmode='require'
        )
    else:
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=POSTGRES_DB_CWAF
        )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Check if the database exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    exists = cursor.fetchone()

    if not exists:
        print(f"Database '{db_name}' does not exist. Creating it...")
        cursor.execute(f'CREATE DATABASE "{db_name}"')
    else:
        print(f"Database '{db_name}' already exists.")

    cursor.close()
    conn.close()





#check if the database is populated if the folder /chromadb contains data
if not os.path.exists("/chromadb/chroma.sqlite3"):
    print("Vector Database does not exist, populating...")
    populate_db()
else:
    print("Vector Database already exists")

ensure_database_exists(
    db_name=POSTGRES_DB_CHATBOT,
    user=DB_USER,
    password=DB_PASSWORD,
    host="postgres",
    port=5432
)