'use client'

import { Bot, Send, Target, User, Zap } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  tools_used?: string[]
  odds?: Record<string, number>
}

export function BaseballChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content:
        "🎯 Welcome to the AI Baseball Analyst! I'm powered by 18 machine learning models trained on 25+ years of MLB data. Ask me anything about baseball predictions, game analysis, or player performance!",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scrollToBottom])

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Call our Python API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_history: messages.slice(-5), // Last 5 messages for context
        }),
      })

      const result = await response.json()

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.response,
        timestamp: new Date(),
        tools_used: result.tools_used,
        odds: result.odds,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-gradient-to-r from-blue-600 to-purple-600">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">AI Baseball Analyst</h2>
              <p className="text-blue-100 text-sm">Powered by 18 ML models & 25+ years of data</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="h-96 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-100'
                }`}
              >
                <div className="flex items-center space-x-2 mb-1">
                  {message.role === 'user' ? (
                    <User className="w-4 h-4" />
                  ) : (
                    <Bot className="w-4 h-4" />
                  )}
                  <span className="text-xs opacity-75">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>

                <p className="text-sm">{message.content}</p>

                {/* Tools used indicator */}
                {message.tools_used && message.tools_used.length > 0 && (
                  <div className="mt-2 flex items-center space-x-1">
                    <Zap className="w-3 h-3 text-yellow-400" />
                    <span className="text-xs text-yellow-400">
                      Used: {message.tools_used.join(', ')}
                    </span>
                  </div>
                )}

                {/* Odds display */}
                {message.odds && (
                  <div className="mt-2 p-2 bg-slate-600 rounded text-xs">
                    <div className="flex items-center space-x-1 mb-1">
                      <Target className="w-3 h-3 text-green-400" />
                      <span className="text-green-400 font-medium">Live Odds</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1 text-slate-300">
                      {Object.entries(message.odds)
                        .slice(0, 6)
                        .map(([key, value]) => (
                          <div key={key} className="flex justify-between">
                            <span>{key.replace('pa_batter_', '').replace('_', ' ')}:</span>
                            <span className="font-mono">{(value * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Bot className="w-4 h-4" />
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                    <div
                      className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"
                      style={{ animationDelay: '0.1s' }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"
                      style={{ animationDelay: '0.2s' }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-slate-700">
          <form onSubmit={sendMessage} className="flex space-x-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about baseball predictions, odds, or analysis..."
              className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors flex items-center space-x-2"
            >
              <Send className="w-4 h-4" />
              <span>Send</span>
            </button>
          </form>

          {/* Quick suggestions */}
          <div className="mt-3 flex flex-wrap gap-2">
            {[
              'What are the odds of a home run?',
              'Simulate this half-inning',
              'Who has the best batting average?',
              "What's the win probability?",
            ].map((suggestion) => (
              <button
                type="button"
                key={suggestion}
                onClick={() => setInput(suggestion)}
                className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-full transition-colors"
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
