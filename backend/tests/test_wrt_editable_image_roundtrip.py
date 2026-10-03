# NOTICE: This file is protected under RCF-PL
"""Regression tests for inline images on the Visual Mode path.

``wrt_to_editable_html`` and ``wrt_from_editable_html`` had no handling for
``[img ...]`` at all, even though ``VALID_TAGS`` lists ``img`` as a valid tag.
The tag fell through to the text-escaping branch and rendered into the editor as
the literal string ``[img src="data:image/png;base64,..."]``.

The payload survived a plain save only by accident -- escaping is symmetric, so
the literal text round-tripped back into the same tag. The real damage was that
the payload was *visible and editable*: one keystroke inside that literal text
rewrites the base64, ``validate`` still reports ``valid: true``, and every
downstream consumer (DOCX/PPTX export) then falls back to an ``[Image: alt]``
placeholder because the payload no longer decodes.

These tests drive the binary directly rather than going through the service
wrapper. The wrapper prefers the Unix-socket daemon, and a daemon started before
a rebuild keeps serving the old image from memory -- so a passing run would say
nothing about the code on disk.
"""

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "backend" / "native" / "wrt" / "wrt-engine"

# 1x1 transparent PNG -- a real, decodable payload.
PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
PNG_DATA_URI = f"data:image/png;base64,{PNG_B64}"


def img_tag(src: str = PNG_DATA_URI, alt: str = "logo") -> str:
    return f'[img src="{src}" alt="{alt}"]'


class TestWrtEditableImageRoundtrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ENGINE.is_file():
            raise RuntimeError(
                f"Build the native engine first: make -C backend/native/wrt wrt-engine ({ENGINE})"
            )

    def engine(self, action: str, text: str) -> str:
        proc = subprocess.run(
            [str(ENGINE), action, "-"],
            input=text,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"{action} failed: {proc.stderr}")
        return proc.stdout

    def to_html(self, wrt: str) -> str:
        return self.engine("to-editable-html", wrt)

    def from_html(self, html: str) -> str:
        return self.engine("from-editable-html", html)

    # -- rendering -------------------------------------------------------

    def test_img_renders_as_element_not_literal_text(self):
        html = self.to_html(img_tag())

        self.assertIn("<img", html)
        # The regression: the whole tag used to be emitted as escaped visible text.
        self.assertNotIn("&quot;data:image/png;base64,", html)
        self.assertIn(f'src="{PNG_DATA_URI}"', html)
        self.assertIn('alt="logo"', html)

    def test_img_renders_inside_heading(self):
        """Headings copy their body in one go, so a blanket escape renders the
        image as markup text inside the heading."""
        html = self.to_html(f"[h1]Title {img_tag(alt='h')}[/h1]")

        self.assertIn("<img", html)
        self.assertNotIn("&quot;data:image/png;base64,", html)

    def test_img_renders_inside_quote(self):
        html = self.to_html(f"[quote]q {img_tag(alt='q')}[/quote]")
        self.assertIn("<img", html)

    def test_img_renders_inside_list_item(self):
        html = self.to_html(f"[list]\n* item {img_tag(alt='li')}\n[/list]")
        self.assertIn("<img", html)

    # -- round trip ------------------------------------------------------

    def test_img_payload_survives_roundtrip_byte_for_byte(self):
        wrt = self.from_html(self.to_html(img_tag()))
        self.assertIn(f'[img src="{PNG_DATA_URI}" alt="logo"]', wrt)

    def test_img_keeps_position_between_surrounding_text(self):
        """Ordering is the failure mode that bit the DOCX path (#974).

        Two separate accumulators cannot preserve interleaving; the Visual path
        has to emit the image exactly where it sat in the WRT source, not hoisted
        to the start or the end of its paragraph.
        """
        wrt = self.from_html(self.to_html(f"before {img_tag()} after"))
        img_at = wrt.index("[img ")

        self.assertGreater(img_at, 0, "image must not be hoisted to the start")
        self.assertIn("before", wrt[:img_at], "text before the image must stay before it")
        self.assertIn("after", wrt[img_at:], "text after the image must stay after it")

    def test_two_images_in_one_paragraph_both_survive(self):
        other = f"data:image/png;base64,{PNG_B64[:-4]}AAAA"
        wrt = self.from_html(self.to_html(f"{img_tag(alt='first')} x {img_tag(other, alt='second')}"))

        self.assertEqual(wrt.count("[img "), 2)
        self.assertIn('alt="first"', wrt)
        self.assertIn('alt="second"', wrt)

    def test_img_inside_heading_survives(self):
        wrt = self.from_html(self.to_html(f"[h1]Title {img_tag(alt='h')}[/h1]"))

        self.assertIn("[img ", wrt, "image inside a heading must not be swallowed")
        self.assertIn('alt="h"', wrt)

    def test_img_alongside_inline_formatting_tags(self):
        wrt = self.from_html(self.to_html(f"[b]{img_tag(alt='bold-img')}[/b]"))

        self.assertIn("[b]", wrt)
        self.assertIn("[/b]", wrt)
        self.assertIn('alt="bold-img"', wrt)

    def test_alt_with_html_special_characters_is_decoded(self):
        """The value is escaped on the way to HTML and decoded on the way back.
        Forgetting the decode step would leave ``&amp;amp;`` in the WRT source and
        silently rewrite the alt text on every save."""
        html = self.to_html(img_tag(alt="Tom &amp; Jerry &lt;3"))
        self.assertIn("Tom &amp;amp; Jerry", html)

        wrt = self.from_html(html)
        self.assertIn('alt="Tom &amp; Jerry &lt;3"', wrt)
        self.assertNotIn("&amp;amp;", wrt, "attribute value must be decoded exactly once")

    def test_img_tag_stays_valid_after_roundtrip(self):
        proc = subprocess.run(
            [str(ENGINE), "validate", "-"],
            input=self.from_html(self.to_html(img_tag())),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"valid":true', proc.stdout.replace(" ", ""))

    # -- degenerate input must not read out of bounds ----------------------

    def test_bare_img_without_attributes_does_not_crash(self):
        self.assertIsInstance(self.to_html("[img]"), str)
        self.assertIsInstance(self.from_html(self.to_html("[img]")), str)

    def test_unterminated_img_tag_does_not_read_past_buffer(self):
        html = self.to_html('[img src="data:image/png;base64,AAAA')
        self.assertIn("AAAA", html)

    def test_img_tag_without_alt_keeps_src(self):
        wrt = self.from_html(self.to_html(f'[img src="{PNG_DATA_URI}"]'))
        self.assertIn(PNG_DATA_URI, wrt)

    def test_img_element_without_src_is_dropped_not_mangled(self):
        """A src-less <img> has no payload; emitting a bare [img] would just add a
        tag the validator flags as malformed."""
        wrt = self.from_html('<div><p>a<img alt="x" />b</p></div>')
        self.assertNotIn("[img", wrt)
        self.assertIn("a", wrt)
        self.assertIn("b", wrt)


if __name__ == "__main__":
    unittest.main()