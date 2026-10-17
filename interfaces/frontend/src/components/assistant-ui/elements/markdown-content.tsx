"use client";

import { TextMessagePartProvider } from "@assistant-ui/react";

import { MarkdownText } from "@/components/assistant-ui/elements/markdown-text";

type MarkdownContentProps = {
  text: string;
};

export function MarkdownContent({ text }: MarkdownContentProps) {
  return (
    <TextMessagePartProvider text={text} isRunning={false}>
      <MarkdownText smooth={false} />
    </TextMessagePartProvider>
  );
}
