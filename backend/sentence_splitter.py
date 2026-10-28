import re
from typing import Generator, List, Optional, Tuple

class SentenceSplitter:
    """
    Buffers streaming text chunks and yields complete sentences.
    - Emits sentences ending in English (. ! ?), Hindi danda (। U+0964, ॥ U+0965), and Kannada punctuation.
    - Handles sentences split across multiple chunks.
    - Avoids splitting on decimal numbers (e.g., 3.5, 0.01) and common abbreviations (e.g., e.g., i.e., Dr.).
    - Flushes remaining buffered text when the stream ends.
    """
    def __init__(self):
        self.buffer = ""
        self._abbreviations = {
            "e.g.", "i.e.", "dr.", "mr.", "mrs.", "ms.", "prof.", "vs.", "etc.", "st.", "jr.", "sr."
        }

    def feed(self, chunk: str) -> List[str]:
        """Feeds a text chunk into the buffer and returns any complete sentences."""
        if not chunk:
            return []
        self.buffer += chunk
        return self._extract_sentences()

    def flush(self) -> List[str]:
        """Flushes and returns any remaining text in the buffer as the final sentence."""
        remaining = self.buffer.strip()
        self.buffer = ""
        if remaining:
            return [remaining]
        return []

    def _extract_sentences(self) -> List[str]:
        sentences = []
        while True:
            boundary = self._find_next_boundary()
            if not boundary:
                break
            end_pos, next_start = boundary
            sentence = self.buffer[:end_pos].strip()
            self.buffer = self.buffer[next_start:]
            if sentence:
                sentences.append(sentence)
        return sentences

    def _find_next_boundary(self) -> Optional[Tuple[int, int]]:
        buf = self.buffer
        length = len(buf)
        i = 0

        while i < length:
            char = buf[i]

            # 1. Hindi danda (।) and double danda (॥)
            if char in ("\u0964", "\u0965"):
                end_pos = i + 1
                while end_pos < length and buf[end_pos] in ('"', "'", '”', '’', ')', ']'):
                    end_pos += 1
                if end_pos < length:
                    if buf[end_pos].isspace():
                        next_start = end_pos + 1
                        while next_start < length and buf[next_start].isspace():
                            next_start += 1
                        return (end_pos, next_start)
                    else:
                        i = end_pos
                        continue
                else:
                    # At buffer boundary; wait for next chunk
                    return None

            # 2. Exclamation mark (!) and Question mark (?)
            elif char in ("!", "?"):
                end_pos = i + 1
                while end_pos < length and buf[end_pos] in ("!", "?", '"', "'", '”', '’', ')', ']'):
                    end_pos += 1
                if end_pos < length:
                    if buf[end_pos].isspace():
                        next_start = end_pos + 1
                        while next_start < length and buf[next_start].isspace():
                            next_start += 1
                        return (end_pos, next_start)
                    else:
                        i = end_pos
                        continue
                else:
                    return None

            # 3. Period / Dot (.)
            elif char == ".":
                # Check for ellipsis (...)
                if (i + 1 < length and buf[i + 1] == ".") or (i > 0 and buf[i - 1] == "."):
                    i += 1
                    continue

                # Decimal number check: preceded by digit and (followed by digit or waiting for digit)
                if i > 0 and buf[i - 1].isdigit():
                    if i + 1 < length and buf[i + 1].isdigit():
                        i += 1
                        continue
                    if i + 1 == length:
                        # Could be followed by digit in next chunk (e.g. 3. -> 5)
                        return None

                # Abbreviation check: look back for the word preceding the period
                word_match = re.search(r'[A-Za-z.]+$', buf[: i + 1])
                if word_match:
                    word = word_match.group(0).lower()
                    if word in self._abbreviations:
                        i += 1
                        continue

                end_pos = i + 1
                while end_pos < length and buf[end_pos] in ('"', "'", '”', '’', ')', ']'):
                    end_pos += 1
                if end_pos < length:
                    if buf[end_pos].isspace():
                        next_start = end_pos + 1
                        while next_start < length and buf[next_start].isspace():
                            next_start += 1
                        return (end_pos, next_start)
                    else:
                        i = end_pos
                        continue
                else:
                    return None

            i += 1

        return None
