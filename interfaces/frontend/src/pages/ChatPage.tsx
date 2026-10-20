"use client";

import { useState } from "react";
import { ChatRuntimeProvider } from "@/components/chat-runtime";
import { ChatSidebar } from "@/components/chat-sidebar";
import { AppWelcome } from "@/components/app-welcome";
import { ProjectFiles } from "@/components/project-files";
import { InterruptPrompt } from "@/components/assistant-ui/elements/interrupt.aui";
import { Thread } from "@/components/assistant-ui/elements/thread.aui";

export default function ChatPage() {
  const [selectedThreadId, setSelectedThreadId] = useState<
    string | undefined
  >(undefined);
  const [showProjectFiles, setShowProjectFiles] = useState(false);

  const handleSelectThread = (threadId: string | undefined) => {
    setShowProjectFiles(false);
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
          showProjectFiles={showProjectFiles}
          onOpenProjectFiles={() => setShowProjectFiles(true)}
        />
        <main className="app-main">
          {showProjectFiles ? (
            <ProjectFiles />
          ) : (
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
