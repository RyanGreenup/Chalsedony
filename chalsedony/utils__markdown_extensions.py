from typing import Any, Tuple, Union
from markdown.extensions.wikilinks import WikiLinkExtension, WikiLinksInlineProcessor
from xml.etree.ElementTree import Element
from markdown import Markdown
from re import Match
from .db_api import IdTable
from .note_model import NoteModel

from . import static_resources_rc  # pyright: ignore # noqa
from . import katex_resources_rc  # pyright: ignore   # noqa
from . import katex_fonts_rc  # pyright: ignore # noqa


class CustomWikiLinkExtension(WikiLinkExtension):
    def __init__(self, note_model: NoteModel, **kwargs: Any) -> None:
        self.note_model = note_model
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        # Create pattern to match [[pagename]]
        pattern = r"\[\[([^\]]+)\]\]"
        # Create the processor with our custom build_url
        processor = CustomWikiLinksInlineProcessor(
            pattern, self.getConfigs(), self.note_model
        )
        # Register it
        md.inlinePatterns.register(processor, "wikilink", 175)


class CustomWikiLinksInlineProcessor(WikiLinksInlineProcessor):
    def __init__(
        self, pattern: str, config: dict[str, Any], note_model: NoteModel
    ) -> None:
        super().__init__(pattern, config)
        self.note_model = note_model

    def handleMatch(  # type: ignore  # The typing here is a bit strange
        self, m: Match[str], data: str
    ) -> Union[Tuple[Element, int, int], Tuple[str, int, int]]:
        _ = data
        if m.group(1).strip():
            note_id = m.group(1).strip()
            if self.note_model.what_is_this(note_id) == IdTable.NOTE:
                if note_meta := self.note_model.get_note_meta_by_id(note_id):
                    label = note_meta.title
                else:
                    label = note_id
            else:
                label = note_id
            url = self.config["base_url"] + note_id
            a = Element("a")
            a.text = label
            a.set("href", url)
            return a, m.start(0), m.end(0)
        else:
            return "", m.start(0), m.end(0)
