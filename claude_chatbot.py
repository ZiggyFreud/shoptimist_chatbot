import os
from dotenv import load_dotenv
import anthropic
import voyageai
import chromadb

load_dotenv()

MODEL = "claude-3-haiku-20240307"
MAX_TOKENS = 600

def get_relevant_context(query: str, vo, col, n_results: int = 5) -> str:
    embedding = vo.embed([query], model="voyage-3-large", input_type="query").embeddings[0]
    results = col.query(query_embeddings=[embedding], n_results=n_results)
    chunks = results["documents"][0]
    urls = [m["url"] for m in results["metadatas"][0]]
    context_parts = []
    for chunk, url in zip(chunks, urls):
        context_parts.append(f"Source: {url}\n{chunk}")
    return "\n\n---\n\n".join(context_parts)

def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not found in .env file.")
        return

    client = anthropic.Anthropic(api_key=api_key)
    vo = voyageai.Client()

    chroma_client = chromadb.PersistentClient(path="chroma_db")
    col = chroma_client.get_or_create_collection(name="website")

    system_prompt = """You are a helpful assistant for Shoptimist USA (shoptimistusa.com).
Answer questions using only the context provided from the website.
If the context doesn't contain enough information to answer, say so honestly.
Always be friendly and helpful."""

    messages = []

    print("Shoptimist chatbot ready. Type 'exit' to quit.\n")

    while True:
        user_text = input("You: ").strip()

        if user_text.lower() in {"exit", "quit"}:
            break

        if not user_text:
            continue

        context = get_relevant_context(user_text, vo, col)

        user_message = f"""Use the following content from the Shoptimist USA website to answer the question.

CONTEXT:
{context}

QUESTION: {user_text}"""

        messages.append({"role": "user", "content": user_message})

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        )

        bot_text = "".join(
            block.text for block in response.content
            if block.type == "text"
        )

        print(f"\nBot: {bot_text}\n")

        messages.append({"role": "assistant", "content": bot_text})

if __name__ == "__main__":
    main()