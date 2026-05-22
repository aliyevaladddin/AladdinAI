import Link from "next/link";

interface WordmarkProps {
  href?: string;
  size?: number;
}

/**
 * "AladdinAI" wordmark — uses the active theme's display font.
 * The "AI" half is italic and amber-tinted.
 */
export function Wordmark({ href = "/", size = 17 }: WordmarkProps) {
  const content = (
    <span className="wordmark" style={{ fontSize: size }}>
      Aladdin<i>AI</i>
    </span>
  );

  if (!href) return content;
  return (
    <Link href={href} aria-label="AladdinAI home" style={{ textDecoration: "none" }}>
      {content}
    </Link>
  );
}
