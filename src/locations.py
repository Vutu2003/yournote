"""Version-scoped locations: pages only for PDFs, anchors for reflowable text."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Locator(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['page', 'paragraph']
    page: int | None = Field(default=None, ge=1)
    anchor: str | None = Field(default=None, pattern=r'^b[0-9]{6}$')
    paragraph: int | None = Field(default=None, ge=1)
    heading: list[str] = Field(default_factory=list, max_length=6)

    @model_validator(mode='after')
    def consistent(self):
        if self.kind == 'page':
            if self.page is None or self.anchor is not None or self.paragraph is not None:
                raise ValueError('A page locator requires only a page number')
        elif self.anchor is None or self.paragraph is None or self.page is not None:
            raise ValueError('A paragraph locator requires an anchor and paragraph, never a page')
        return self


def location_label(locator: Locator | None, page: int | None = None) -> str:
    if locator and locator.kind == 'paragraph':
        heading = ' / '.join(locator.heading)
        return (heading + ' · ' if heading else '') + f'đoạn {locator.paragraph}'
    return f'trang {locator.page if locator else page}'


def checked_page(page, locator):
    if locator is None: return page
    if locator.kind == 'paragraph':
        if page is not None: raise ValueError('Paragraph locations must not invent a page number')
        return None
    if page is not None and page != locator.page: raise ValueError('Page and locator disagree')
    return locator.page
