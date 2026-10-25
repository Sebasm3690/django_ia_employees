import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
import os
from pypdf import PdfReader

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



def load_documents():
  docs_path = "support/documents/"

  documents = []
  ids = []

  for filename in os.listdir(docs_path): #Will list all the files inside this path ""support/documents/"" -> refund_policy.pdf
    if filename.endswith(".pdf"):
      #filepath: support/documents/refund_policy.pdf
      #docs_path: "support/documents/"
      #filename: "refund_policy.pdf"
      filepath = os.path.join(docs_path,filename)
      reader = PdfReader(filepath) #Reader will give us access to each and every page of a pdf file

      raw_text = ""
      for page in reader.pages: #We are going to extract the text from each page and we are going to put in a variable
        raw_text += page.extract_text()
      
      chunks = chunk_text(raw_text, chunk_size=500)

      for i,chunk in enumerate(chunks): #enumerate allows to lopp through index numbers
        documents.append(chunk)
        ids.append(f"{filename}_{i}")
  
  if documents:
    collection.add(documents=documents, ids=ids)

    print(f"Loaded {len(documents)} chunks into ChromaDB")
    

def search_knowledge_base(query): #User question
  results = collection.query(query_texts=[query], n_results=3) #database query #Get top 3 results
  
  if not results["documents"][0]:
    return "No relevant information found in company documents. "
  
  matched_chunks = results["documents"][0]
  return "\n\n".join(matched_chunks)


"""
matched_chunks = [
  "Refund requests must be submitted within 30 days of delivery.",
  "Customers must provide proof of purchase to be eligible for a refund.",
  "Refunds will be processed within 5-7 business days.",
]

----We will return like this:

Refund requests must be submitted within 30 days of delivery.

Customers must provide proof of purchase to be eligible for a refund.

Refunds will be processed within 5-7 business days.


"""
  


  







      


      



  


