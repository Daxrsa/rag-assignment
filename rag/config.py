from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()

# corpus + vector store
DATA_DIR = "/Users/daorsa/Documents/Software/rag-assignment/sample_documents"
CHROMA_DIR = "/Users/daorsa/Documents/Software/rag-assignment/.chroma"
COLLECTION_NAME = "rag_assignment"
FILE_PATTERNS = ["**/*.txt", "**/*.md"]

# chunking
CHUNK_SIZE = 400
CHUNK_OVERLAP = 200

# retrieval
# - RETRIEVAL_K: how many candidate chunks to pull
# - SIMILARITY_THRESHOLD: cosine similarity floor; raise to reduce noise, lower to reduce refusals
# - MAX_HISTORY_TURNS: how many prior (question, answer) pairs to keep for query rewriting
RETRIEVAL_K = 6
SIMILARITY_THRESHOLD = 0.30
MAX_HISTORY_TURNS = 5

# models (shared singletons)
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
