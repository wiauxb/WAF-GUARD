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
  const { theme } = useTheme()

  return (
    <div className={className}>
      <Editor
        height={height}
        defaultLanguage={language}
        language={language}
        value={value}
        onChange={onChange}
        theme={theme === 'dark' ? 'vs-dark' : 'light'}
        options={{
          readOnly,
          minimap: { enabled: true },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
        }}
        loading={<LoadingSpinner />}
      />
    </div>
  )
}
