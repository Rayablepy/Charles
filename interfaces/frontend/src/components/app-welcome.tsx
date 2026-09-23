"use client";

export function AppWelcome() {
  return (
    <div className="mb-6 flex flex-col px-2">
      <p className="app-welcome-brand">Charles</p>
      <h2 className="app-welcome-title">How can I help you today?</h2>
      <p className="app-welcome-subtitle">
        A local LangGraph agent. Ask about your codebase, files, tools, and
        long-term memory — or pick an earlier conversation from the sidebar.
      </p>
    </div>
  );
}