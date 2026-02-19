import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic
import voyageai
import chromadb

load_dotenv()

app = Flask(__name__)
CORS(app)

MODEL = "claude-3-haiku-20240307"
MAX_TOKENS = 600

vo = voyageai.Client()
chroma_client = chromadb.PersistentClient(path="chroma_db")
col = chroma_client.get_or_create_collection(name="website")

def get_relevant_context(query: str, n_results: int = 5) -> str:
    embedding = vo.embed([query], model="voyage-3-large", input_type="query").embeddings[0]
    results = col.query(query_embeddings=[embedding], n_results=n_results)
    chunks = results["documents"][0]
    urls = [m["url"] for m in results["metadatas"][0]]
    context_parts = []
    for chunk, url in zip(chunks, urls):
        context_parts.append(f"Source: {url}\n{chunk}")
    return "\n\n---\n\n".join(context_parts)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        context = get_relevant_context(user_message)
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=api_key)
        
        system_prompt = """You are a helpful assistant for Shoptimist USA (shoptimistusa.com).
Use the context to give a helpful, specific answer. Extract and summarize relevant information even if it's not perfectly organized.
Always be friendly and helpful."""
        
        full_message = f"""Use the following content from the Shoptimist USA website to answer the question.

CONTEXT:
{context}

QUESTION: {user_message}"""
        
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": full_message}],
        )
        
        bot_text = "".join(
            block.text for block in response.content
            if block.type == "text"
        )
        
        return jsonify({'response': bot_text})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'chunks': col.count(), 'path': os.path.abspath('chroma_db')})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
