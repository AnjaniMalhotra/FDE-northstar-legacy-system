"""RAG over Northstar's policy/SOP/memo documents, with evidence enforced in
code: a POLICY-type match is what marks a trace as having real evidence
(src/tracing.py), which flag_tools.log_dispute_flag then requires before it
will write anything."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

from copilot.tracing import mark_policy_evidence_ok

# ------------------------------------------
# ENV SETUP — load project .env so PINECONE_API_KEY is available
# ------------------------------------------
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env")

# ------------------------------------------
# EMBEDDING MODEL + PINECONE INDEX — set up once at import time
# ------------------------------------------
_embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
_policy_index = _pc.Index("northstar-policy-index")

# ------------------------------------------
# RELEVANCE_THRESHOLD — minimum match score before treating a result as real
# ------------------------------------------
RELEVANCE_THRESHOLD = 0.25  # below this, treat the query as unanswered, not weakly answered


# ------------------------------------------
# SEARCH POLICY DOCUMENTS — RAG lookup over POLICY/SOP/MEMO content
# ------------------------------------------
@tool
def search_policy_documents(query: str, config: RunnableConfig) -> str:
    """
    Searches Northstar's internal policy and process documents (the
    Accessorial Dispute Policy, the Detention Dispute Workflow SOP, and the
    Carrier Risk Indicators memo) for rules, thresholds, and process steps.
    Always check this before deciding whether a discrepancy is significant
    enough to flag, or what steps to follow.

    Every result names its document type — POLICY (sets a rule/threshold),
    SOP (sets a process/steps), or MEMO (background context only). A MEMO
    chunk can never justify a policy conclusion by itself; only POLICY or
    SOP content can. If nothing relevant is found, this says so explicitly
    — treat that as "no authoritative answer," not license to guess.
    """
    try:
        # ------------------------------------------
        # EMBED QUERY & SEARCH PINECONE
        # ------------------------------------------
        vector = _embedding_model.encode(query).tolist()
        result = _policy_index.query(vector=vector, top_k=4, include_metadata=True)
        matches = [m for m in result["matches"] if m["score"] >= RELEVANCE_THRESHOLD]

        # ------------------------------------------
        # ABSTAIN IF NOTHING CLEARS THE RELEVANCE THRESHOLD
        # ------------------------------------------
        if not matches:
            return (
                "ABSTAIN: no policy or SOP content meets the relevance threshold for this "
                "query. Do not answer as if a rule or process exists — say this could not be "
                "found in Northstar's documented policy."
            )
        # ------------------------------------------
        # MARK POLICY EVIDENCE — a real POLICY match unlocks log_dispute_flag
        # ------------------------------------------
        # log_dispute_flag's evidence gate specifically requires a POLICY
        # chunk (not just any non-abstained result) — a query that only
        # surfaces MEMO background content doesn't satisfy it, matching the
        # rule that a MEMO can never itself justify a tier decision.
        if any(m["metadata"]["document_type"] == "POLICY" for m in matches):
            mark_policy_evidence_ok(config["configurable"]["trace_id"])

        # ------------------------------------------
        # FORMAT MATCHES INTO A READABLE RESULT
        # ------------------------------------------
        return "\n\n".join(
            f"[{m['metadata']['document_type']} | {m['metadata']['source_file']}"
            f"{' | Section: ' + m['metadata']['section'] if m['metadata'].get('section') else ''}"
            f" | v{m['metadata'].get('policy_version', '?')} | score {m['score']:.2f}]\n"
            f"{m['metadata']['text']}"
            for m in matches
        )
    except Exception as e:
        return f"Policy search error: {e}"
