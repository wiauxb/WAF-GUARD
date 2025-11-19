import { wafApi, analyzerApi, chatbotApi, webAppApi } from './api'

export interface ServiceHealth {
  status: 'online' | 'offline'
  message?: string
}

export async function checkWafHealth(): Promise<ServiceHealth> {
  try {
    const response = await wafApi.get('/health')
    return { status: 'online' }
  } catch (error) {
    return { status: 'offline', message: 'WAF service unavailable' }
  }
}

export async function checkAnalyzerHealth(): Promise<ServiceHealth> {
  try {
    // The analyzer doesn't have a /health endpoint, so we'll just check if it responds
    await analyzerApi.get('/health')
    return { status: 'online' }
  } catch (error) {
    return { status: 'offline', message: 'Analyzer service unavailable' }
  }
}

export async function checkChatbotHealth(): Promise<ServiceHealth> {
  try {
    // Try to access the threads endpoint as a health check
    await chatbotApi.get('/chat/threads')
    return { status: 'online' }
  } catch (error) {
    return { status: 'offline', message: 'Chatbot service unavailable' }
  }
}

export async function checkWebAppHealth(): Promise<ServiceHealth> {
  try {
    await webAppApi.get('/configs')
    return { status: 'online' }
  } catch (error) {
    return { status: 'offline', message: 'Web App service unavailable' }
  }
}

export async function checkAllServices() {
  const [waf, analyzer, chatbot, webApp] = await Promise.all([
    checkWafHealth(),
    checkAnalyzerHealth(),
    checkChatbotHealth(),
    checkWebAppHealth(),
  ])

  return {
    waf,
    analyzer,
    chatbot,
    webApp,
    allOnline: [waf, analyzer, chatbot, webApp].every(s => s.status === 'online'),
  }
}
