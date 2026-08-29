'use client'

import { useMemo } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { cn } from '@/lib/utils'

/**
 * Render assistant markdown.
 *
 * The model writes `**bold**`, lists, tables and fenced code; the chat used
 * `whitespace-pre-wrap`, so all of that showed up as literal asterisks and pipes.
 *
 * SANITISED, not trusted. This is `dangerouslySetInnerHTML`, and the text is model output
 * that can quote whatever a user typed — so anything a browser would execute has to be
 * stripped BEFORE it reaches the DOM. DOMPurify does that; the allow-list below is the
 * markdown subset and nothing else.
 */
const ALLOWED_TAGS = [
  'p', 'br', 'strong', 'em', 'del', 'code', 'pre', 'blockquote',
  'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a', 'hr',
]

export function Markdown({ content, className }: { content: string; className?: string }) {
  const html = useMemo(() => {
    const raw = marked.parse(content ?? '', { async: false, breaks: true }) as string
    return DOMPurify.sanitize(raw, {
      ALLOWED_TAGS,
      ALLOWED_ATTR: ['href', 'title'],
      // Anchors only, and only to schemes that cannot execute — no javascript:, no data:.
      ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|#)/i,
    })
  }, [content])

  return (
    <div
      // Tailwind v4 here has no typography plugin, so the element styles are explicit.
      // Sized down to sit inside a chat bubble rather than read as a document.
      className={cn(
        'text-sm leading-relaxed break-words',
        '[&_p]:my-1 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0',
        '[&_strong]:font-semibold',
        '[&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-5',
        '[&_ol]:my-1 [&_ol]:list-decimal [&_ol]:pl-5',
        '[&_li]:my-0.5',
        '[&_h1]:text-base [&_h1]:font-semibold [&_h1]:mt-2 [&_h1]:mb-1',
        '[&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mt-2 [&_h2]:mb-1',
        '[&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mt-2 [&_h3]:mb-1',
        '[&_code]:rounded [&_code]:bg-black/10 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs',
        '[&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-black/10 [&_pre]:p-2',
        // A fenced block should not inherit the inline-code chip styling.
        '[&_pre_code]:bg-transparent [&_pre_code]:p-0',
        '[&_blockquote]:my-1 [&_blockquote]:border-l-2 [&_blockquote]:pl-2 [&_blockquote]:opacity-80',
        '[&_a]:underline [&_a]:underline-offset-2',
        '[&_table]:my-2 [&_table]:block [&_table]:w-full [&_table]:overflow-x-auto [&_table]:text-xs',
        '[&_th]:border [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-medium',
        '[&_td]:border [&_td]:px-2 [&_td]:py-1',
        '[&_hr]:my-2 [&_hr]:border-t',
        className,
      )}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
