'use client'

import { Editor } from '@monaco-editor/react'
import { useTheme } from 'next-themes'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface CodeEditorProps {
  value: string
  onChange?: (value: string | undefined) => void
  language?: string
  readOnly?: boolean
  height?: string
  className?: string
}

export function CodeEditor({
  value,
  onChange,
  language = 'plaintext',
  readOnly = false,
  height = '600px',
  className = '',
}: CodeEditorProps) {
  const { theme, resolvedTheme } = useTheme()

  // Use resolvedTheme to get the actual theme (not 'system')
  const editorTheme = (resolvedTheme === 'dark' || theme === 'dark') ? 'light' : 'light'

  return (
    <div className={`w-full h-full ${className}`} style={{ minHeight: '300px' }}>
      <Editor
        height={height}
        defaultLanguage={language}
        language={language}
        value={value}
        onChange={onChange}
        theme={editorTheme}
        options={{
          readOnly,
          minimap: { enabled: false }, // Disable minimap for better space usage
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          folding: true,
          lineDecorationsWidth: 10,
          lineNumbersMinChars: 3,
          glyphMargin: false,
          scrollbar: {
            vertical: 'visible',
            horizontal: 'visible',
            useShadows: false,
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10,
          },
          overviewRulerLanes: 0,
          hideCursorInOverviewRuler: true,
          overviewRulerBorder: false,
          renderLineHighlight: 'line',
          selectOnLineNumbers: true,
          roundedSelection: false,
          cursorStyle: 'line',
          cursorBlinking: 'blink',
          padding: { top: 10, bottom: 10 },
        }}
        loading={
          <div className="flex items-center justify-center h-full w-full">
            <LoadingSpinner />
          </div>
        }
      />
    </div>
  )
}
