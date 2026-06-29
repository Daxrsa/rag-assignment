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
# - SIMILARITY_THRESHOLD_TOP1: softer floor applied ONLY to the top-1 chunk, so a single
#   strong-but-borderline match (e.g. a colloquial paraphrase of corpus wording) still gets through
# - MAX_HISTORY_TURNS: how many prior (question, answer) pairs to keep for query rewriting
RETRIEVAL_K = 6
SIMILARITY_THRESHOLD = 0.30
SIMILARITY_THRESHOLD_TOP1 = 0.25
MAX_HISTORY_TURNS = 5

# verification (third LLM call, gated to high-impact answers only)
# Weak retrieval = top score below SIMILARITY_THRESHOLD (i.e. we only kept a chunk
# via the softer SIMILARITY_THRESHOLD_TOP1 floor).
# - VERIFY_MIN_CHUNKS: if fewer than this many chunks passed the threshold, evidence
#   is sparse and verification is triggered
# - VERIFY_QUESTION_LEN: questions longer than this (chars) are treated as high-impact
VERIFY_MIN_CHUNKS = 2
VERIFY_QUESTION_LEN = 120

# models (shared singletons)
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")
