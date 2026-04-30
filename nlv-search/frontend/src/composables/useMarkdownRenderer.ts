import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";

export function useMarkdownRenderer() {
  const markdown = new MarkdownIt({
    linkify: true,
    breaks: true,
  });

  const defaultLinkRenderer =
    markdown.renderer.rules.link_open ||
    ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options));

  markdown.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const token = tokens[idx];
    token.attrSet("target", "_blank");
    token.attrSet("rel", "noopener noreferrer");
    return defaultLinkRenderer(tokens, idx, options, env, self);
  };

  function renderMarkdown(content?: string): string {
    if (!content) return "";
    const rawHtml = markdown.render(content);
    return DOMPurify.sanitize(rawHtml);
  }

  return { renderMarkdown };
}
