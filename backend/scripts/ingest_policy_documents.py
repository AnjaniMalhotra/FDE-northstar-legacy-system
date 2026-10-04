"""
Ingests data/policy/*.md and *.pdf into Pinecone: extracts text, splits into
paragraph-sized chunks tagged with real metadata, embeds each chunk locally
(sentence-transformers — no API key, runs on CPU), and upserts into a
Pinecone index. Pinecone only stores and searches the vectors; nothing about
the embedding step needs the cloud.

Every chunk carries: which document it came from, that document's type
(POLICY sets rules, SOP sets process steps, MEMO is background context
only), its section (where detectable), version, effective date, and access
classification. This is what lets search_policy_documents refuse to let a
MEMO answer a question only a POLICY is authoritative for, and cite exactly
where an answer came from.

Safe to re-run any time a source document changes — upserts overwrite by id.
"""
# ------------------------------------------
# IMPORTS — standard library, env loading, PDF parsing, Pinecone, and local embeddings
# ------------------------------------------
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

# ------------------------------------------
# PROJECT PATH AND ENV — load .env from the project root
# ------------------------------------------
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

# ------------------------------------------
# CONFIG — source directory, index name, and embedding model settings
# ------------------------------------------
POLICY_DIR = project_root / "data" / "policy"
INDEX_NAME = "northstar-policy-index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Document-level facts that can't reliably be inferred from the file itself.
# POLICY = sets a rule/threshold. SOP = sets a process/steps. MEMO = context
# only — never authoritative for a rule. See src/tools/policy_tools.py's
# search_policy_documents and the system prompt for how this is enforced.
# ------------------------------------------
# DOCUMENT REGISTRY — per-file type, version, effective date, and access classification
# ------------------------------------------
DOCUMENT_REGISTRY = {
    "accessorial_dispute_policy.md": {
        "document_type": "POLICY",
        "policy_version": "1.0",
        "effective_date": "2026-01",
        "access_classification": "Internal - Finance & Compliance",
    },
    "linehaul_rate_policy.md": {
        "document_type": "POLICY",
        "policy_version": "1.0",
        "effective_date": "2026-01",
        "access_classification": "Internal - Finance & Compliance",
    },
    "sop_detention_dispute_workflow.md": {
        "document_type": "SOP",
        "policy_version": "1.0",
        "effective_date": "2026-01",
        "access_classification": "Internal - Finance & Compliance",
    },
    "carrier_risk_memo.pdf": {
        "document_type": "MEMO",
        "policy_version": "1.0",
        "effective_date": "2026-01",
        "access_classification": "Confidential - Ops & Compliance",
    },
}


# ------------------------------------------
# EXTRACT TEXT — pull raw text out of a markdown or PDF source file
# ------------------------------------------
def extract_text(path: Path) -> str:
    if path.suffix == ".md":
        return path.read_text(encoding="utf-8")
    if path.suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError(f"Unsupported file type: {path.suffix}")


# ------------------------------------------
# CHUNKING PATTERNS — regexes that detect markdown headers and new-chunk boundaries
# ------------------------------------------
HEADER_MARKER = re.compile(r"^#{1,6}\s+(.*)$")
NEW_CHUNK_MARKER = re.compile(r"^(#{1,6}\s|\d+\.\s)")


# ------------------------------------------
# CHUNK TEXT — split extracted text into section-tagged, paragraph-sized chunks
# ------------------------------------------
def chunk_text(text: str) -> list[dict]:
    """
    Groups lines into paragraph-sized chunks, each tagged with the markdown
    section it falls under (None if the source has no markdown headers, as
    with PDF-extracted plain text). Starts a new chunk at a blank line, a
    markdown header, or a numbered list item — handles clean markdown
    (blank-line-separated) *and* PDF-extracted text, which often loses blank
    lines entirely but keeps its heading/list structure.
    """
    chunks: list[dict] = []
    current: list[str] = []
    current_section: str | None = None

    def flush():
        if current:
            chunk_str = " ".join(current).strip()
            if len(chunk_str) > 20:
                chunks.append({"text": chunk_str, "section": current_section})
            current.clear()

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            flush()
            continue
        header_match = HEADER_MARKER.match(line)
        if header_match:
            flush()
            current_section = header_match.group(1).strip()
            current.append(line)
        elif NEW_CHUNK_MARKER.match(line) and current:
            flush()
            current.append(line)
        else:
            current.append(line)
    flush()
    return chunks


# ------------------------------------------
# SETUP MODEL AND INDEX — load the embedding model and ensure the Pinecone index exists
# ------------------------------------------
if __name__ == "__main__":
    print(f"Loading local embedding model [{EMBEDDING_MODEL}]...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    if INDEX_NAME not in pc.list_indexes().names():
        print(f"Creating Pinecone index: {INDEX_NAME} ({EMBEDDING_DIM} dim)...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    index = pc.Index(INDEX_NAME)

    # ------------------------------------------
    # INGEST EACH POLICY FILE — extract, chunk, embed, and upsert every registered document
    # ------------------------------------------
    for file_path in sorted(POLICY_DIR.glob("*")):
        if file_path.suffix not in (".md", ".pdf"):
            continue
        if file_path.name not in DOCUMENT_REGISTRY:
            print(f"SKIPPED {file_path.name}: not in DOCUMENT_REGISTRY — add its type/version/classification first.")
            continue

        doc_meta = DOCUMENT_REGISTRY[file_path.name]
        chunks = chunk_text(extract_text(file_path))
        print(f"{file_path.name} [{doc_meta['document_type']}]: {len(chunks)} chunks")

        # Embed a *contextualized* version of each chunk — its document type
        # and section prepended — not the bare chunk text. This fixed a real
        # retrieval failure: without it, a query about "manager approval"
        # never surfaced the POLICY's actual Escalation Tiers section, even
        # at top_k=8, because a similarly-worded SOP section scored higher.
        # The stored/displayed text stays the original chunk, unprefixed —
        # only the embedding computation sees the added context.
        # ------------------------------------------
        # EMBED AND UPSERT — build contextualized embeddings and write vectors to Pinecone
        # ------------------------------------------
        def contextualize(chunk: dict) -> str:
            prefix = f'{doc_meta["document_type"]} document "{file_path.stem}"'
            if chunk["section"]:
                prefix += f', section: {chunk["section"]}'
            return f"{prefix}. {chunk['text']}"

        embed_texts = [contextualize(c) for c in chunks]
        embeddings = model.encode(embed_texts, show_progress_bar=False)
        vectors = [
            {
                "id": f"{file_path.name}-chunk-{i}",
                "values": embedding.tolist(),
                "metadata": {
                    "source_file": file_path.name,
                    "text": chunk["text"],
                    "section": chunk["section"] or "",
                    **doc_meta,
                },
            }
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]
        index.upsert(vectors=vectors)

    print("Ingestion complete.")
