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
import 'highlight.js/styles/github-dark.css'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('python', python)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)

marked.use(markedHighlight({ highlight(code, language) {
  return language && hljs.getLanguage(language) ? hljs.highlight(code, { language }).value : hljs.highlightAuto(code).value
} }))
marked.use({ breaks: true, gfm: true })

export function renderMarkdown(value: string) { return marked.parse(value) as string }
