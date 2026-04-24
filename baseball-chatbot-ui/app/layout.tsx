import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Retrosheet Command Center',
  description: 'Chat, simulate, backtest, and inspect Retrosheet prediction models',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  )
}
