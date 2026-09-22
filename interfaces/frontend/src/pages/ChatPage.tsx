"use client";

import { ChatRuntimeProvider } from "@/components/chat-runtime";
import { Thread } from "@/components/assistant-ui/elements/thread.aui";

/**
 * Main chat page. Layout styling lives in the central stylesheet
 * (src/index.css) rather than inline in JSX.
 */
export default function ChatPage() {
  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Charles</h1>
        <p className="app-subtitle">Local agent · chat interface</p>
      </header>
      <main className="app-thread">
        <ChatRuntimeProvider>
          <Thread />
        </ChatRuntimeProvider>
      </main>
    </div>
  );
}