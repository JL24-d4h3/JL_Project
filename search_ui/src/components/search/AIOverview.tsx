import { useState, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { dracula } from 'react-syntax-highlighter/dist/esm/styles/prism'

// Eliminar cualquier border/decoration residual del tema
const cleanDracula = Object.fromEntries(
  Object.entries(dracula).map(([sel, styles]) => [
    sel,
    Object.fromEntries(
      Object.entries(styles as Record<string, string>).filter(
        ([p]) => !p.toLowerCase().startsWith('border') &&
                 p !== 'textDecoration' && p !== 'outline'
      )
    )
  ])
)

const IconCopy = () => (
  <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
    <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z"/>
    <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z"/>
  </svg>
)
const IconCheck = () => (
  <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd"/>
  </svg>
)

function CodeRenderer({ inline, className, children }: {
  inline?: boolean
  className?: string
  children?: React.ReactNode
}) {
  const [copied, setCopied] = useState(false)
  const code = String(children ?? '').replace(/\n$/, '')
  const match = /language-(\w+)/.exec(className ?? '')
  const lang = match ? match[1] : 'text'

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [code])

  if (inline) {
    return <code className={className}>{children}</code>
  }

  const bgBody   = 'rgba(11, 16, 40, 0.93)'
  const bgHeader  = 'rgba(7, 10, 26, 0.98)'
  const borderClr = 'rgba(70, 110, 210, 0.22)'

  return (
    <div className="code-block-wrap relative my-4" style={{
      borderRadius: '0.75rem',
      border: `1px solid ${borderClr}`,
      boxShadow: '0 4px 24px rgba(30, 60, 160, 0.13), inset 0 1px 0 rgba(120,160,255,0.07)',
      overflow: 'hidden',
    }}>
      <div className="flex items-center justify-between px-4 py-1.5" style={{
        background: bgHeader,
        borderBottom: `1px solid ${borderClr}`,
      }}>
        <span className="text-[11px] font-mono" style={{ color: 'rgba(140,170,255,0.75)' }}>{lang}</span>
        <button
          onClick={handleCopy}
          className="flex items-center rounded p-1 transition-colors"
          style={{ color: copied ? '#4ade80' : 'rgba(140,170,255,0.50)' }}
          title={copied ? 'Copiado' : 'Copiar'}
        >
          {copied ? <IconCheck /> : <IconCopy />}
        </button>
      </div>
      <SyntaxHighlighter
        language={lang}
        style={cleanDracula}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          fontSize: '0.78rem',
          lineHeight: '1.65',
          background: bgBody,
          padding: '1rem 1.1rem',
        }}
        showLineNumbers={false}
        wrapLongLines={false}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

interface Props {
  text:        string
  isStreaming: boolean
  hasError?:   boolean
  level?:      string
}

export default function AIOverview({ text, isStreaming, hasError, level }: Props) {
  const [expanded, setExpanded] = useState(true)
  useEffect(() => { if (isStreaming) setExpanded(true) }, [isStreaming])

  if (hasError) return null
  if (!text && !isStreaming) return null

  const isGeneral = level === 'L3' || level === 'L4'

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center gap-2 px-5 pt-4 pb-2 border-b border-slate-100">
        <svg className="h-3.5 w-3.5 flex-shrink-0 text-indigo-500" viewBox="0 0 24 24" fill="currentColor">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
        </svg>
        <span className="text-[11px] font-bold uppercase tracking-widest text-slate-500">
          {isGeneral ? 'Respuesta del modelo' : 'Resumen IA'}
        </span>
        {isGeneral && (
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">
            conocimiento general
          </span>
        )}
        {isStreaming && (
          <span className="ml-auto flex items-center gap-1 text-[11px] text-slate-400">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" />
            generando
          </span>
        )}
      </div>

      {isStreaming && !text && (
        <div className="space-y-2 px-5 py-4">
          {[1,2,3].map(i => (
            <div key={i} className={`h-3 animate-pulse rounded bg-slate-100 ${
              i===1?'w-full':i===2?'w-5/6':'w-3/4'
            }`} />
          ))}
        </div>
      )}

      {text && (
        <>
          <div className={`px-5 py-4 ${!expanded ? 'max-h-72 overflow-hidden relative' : ''}`}>
            <div className="md-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{ code: CodeRenderer as any }}
              >
                {text}
              </ReactMarkdown>
              {isStreaming && (
                <span className="inline-block h-4 w-0.5 animate-pulse bg-indigo-500 align-middle ml-0.5" />
              )}
            </div>
            {!expanded && (
              <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-white to-transparent" />
            )}
          </div>

          {!isStreaming && (
            <button
              onClick={() => setExpanded(e => !e)}
              className="flex w-full items-center justify-center gap-1.5 border-t border-slate-100
                py-2.5 text-[11px] font-medium text-slate-400 hover:text-indigo-600 hover:bg-slate-50 transition-colors"
            >
              {expanded ? (
                <><svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M14.77 12.79a.75.75 0 01-1.06-.02L10 8.832 6.29 12.77a.75.75 0 11-1.08-1.04l4.25-4.5a.75.75 0 011.08 0l4.25 4.5a.75.75 0 01-.02 1.06z" clipRule="evenodd"/></svg>mostrar menos</>
              ) : (
                <><svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd"/></svg>ver respuesta completa</>
              )}
            </button>
          )}
        </>
      )}
    </div>
  )
}
