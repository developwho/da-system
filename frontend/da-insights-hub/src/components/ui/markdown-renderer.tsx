import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div
      className={cn(
        'prose prose-sm sm:prose-base max-w-none dark:prose-invert',
        'prose-headings:font-semibold prose-headings:text-foreground',
        'prose-p:text-foreground/90 prose-li:text-foreground/90 prose-strong:text-foreground',
        'prose-a:text-primary hover:prose-a:text-primary/80',
        "prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:before:content-[''] prose-code:after:content-['']",
        'prose-pre:bg-muted prose-pre:text-foreground prose-pre:border prose-pre:border-border',
        'prose-hr:border-border',
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          a: ({ href, children, ...props }) => {
            const isExternal = Boolean(href?.startsWith('http'));
            return (
              <a
                href={href}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noreferrer noopener' : undefined}
                {...props}
              >
                {children}
              </a>
            );
          },
          table: ({ children, ...props }) => (
            <div className="my-4 overflow-x-auto rounded-md border border-border">
              <table className="w-full border-collapse text-sm" {...props}>
                {children}
              </table>
            </div>
          ),
          thead: ({ children, ...props }) => (
            <thead className="bg-muted/50" {...props}>
              {children}
            </thead>
          ),
          th: ({ children, ...props }) => (
            <th className="border-b border-border px-3 py-2 text-left font-semibold text-foreground" {...props}>
              {children}
            </th>
          ),
          td: ({ children, ...props }) => (
            <td className="border-b border-border/70 px-3 py-2 align-top text-foreground/90 last:border-b-0" {...props}>
              {children}
            </td>
          ),
          blockquote: ({ children, ...props }) => (
            <blockquote className="border-l-4 border-primary/40 bg-muted/30 px-4 py-1 text-foreground/80" {...props}>
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
