from typing import Any, Tuple, Union
from markdown.extensions.wikilinks import WikiLinkExtension, WikiLinksInlineProcessor
from xml.etree.ElementTree import Element
from markdown import Markdown
from re import Match
from .db_api import IdTable
from .note_model import NoteModel
from typing import Callable
import sys

from . import static_resources_rc  # pyright: ignore # noqa
from . import katex_resources_rc  # pyright: ignore   # noqa
from . import katex_fonts_rc  # pyright: ignore # noqa


class CustomWikiLinkExtension(WikiLinkExtension):
    def __init__(
        self,
        note_model: NoteModel,
        current_note_id: Callable[[], str | None],
        **kwargs: Any,
    ) -> None:
        self.note_model = note_model
        self.current_note_id = current_note_id
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        # Create pattern to match [[pagename]]
        pattern = r"\[\[([^\]]+)\]\]"
        # Create the processor with our custom build_url
        processor = CustomWikiLinksInlineProcessor(
            pattern, self.getConfigs(), self.note_model, self.current_note_id
        )
        # Register it
        md.inlinePatterns.register(processor, "wikilink", 175)


class CustomWikiLinksInlineProcessor(WikiLinksInlineProcessor):
    def __init__(
        self,
        pattern: str,
        config: dict[str, Any],
        note_model: NoteModel,
        current_note_id: Callable[[], str | None],
    ) -> None:
        super().__init__(pattern, config)
        self.note_model = note_model
        self.maybe_current_note_id = current_note_id

    def handleMatch(  # type: ignore  # The typing here is a bit strange
        self, m: Match[str], data: str
    ) -> Union[Tuple[Element, int, int], Tuple[str, int, int]]:
        _ = data
        if m.group(1).strip():
            target_note_id = m.group(1).strip()
            url = self.config["base_url"] + target_note_id
            a = Element("a")
            a.text = self.get_label(target_note_id)
            a.set("href", url)
            return a, m.start(0), m.end(0)
        else:
            return "", m.start(0), m.end(0)

    def get_label(self, target_note_id: str) -> str:
        if self.note_model.what_is_this(target_note_id) == IdTable.NOTE:
            if note_meta := self.note_model.get_note_meta_by_id(target_note_id):
                label = note_meta.title
                target_folder_id = self.note_model.get_folder_id_from_note(
                    target_note_id
                )
                path = self.note_model.get_folder_path(target_folder_id)
                if current_note_id := self.maybe_current_note_id():
                    path_components = self.note_model.get_relative_path(
                        self.note_model.get_folder_id_from_note(current_note_id),
                        target_folder_id,
                    )

                    path = "/".join(path_components)
                else:
                    print(
                        "No current Note but asked to render wikilink, investigate this, likely a bug",
                        file=sys.stderr,
                    )
                if path:
                    label = f"{path}/{label}"
            else:
                label = target_note_id
        else:
            label = target_note_id

        return label
