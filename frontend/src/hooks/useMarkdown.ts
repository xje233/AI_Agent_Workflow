// Markdown 渲染：将模型输出转换为带代码高亮的受控 HTML。
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import { markedHighlight } from 'marked-highlight'
import { useEffect, useMemo, useRef, useState } from 'react'
import 'highlight.js/styles/github-dark.css'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('python', python)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)

// 已注册语言优先精确高亮，未知语言回退到自动识别。
marked.use(markedHighlight({ highlight(code, language) {
  return language && hljs.getLanguage(language) ? hljs.highlight(code, { language }).value : hljs.highlightAuto(code).value
} }))
marked.use({ breaks: true, gfm: true })

export function renderMarkdown(value: string) { return marked.parse(value) as string }

const STREAM_MARKDOWN_INTERVAL = 100

export function useRenderedMarkdown(value: string, streaming: boolean) {
  const [throttledValue, setThrottledValue] = useState(value)
  const latestValue = useRef(value)
  const lastRenderAt = useRef(0)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    latestValue.current = value
    if (!streaming) {
      if (timer.current !== null) window.clearTimeout(timer.current)
      timer.current = null
      setThrottledValue(value)
      return
    }

    const elapsed = performance.now() - lastRenderAt.current
    if (elapsed >= STREAM_MARKDOWN_INTERVAL) {
      lastRenderAt.current = performance.now()
      setThrottledValue(value)
      return
    }

    if (timer.current === null) {
      timer.current = window.setTimeout(() => {
        timer.current = null
        lastRenderAt.current = performance.now()
        setThrottledValue(latestValue.current)
      }, STREAM_MARKDOWN_INTERVAL - elapsed)
    }
  }, [streaming, value])

  useEffect(() => () => {
    if (timer.current !== null) window.clearTimeout(timer.current)
  }, [])

  return useMemo(() => renderMarkdown(streaming ? throttledValue : value), [streaming, throttledValue, value])
}
