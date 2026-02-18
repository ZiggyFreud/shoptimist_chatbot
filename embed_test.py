print("RUNNING FILE")

import os
from dotenv import load_dotenv
import voyageai

load_dotenv()

print("After load_dotenv")

api_key = os.getenv("VOYAGE_API_KEY")
print("API key:", api_key)

vo = voyageai.Client(api_key=api_key)

result = vo.embed(
    texts=["Hello world"],
    model="voyage-3-large",
    input_type="document"
)

print("Embedding:", result.embeddings[0][:5])
