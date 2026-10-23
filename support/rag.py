import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

#Initialize chromadb client
client = chromadb.PersistentClient(path="./chroma_db")
embedding_fn = DefaultEmbeddingFunction() # We will need this function later when we want to convert our chunks or our text into numbers (vectors)

#Get or create the  - just like table in regular db
collection = client.get_or_create_collection(
  name="coolbreze_docs", #This will be the "table name"
  embedding_function = embedding_fn
  )



def chunk_text(text, chunk_size = 500):
  words = text.split()
  current_chunk = []
  chunk = []
  size = 0

  for word in words:
    current_chunk.append(word)
    size += len(word) + 1

    if size > chunk_size:
      chunk.append(" ".join(current_chunk))
      size = 0
      current_chunk = []

  if current_chunk:
    chunk.append(" ".join(current_chunk))
  
  return chunk

  


