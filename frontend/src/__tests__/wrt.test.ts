// NOTICE: This file is protected under RCF-PL
import { wrtToHtml, wrtToEditableHtml, editableElementToWrt } from "@/lib/wrt";

/* ── wrtToHtml ─────────────────────────────────────────────────── */

describe("wrtToHtml", () => {
  it("renders plain text as a paragraph", () => {
    expect(wrtToHtml("Hello world")).toBe("<p>Hello world</p>");
  });

  it("renders bold text", () => {
    expect(wrtToHtml("[b]Author[/b]")).toBe("<p><strong>Author</strong></p>");
  });

  it("renders italic text", () => {
    expect(wrtToHtml("[i]emphasis[/i]")).toBe("<p><em>emphasis</em></p>");
  });

  it("renders underline text", () => {
    expect(wrtToHtml("[u]underlined[/u]")).toBe("<p><u>underlined</u></p>");
  });

  it("renders strikethrough text", () => {
    expect(wrtToHtml("[s]deleted[/s]")).toBe("<p><s>deleted</s></p>");
  });

  it("renders code spans", () => {
    expect(wrtToHtml("[code]x = 1[/code]")).toBe("<p><code>x = 1</code></p>");
  });

  it("renders nested inline tags", () => {
    expect(wrtToHtml("[b][i]bold italic[/i][/b]")).toBe(
      "<p><strong><em>bold italic</em></strong></p>",
    );
  });

  it("renders headings h1–h3", () => {
    expect(wrtToHtml("[h1]Title[/h1]")).toBe("<h1>Title</h1>");
    expect(wrtToHtml("[h2]Subtitle[/h2]")).toBe("<h2>Subtitle</h2>");
    expect(wrtToHtml("[h3]Section[/h3]")).toBe("<h3>Section</h3>");
  });

  it("renders headings with inline formatting", () => {
    expect(wrtToHtml("[h1][b]Bold Title[/b][/h1]")).toBe(
      "<h1><strong>Bold Title</strong></h1>",
    );
  });

  it("renders blockquotes", () => {
    expect(wrtToHtml("[quote]\nSome wisdom\n[/quote]")).toBe(
      "<blockquote>Some wisdom</blockquote>",
    );
  });

  it("renders multi-line blockquotes", () => {
    expect(wrtToHtml("[quote]\nLine one\nLine two\n[/quote]")).toBe(
      "<blockquote>Line one<br>Line two</blockquote>",
    );
  });

  it("renders lists", () => {
    const wrt = "[list]\n* First\n* Second\n* Third\n[/list]";
    expect(wrtToHtml(wrt)).toBe(
      "<ul><li>First</li><li>Second</li><li>Third</li></ul>",
    );
  });

  it("renders lists with inline formatting", () => {
    const wrt = "[list]\n* [b]Bold item[/b]\n* Normal item\n[/list]";
    expect(wrtToHtml(wrt)).toBe(
      "<ul><li><strong>Bold item</strong></li><li>Normal item</li></ul>",
    );
  });

  it("renders tables", () => {
    const wrt = "[table]\n| Name | Age |\n| Alice | 30 |\n[/table]";
    expect(wrtToHtml(wrt)).toContain("<table>");
    expect(wrtToHtml(wrt)).toContain("<th>Name</th>");
    expect(wrtToHtml(wrt)).toContain("<td>Alice</td>");
    expect(wrtToHtml(wrt)).toContain("<td>30</td>");
  });

  it("renders images", () => {
    const wrt = '[img src="/test.png" alt="Test image"]';
    expect(wrtToHtml(wrt)).toBe(
      '<img src="/test.png" alt="Test image">',
    );
  });

  it("renders images with https URLs", () => {
    const wrt = '[img src="https://example.com/img.jpg" alt="Photo"]';
    expect(wrtToHtml(wrt)).toBe(
      '<img src="https://example.com/img.jpg" alt="Photo">',
    );
  });

  it("rejects images with unsafe protocols", () => {
    const wrt = '[img src="javascript:alert(1)" alt="xss"]';
    // Unsafe protocol → not matched as image → rendered as escaped paragraph text
    const html = wrtToHtml(wrt);
    expect(html).not.toContain("<img");
    // The text is safely escaped — no executable attribute
    expect(html).toContain("&quot;");
  });

  it("escapes HTML in plain text", () => {
    expect(wrtToHtml("<script>alert(1)</script>")).toBe(
      "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>",
    );
  });

  it("handles escaped brackets as literal text", () => {
    expect(wrtToHtml("Use \\[b] for bold")).toBe(
      "<p>Use [b] for bold</p>",
    );
  });

  it("separates paragraphs by blank lines", () => {
    expect(wrtToHtml("Paragraph one\n\nParagraph two")).toBe(
      "<p>Paragraph one</p>\n<p>Paragraph two</p>",
    );
  });

  it("joins non-blank lines within a paragraph with <br>", () => {
    expect(wrtToHtml("Line one\nLine two")).toBe(
      "<p>Line one<br>Line two</p>",
    );
  });

  it("returns empty string for empty input", () => {
    expect(wrtToHtml("")).toBe("");
  });

  it("handles a realistic DOCX-converted document", () => {
    const wrt = [
      "[h1]Meeting Notes[/h1]",
      "",
      "[b]Author:[/b] John",
      "[i]Date:[/i] 2026-09-05",
      "",
      "[list]",
      "* Review Q3 numbers",
      "* Plan Q4 roadmap",
      "[/list]",
    ].join("\n");

    const html = wrtToHtml(wrt);
    expect(html).toContain("<h1>Meeting Notes</h1>");
    expect(html).toContain("<strong>Author:</strong> John");
    expect(html).toContain("<em>Date:</em> 2026-09-05");
    expect(html).toContain("<li>Review Q3 numbers</li>");
    expect(html).toContain("<li>Plan Q4 roadmap</li>");
  });
});

/* ── wrtToEditableHtml ─────────────────────────────────────────── */

describe("wrtToEditableHtml", () => {
  it("returns placeholder paragraph for empty input", () => {
    expect(wrtToEditableHtml("")).toBe("<p><br></p>");
  });

  it("returns rendered HTML for non-empty input", () => {
    expect(wrtToEditableHtml("[b]Hello[/b]")).toBe(
      "<p><strong>Hello</strong></p>",
    );
  });
});

/* ── editableElementToWrt (DOM → WRT roundtrip) ───────────────── */

describe("editableElementToWrt", () => {
  function domFromHtml(html: string): HTMLElement {
    const container = document.createElement("div");
    container.innerHTML = html;
    return container;
  }

  it("serializes plain paragraph", () => {
    const root = domFromHtml("<p>Hello world</p>");
    expect(editableElementToWrt(root)).toBe("Hello world\n");
  });

  it("serializes bold text", () => {
    const root = domFromHtml("<p><strong>Author</strong></p>");
    expect(editableElementToWrt(root)).toBe("[b]Author[/b]\n");
  });

  it("serializes italic text", () => {
    const root = domFromHtml("<p><em>emphasis</em></p>");
    expect(editableElementToWrt(root)).toBe("[i]emphasis[/i]\n");
  });

  it("serializes underline text", () => {
    const root = domFromHtml("<p><u>underlined</u></p>");
    expect(editableElementToWrt(root)).toBe("[u]underlined[/u]\n");
  });

  it("serializes strikethrough (s/strike/del)", () => {
    expect(editableElementToWrt(domFromHtml("<p><s>gone</s></p>"))).toBe("[s]gone[/s]\n");
    expect(editableElementToWrt(domFromHtml("<p><strike>gone</strike></p>"))).toBe("[s]gone[/s]\n");
    expect(editableElementToWrt(domFromHtml("<p><del>gone</del></p>"))).toBe("[s]gone[/s]\n");
  });

  it("serializes code spans", () => {
    const root = domFromHtml("<p><code>x = 1</code></p>");
    expect(editableElementToWrt(root)).toBe("[code]x = 1[/code]\n");
  });

  it("serializes nested inline formatting", () => {
    const root = domFromHtml("<p><strong><em>bold italic</em></strong></p>");
    expect(editableElementToWrt(root)).toBe("[b][i]bold italic[/i][/b]\n");
  });

  it("serializes headings", () => {
    expect(editableElementToWrt(domFromHtml("<h1>Title</h1>"))).toBe("[h1]Title[/h1]\n");
    expect(editableElementToWrt(domFromHtml("<h2>Sub</h2>"))).toBe("[h2]Sub[/h2]\n");
    expect(editableElementToWrt(domFromHtml("<h3>Section</h3>"))).toBe("[h3]Section[/h3]\n");
  });

  it("serializes blockquotes", () => {
    const root = domFromHtml("<blockquote>Wisdom here</blockquote>");
    expect(editableElementToWrt(root)).toBe("[quote]\nWisdom here\n[/quote]\n");
  });

  it("serializes unordered lists", () => {
    const root = domFromHtml("<ul><li>First</li><li>Second</li></ul>");
    expect(editableElementToWrt(root)).toBe("[list]\n* First\n* Second\n[/list]\n");
  });

  it("serializes ordered lists as WRT [list]", () => {
    const root = domFromHtml("<ol><li>A</li><li>B</li></ol>");
    expect(editableElementToWrt(root)).toBe("[list]\n* A\n* B\n[/list]\n");
  });

  it("serializes tables", () => {
    const root = domFromHtml(
      "<table><thead><tr><th>Name</th><th>Age</th></tr></thead>" +
      "<tbody><tr><td>Alice</td><td>30</td></tr></tbody></table>",
    );
    const wrt = editableElementToWrt(root);
    expect(wrt).toContain("[table]");
    expect(wrt).toContain("| Name | Age |");
    expect(wrt).toContain("| Alice | 30 |");
    expect(wrt).toContain("[/table]");
  });

  it("serializes images", () => {
    const root = domFromHtml('<img src="/photo.png" alt="A photo">');
    expect(editableElementToWrt(root)).toBe('[img src="/photo.png" alt="A photo"]\n');
  });

  it("escapes literal brackets in text", () => {
    const root = domFromHtml("<p>Use [b] for bold</p>");
    expect(editableElementToWrt(root)).toBe("Use \\[b] for bold\n");
  });

  it("escapes pipe inside table cells", () => {
    const root = domFromHtml(
      "<table><tr><td>a|b</td><td>c</td></tr></table>",
    );
    const wrt = editableElementToWrt(root);
    expect(wrt).toContain("a\\|b");
  });

  it("serializes <br> as newline", () => {
    const root = domFromHtml("<p>Line one<br>Line two</p>");
    expect(editableElementToWrt(root)).toBe("Line one\nLine two\n");
  });

  it("handles multiple paragraphs", () => {
    const root = domFromHtml("<p>First</p><p>Second</p>");
    expect(editableElementToWrt(root)).toBe("First\n\nSecond\n");
  });
});

/* ── Roundtrip: WRT → HTML → DOM → WRT ────────────────────────── */

describe("WRT roundtrip", () => {
  function roundtrip(wrt: string): string {
    const html = wrtToEditableHtml(wrt);
    const root = document.createElement("div");
    root.innerHTML = html;
    return editableElementToWrt(root);
  }

  it("roundtrips plain text", () => {
    expect(roundtrip("Hello world")).toBe("Hello world\n");
  });

  it("roundtrips bold", () => {
    expect(roundtrip("[b]Author[/b]")).toBe("[b]Author[/b]\n");
  });

  it("roundtrips italic", () => {
    expect(roundtrip("[i]emphasis[/i]")).toBe("[i]emphasis[/i]\n");
  });

  it("roundtrips underline", () => {
    expect(roundtrip("[u]underlined[/u]")).toBe("[u]underlined[/u]\n");
  });

  it("roundtrips strikethrough", () => {
    expect(roundtrip("[s]crossed[/s]")).toBe("[s]crossed[/s]\n");
  });

  it("roundtrips headings", () => {
    expect(roundtrip("[h1]Title[/h1]")).toBe("[h1]Title[/h1]\n");
    expect(roundtrip("[h2]Sub[/h2]")).toBe("[h2]Sub[/h2]\n");
    expect(roundtrip("[h3]Section[/h3]")).toBe("[h3]Section[/h3]\n");
  });

  it("roundtrips nested bold+italic", () => {
    expect(roundtrip("[b][i]nested[/i][/b]")).toBe("[b][i]nested[/i][/b]\n");
  });

  it("roundtrips mixed paragraph with formatting", () => {
    const wrt = "[b]Author:[/b] Alice";
    const result = roundtrip(wrt);
    expect(result).toBe("[b]Author:[/b] Alice\n");
  });

  it("roundtrips lists", () => {
    const wrt = "[list]\n* First\n* Second\n[/list]";
    const result = roundtrip(wrt);
    expect(result).toContain("[list]");
    expect(result).toContain("* First");
    expect(result).toContain("* Second");
    expect(result).toContain("[/list]");
  });

  it("roundtrips blockquote", () => {
    const wrt = "[quote]\nWise words\n[/quote]";
    const result = roundtrip(wrt);
    expect(result).toContain("[quote]");
    expect(result).toContain("Wise words");
    expect(result).toContain("[/quote]");
  });

  it("roundtrips tables", () => {
    const wrt = "[table]\n| Col1 | Col2 |\n| A | B |\n[/table]";
    const result = roundtrip(wrt);
    expect(result).toContain("[table]");
    expect(result).toContain("Col1");
    expect(result).toContain("[/table]");
  });

  it("roundtrips images", () => {
    const wrt = '[img src="/photo.png" alt="Photo"]';
    const result = roundtrip(wrt);
    expect(result).toContain('[img src="/photo.png" alt="Photo"]');
  });

  it("roundtrips a multi-block document", () => {
    const wrt = [
      "[h1]Report[/h1]",
      "",
      "[b]Author:[/b] Test User",
      "",
      "[list]",
      "* Item one",
      "* Item two",
      "[/list]",
    ].join("\n");

    const result = roundtrip(wrt);
    expect(result).toContain("[h1]Report[/h1]");
    expect(result).toContain("[b]Author:[/b] Test User");
    expect(result).toContain("* Item one");
    expect(result).toContain("* Item two");
  });
});
