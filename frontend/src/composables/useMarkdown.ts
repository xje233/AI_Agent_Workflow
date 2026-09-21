import { marked } from 'marked'
import hljs from 'highlight.js'
import { markedHighlight } from 'marked-highlight'
import 'highlight.js/styles/github-dark.css'

// 使用 marked-highlight 扩展替代已废弃的 highlight 选项（marked v5+）
marked.use(
  markedHighlight({
    highlight(code: string, lang: string) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value
      }
      return hljs.highlightAuto(code).value
    },
  })
)

marked.use({ breaks: true, gfm: true })

export function useMarkdown() {
  function render(markdown: string): string {
    return marked.parse(markdown) as string
  }

  return { render }
}
