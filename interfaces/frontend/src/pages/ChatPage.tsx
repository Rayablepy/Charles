"use client";

import { useState } from "react";
import { ChatRuntimeProvider } from "@/components/chat-runtime";
import { ChatSidebar, type AppView } from "@/components/chat-sidebar";
import { AppWelcome } from "@/components/app-welcome";
import { FileBrowser } from "@/components/file-browser";
import { InterruptPrompt } from "@/components/assistant-ui/elements/interrupt.aui";
import { Thread } from "@/components/assistant-ui/elements/thread.aui";

export default function ChatPage() {
  const [selectedThreadId, setSelectedThreadId] = useState<
    string | undefined
  >(undefined);
  const [view, setView] = useState<AppView>("chat");

  const handleSelectThread = (threadId: string | undefined) => {
    setView("chat");
    setSelectedThreadId(threadId);
  };

  return (
    <div className="app">
      <ChatRuntimeProvider
        threadId={selectedThreadId}
        onThreadIdChange={setSelectedThreadId}
      >
        <ChatSidebar
          activeThreadId={selectedThreadId}
          onSelect={handleSelectThread}
          view={view}
          onSelectView={setView}
        />
        <main className="app-main">
          {view === "project" && (
            <FileBrowser scope="project" title="Project Files" />
          )}
          {view === "skills" && (
            <FileBrowser
              scope="skills"
              title="Skills"
              description="Editable skills follow your requests; locked skills need your approval before the agent writes."
            />
          )}
          {view === "chat" && (
            <div className="app-thread">
              <Thread
                components={{
                  Welcome: AppWelcome,
                  Interrupt: InterruptPrompt,
                }}
              />
            </div>
          )}
        </main>
      </ChatRuntimeProvider>
    </div>
  );
}
