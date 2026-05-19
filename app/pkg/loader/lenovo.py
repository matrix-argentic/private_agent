import asyncio
from http import HTTPStatus
from pathlib import Path
from typing import AsyncIterator, Iterator

from bs4 import BeautifulSoup, Tag
import httpx
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from loguru import logger
from markdownify import markdownify

from app.core.config import get_app_config


class LenovoDocumentLoader(BaseLoader):

    def __init__(self, base_url: str = "", knowledge_no_list: list[int] = [1]):
        super().__init__()
        if not base_url:
            base_url = "https://iknow.lenovo.com.cn/knowledgeapi/api/knowledge/knowledgeDetails"
        self.base_url = base_url
        self.knowledge_no_list = knowledge_no_list

    def _fetch_data(self, params: dict | None = None):
        params = params or {}
        with httpx.Client() as client:
            response = client.get(self.base_url, params=params)
            if response.status_code != HTTPStatus.OK:
                return "", {}
            response_json = response.json()
            response_data = response_json.get("data", {})
            if not response_data:
                return "", {}
            return self._extract_content_metadata(response_data=response_data)

    async def _afetch_data(self, params: dict | None = None) -> tuple[str, dict]:
        params = params or {}
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            if response.status_code != HTTPStatus.OK:
                return ""
            response_json = response.json()
            response_data = response_json.get("data", {})
            if not response_data:
                return ""
            return self._extract_content_metadata(response_data=response_data)

    def _extract_content_metadata(self, response_data: dict):
        content_str = ""
        # metadata
        knowledge_no = response_data.get("knowledgeNo", 0)
        title = response_data.get("title", "")
        content_str += f"# 标题:\n{title}\n\n"
        digest = response_data.get("digest", "")
        content_str += f"## 问题摘要\n{digest}\n\n"
        keywords = response_data.get("keywords", [])
        keywords = [item for s in keywords for item in s.split(",")]
        if len(keywords) > 0:
            content_str += f"## 关键字:\n{" ".join(keywords)}"

        topic = response_data.get("firstTopicName", "")
        sub_topic = response_data.get("subTopicName", "")
        question_category = response_data.get("questionCategoryName", "")
        create_time = response_data.get("createTime", "")
        version = response_data.get("versionNo", "")
        metadata = {
            "knowledge_no": knowledge_no,
            "title": title,
            "digest": digest,
            "topic": topic,
            "sub_topic": sub_topic,
            "question_category": question_category,
            "keywords": keywords,
            "create_time": create_time,
            "version": version,
        }

        # content
        content = response_data.get("content", "")
        if not content:
            return "", {}
        content = self._parse_html_to_markdown(html_data=content)
        content = response_data.get("content", "")
        if not content:
            return "", {}
        content_str += self._parse_html_to_markdown(html_data=content)
        return content_str, metadata

    def _parse_html_to_markdown(self, html_data: str) -> str:
        """
        html数据转化为markdown数据

        Args:
            html_data: html的数据字符串

        Returns: 返回 markdown 格式的字符串
        """
        if not html_data:
            return ""
        soup = BeautifulSoup(html_data, "html.parser")

        # 数据清洗
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        for ad in soup.select(".mceNonEditable"):
            ad.decompose()

        # 合并相邻的加粗标签
        bold_tags = soup.find_all(["strong", "b"])
        for tag in bold_tags:
            if not tag.parent:
                continue
            next_sibling = tag.next_sibling
            if (
                next_sibling
                and isinstance(next_sibling, Tag)
                and next_sibling.name in ["strong", "b"]
            ):
                tag.extend(next_sibling.contents)
                next_sibling.decompose()

        return markdownify(str(soup))

    def lazy_load(self) -> Iterator[Document]:
        for knowledge_no in self.knowledge_no_list:
            params = {"knowledgeNo": knowledge_no}
            content, metadata = self._fetch_data(params=params)
            if content:
                yield Document(page_content=content, metadata=metadata)

    async def alazy_load(self) -> AsyncIterator[Document]:
        tasks = {
            no: self._afetch_data(params={"knowledgeNo": no})
            for no in self.knowledge_no_list
        }
        for coro in asyncio.as_completed(tasks.values()):
            content, metadata = await coro
            if content:
                yield Document(page_content=content, metadata=metadata)

    def save_markdown(self, output_dir: str | Path | None = None):
        """Fetch each knowledge_no and save the extracted markdown to disk.

        Each document is saved as ``data/documents/{title}.md`` where *title*
        comes from the response metadata.

        Args:
            output_dir: Target directory (defaults to ``rag/data/documents/``).
        """
        if output_dir is None:
            output_dir = Path(__file__).resolve().parents[3] / "data" / "documents"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for knowledge_no in self.knowledge_no_list:
            content, metadata = self._fetch_data(params={"knowledgeNo": knowledge_no})
            if not content or not metadata.get("title"):
                logger.warning(
                    "Skipping knowledge_no={}: no content or title", knowledge_no
                )
                continue

            title = metadata["title"]
            safe_name = "".join(
                c if c.isalnum() or c in " _-." else "_" for c in title
            ).strip()
            if not safe_name:
                safe_name = f"knowledge_{knowledge_no}"

            dest = output_dir / f"{safe_name}.md"
            dest.write_text(content, encoding="utf-8")
            logger.info("Saved: {} ({})", dest.name, knowledge_no)


# uv run -m rag.loader.lenovo
if __name__ == "__main__":
    from tqdm import tqdm

    config = get_app_config()
    base_url = (
        f"{config.knowledge_base_url}/knowledgeapi/api/knowledge/knowledgeDetails"
    )
    batch_size = 50
    total = 500
    for start in tqdm(
        range(1, total + 1, batch_size), desc="markdown下载进度", unit="batch"
    ):
        end = min(start + batch_size, total + 1)
        knowledge_no_list = list(range(start, end))
        loader = LenovoDocumentLoader(
            base_url=base_url, knowledge_no_list=knowledge_no_list
        )
        loader.save_markdown()
