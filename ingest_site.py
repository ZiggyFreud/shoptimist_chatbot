<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
	<head>
		<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
		<title>Pastebin.com - Access Denied Warning</title>
        <!-- Global site tag (gtag.js) - Google Analytics -->

	</head> 
	<body style="text-align: center;margin:10px 0 0 0;background-color:#E0E0E0;font-family:segoe ui,trebuchet MS,Lucida Sans Unicode,Lucida Sans,Sans-Serif">
		<div style="margin: auto;background:#fff;width:485px;padding:25px;display:inline-block;border-radius:10px">
			<div style="clear: both">

                <div style="width:80px;height:80px;margin: 0 auto">
                    <svg version="1.1" xmlns="http://www.w3.org/2000/svg"
                         xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
                         viewBox="0 0 497.472 497.472" style="enable-background:new 0 0 497.472 497.472;"
                         xml:space="preserve">

                        <g transform="matrix(1.25 0 0 -1.25 0 45)">
                            <g>
                                <g>
                                    <path style="fill:#FFCC4D;" d="M24.374-357.857c-20.958,0-30.197,15.223-20.548,33.826L181.421,17.928
                                        c9.648,18.603,25.463,18.603,35.123,0L394.14-324.031c9.671-18.603,0.421-33.826-20.548-33.826H24.374z"/>
                                    <path style="fill:#231F20;" d="M173.605-80.922c0,14.814,10.934,23.984,25.395,23.984c14.12,0,25.407-9.512,25.407-23.984
                                        V-216.75c0-14.461-11.287-23.984-25.407-23.984c-14.461,0-25.395,9.182-25.395,23.984V-80.922z M171.489-289.056
                                        c0,15.167,12.345,27.511,27.511,27.511c15.167,0,27.523-12.345,27.523-27.511c0-15.178-12.356-27.523-27.523-27.523
                                        C183.834-316.579,171.489-304.234,171.489-289.056"/>
                                </g>
                            </g>
                        </g>

                    </svg>
                </div>

			 	<h2 style="color:#181818;font-size:140%">Pastebin.com has blocked your IP</h2>
			 	<h3 style="color:#181818;font-size:100%;font-weight:normal">We have <i>temporarily</i> blocked your IP from accessing our website because we have <i><b>detected unnatural browsing behavior</b></i>.</h3>
					
				<div style="border:3px dotted #C03;background:#f9f9f9;padding:5px 10px;border-radius:5px">
					<h3 style="color:#181818;font-size: 100%;font-weight:normal">If you are trying to <b>scrape</b> our website, your IP will be blocked, we recommend that you contact <a href="/cdn-cgi/l/email-protection#2251434e4751625243515647404b4c0c414d4f" style="color:#C03"><span class="__cf_email__" data-cfemail="0b786a676e784b7b6a787f6e69626525686466">[email&#160;protected]</span></a> for a possible solution.</h3>
					<div style="text-align:right">Thanks, The Pastebin Team</div>
				</div>
			</div>
		</div>
	<script data-cfasync="false" src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script></body>
</html>import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag, urlparse

import chromadb
import voyageai
from dotenv import load_dotenv

load_dotenv()

START_URL = "https://shoptimistusa.com/"
MAX_PAGES = 30

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return clean_text(soup.get_text(" "))

def same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + chunk_size])
        i += chunk_size - overlap
    return chunks

def crawl(start_url: str, max_pages: int):
    seen = set()
    queue = [start_url]
    pages = []

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        url, _ = urldefrag(url)
        if url in seen:
            continue
        seen.add(url)

        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "SiteRAGBot/1.0"})
            print(f"[{r.status_code}] {url} | Content-Type: {r.headers.get('Content-Type', 'N/A')}")
            if r.status_code != 200:
                continue
            if "text/html" not in r.headers.get("Content-Type", ""):
                continue
        except Exception as e:
            print(f"[ERROR] {url} — {e}")
            continue

        text = html_to_text(r.text)
        print(f"  Text length: {len(text)}")
        if len(text) < 200:
            continue

        pages.append((url, text))

        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select("a[href]"):
            nxt = urljoin(url, a["href"])
            nxt, _ = urldefrag(nxt)
            if same_domain(nxt, start_url) and nxt.startswith(start_url):
                if nxt not in seen:
                    queue.append(nxt)

    return pages

def main():
    import time
    vo = voyageai.Client()

    client = chromadb.PersistentClient(path="chroma_db")
    col = client.get_or_create_collection(name="website")

    pages = crawl(START_URL, MAX_PAGES)

    ids, docs, metas = [], [], []
    for url, text in pages:
        for idx, ch in enumerate(chunk_text(text)):
            ids.append(f"{url}::chunk{idx}")
            docs.append(ch)
            metas.append({"url": url, "chunk": idx})

    if not docs:
        print("No pages ingested. Check START_URL or site blocking.")
        return

    all_embeddings = []
    batch_size = 5
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        print(f"Embedding batch {i//batch_size + 1} of {(len(docs) + batch_size - 1)//batch_size}...")
        emb = vo.embed(texts=batch, model="voyage-3-large", input_type="document").embeddings
        all_embeddings.extend(emb)
        time.sleep(20)

    col.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=all_embeddings)
    print(f"Stored {len(docs)} chunks from {len(pages)} pages into chroma_db.")

if __name__ == "__main__":
    main()