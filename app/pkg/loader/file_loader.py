"""File loader — reads uploaded files and yields LangChain Documents."""

from pathlib import Path
import tempfile
from typing import Iterator

from bs4 import BeautifulSoup
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from markdownify import markdownify


class FileLoader(BaseLoader):
    """通过文件路径加载文档

    支持 ``.txt``, ``.md``, ``.pdf``, ``.docx``, ``.html`` / ``.htm``.
    """

    def __init__(self, file_path: Path, filename: str, metadata: dict | None = None):
        self.file_path = file_path
        self.filename = filename
        self.metadata = metadata or {}

    def lazy_load(self) -> Iterator[Document]:
        ext = Path(self.filename).suffix.lower()
        loader = {
            ".txt": self.load_text,
            ".md": self.load_text,
            ".pdf": self.load_pdf,
            ".docx": self.load_docx,
            ".html": self.load_html,
            ".htm": self.load_html,
        }
        load_fn = loader.get(ext)
        if load_fn is None:
            raise ValueError(
                f"Unsupported file type '{ext}' for '{self.filename}'. "
                f"Supported: {', '.join(sorted(loader))}"
            )
        docs = load_fn()
        for doc in docs:
            yield doc

    # ── internal ────────────────────────────────────────────────────────────

    def _to_textloader(self, text: str, suffix: str = ".txt") -> list[Document]:
        """Write *text* to a temp file and load via ``TextLoader``."""
        from langchain_community.document_loaders.text import TextLoader

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as f:
            f.write(text)
            tmp_path = f.name

        try:
            loader = TextLoader(file_path=tmp_path, encoding="utf-8")
            docs = loader.load()
            for doc in docs:
                doc.metadata.update(self.metadata)
            return docs
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def load_text(self) -> list[Document]:
        from langchain_community.document_loaders.text import TextLoader

        loader = TextLoader(file_path=self.file_path, encoding="utf-8")
        return loader.load()

    def load_pdf(self) -> list[Document]:
        from langchain_mineru import MinerULoader

        loader = MinerULoader(
            language="en",
            source=str(self.file_path),
            mode="flash",
        )
        return loader.load()

    def load_docx(self) -> list[Document]:
        import mammoth

        with open(self.file_path, "rb") as f:
            result = mammoth.convert_to_markdown(f)
            markdown = result.value

        return self._to_textloader(markdown, suffix=".md")

    def load_html(self) -> list[Document]:
        content = self.file_path.read_bytes()
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        markdown = markdownify(str(soup))
        return self._to_textloader(markdown, suffix=".md")
