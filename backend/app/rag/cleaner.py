import re


class TextCleaner:
    _space_re = re.compile(r"[ \t]+")
    _line_re = re.compile(r"\n{3,}")

    def clean(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = self._space_re.sub(" ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = self._line_re.sub("\n\n", text)
        return text.strip()

