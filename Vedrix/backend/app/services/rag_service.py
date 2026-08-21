import os
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.model = None
        self._initialized = False
        self._fallback_mode = False
        self._fallback_documents: Dict[str, List[str]] = {}

    def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.persist_directory = os.path.join(base_dir, "db", "chroma")
            os.makedirs(self.persist_directory, exist_ok=True)

            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name="candidate_interviews",
                metadata={"hnsw:space": "cosine"}
            )

            logger.info("Initializing SentenceTransformer model 'all-MiniLM-L6-v2'...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer model loaded successfully.")
            self._initialized = True
            self._fallback_mode = False
        except Exception as e:
            # Preserve interview context even when the optional vector stack is
            # unavailable. Production can install ChromaDB for semantic search.
            logger.warning(f"RAG service initialization failed; using deterministic fallback: {e}")
            self._initialized = True
            self._fallback_mode = True

    def _embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using the sentence transformer model."""
        self._ensure_initialized()
        if not self._initialized:
            return [[] for _ in texts]
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]

    async def index_resume(self, session_id: str, resume_text: str):
        """Index paragraphs or sections from the candidate's resume."""
        self._ensure_initialized()
        if not self._initialized:
            logger.warning("RAG service not initialized, skipping resume indexing")
            return

        if not resume_text or len(resume_text.strip()) < 20:
            return

        logger.info(f"Indexing resume for session_id: {session_id}...")

        # Split text into paragraphs/chunks
        paragraphs = [p.strip() for p in resume_text.split("\n\n") if len(p.strip()) > 30]
        if not paragraphs:
            # Fallback if no double newlines
            paragraphs = [p.strip() for p in resume_text.split("\n") if len(p.strip()) > 30]

        if not paragraphs:
            paragraphs = [resume_text]

        if self._fallback_mode:
            self._fallback_documents[session_id] = paragraphs
            logger.info("Stored resume context in deterministic RAG fallback for %s", session_id)
            return

        documents = []
        ids = []
        metadatas = []

        for idx, paragraph in enumerate(paragraphs):
            documents.append(paragraph)
            ids.append(f"resume_{session_id}_{idx}")
            metadatas.append({
                "session_id": session_id,
                "type": "resume",
                "index": idx
            })

        embeddings = self._embed_text(documents)

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        logger.info(f"Successfully indexed {len(documents)} resume chunks.")

    async def index_github_profile(self, session_id: str, github_username: str):
        """Fetch and index public repositories from GitHub."""
        self._ensure_initialized()
        if not self._initialized:
            logger.warning("RAG service not initialized, skipping GitHub indexing")
            return

        if not github_username:
            return

        github_username = github_username.strip().split('/')[-1]  # Extract username if full URL is passed
        logger.info(f"Fetching GitHub repositories for: {github_username}...")

        url = f"https://api.github.com/users/{github_username}/repos?per_page=20&sort=updated"
        headers = {"User-Agent": "Vedrix-AI-Interview-System"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch GitHub repos for {github_username}: Status {response.status_code}")
                    return

                repos = response.json()
                if not isinstance(repos, list):
                    return

                documents = []
                ids = []
                metadatas = []

                for idx, repo in enumerate(repos):
                    name = repo.get("name", "")
                    desc = repo.get("description", "No description provided.")
                    lang = repo.get("language", "Not specified")
                    topics = ", ".join(repo.get("topics", []))
                    stars = repo.get("stargazers_count", 0)

                    repo_text = (
                        f"Repository: {name}\n"
                        f"Description: {desc}\n"
                        f"Primary Language: {lang}\n"
                        f"Topics: {topics}\n"
                        f"Stars: {stars}"
                    )

                    documents.append(repo_text)
                    ids.append(f"github_{session_id}_{name}")
                    metadatas.append({
                        "session_id": session_id,
                        "type": "github",
                        "repo_name": name,
                        "language": lang
                    })

                if documents and self._fallback_mode:
                    self._fallback_documents.setdefault(session_id, []).extend(documents)
                    return

                if documents:
                    embeddings = self._embed_text(documents)
                    self.collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        documents=documents
                    )
                    logger.info(f"Successfully indexed {len(documents)} GitHub repositories.")
        except Exception as e:
            logger.error(f"GitHub retrieval/indexing failed: {e}")

    def query_context(self, session_id: str, query: str, limit: int = 3) -> str:
        """Query ChromaDB for relevant context segments related to the interview session."""
        self._ensure_initialized()
        if not self._initialized:
            return ""

        if self._fallback_mode:
            return "\n---\n".join(self._fallback_documents.get(session_id, [])[:limit])

        try:
            query_embedding = self._embed_text([query])[0]

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where={"session_id": session_id}
            )

            documents = results.get("documents", [])
            if not documents or not documents[0]:
                return ""

            compiled_context = "\n---\n".join(documents[0])
            return compiled_context
        except Exception as e:
            logger.error(f"Error querying RAG context: {e}")
            return ""

    def clear_session_data(self, session_id: str):
        """Clean up documents for a given session when completed."""
        self._ensure_initialized()
        if not self._initialized:
            return

        if self._fallback_mode:
            self._fallback_documents.pop(session_id, None)
            return

        try:
            self.collection.delete(where={"session_id": session_id})
            logger.info(f"Cleared RAG documents for session: {session_id}")
        except Exception as e:
            logger.error(f"Error clearing session documents: {e}")


# Global instance (lazy — won't download models until first use)
rag_service = RAGService()
