import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const markdown = new MarkdownIt({ html: false, linkify: false, breaks: true })
const openLink = markdown.renderer.rules.link_open
markdown.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const href = String(tokens[idx].attrGet('href') || '')
  if (!/^https?:\/\//i.test(href)) tokens[idx].attrSet('href', '')
  return openLink ? openLink(tokens, idx, options, env, self) : self.renderToken(tokens, idx, options)
}

const allowedTags = ['p', 'br', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'pre', 'blockquote', 'a', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td']

export function renderAssistant(content: string) {
  return DOMPurify.sanitize(markdown.render(content || ''), { ALLOWED_TAGS: allowedTags, ALLOWED_ATTR: ['href'] })
}
