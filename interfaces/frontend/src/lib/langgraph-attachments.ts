import type {
  AttachmentAdapter,
  CompleteAttachment,
  PendingAttachment,
} from "@assistant-ui/react";
import {
  ACCEPT,
  MAX_UPLOAD_BYTES,
  tooLargeMessage,
  uploadToMemory,
} from "@/lib/rag-upload";

function escapeLabel(name: string) {
  return name.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

function isTooLargeAttachment(attachment: PendingAttachment): attachment is PendingAttachment & {
  status: { type: "incomplete"; reason: "error"; message?: string };
} {
  return (
    attachment.status.type === "incomplete" &&
    attachment.status.reason === "error" &&
    attachment.file.size > MAX_UPLOAD_BYTES
  );
}

export class RagUploadAttachmentAdapter implements AttachmentAdapter {
  public readonly accept = ACCEPT;

  async add(state: { file: File }): Promise<PendingAttachment> {
    if (state.file.size > MAX_UPLOAD_BYTES) {
      return {
        id: crypto.randomUUID(),
        type: "document",
        name: state.file.name,
        contentType: state.file.type,
        file: state.file,
        status: {
          type: "incomplete",
          reason: "error",
          message: tooLargeMessage(state.file.name, state.file.size),
        },
      };
    }
    return {
      id: crypto.randomUUID(),
      type: "document",
      name: state.file.name,
      contentType: state.file.type,
      file: state.file,
      status: { type: "requires-action", reason: "composer-send" },
    };
  }

  async send(attachment: PendingAttachment): Promise<CompleteAttachment> {
    if (isTooLargeAttachment(attachment)) {
      throw new Error(
        attachment.status.message ??
          tooLargeMessage(attachment.name, attachment.file.size),
      );
    }
    const source = await uploadToMemory(attachment.file);
    return {
      ...attachment,
      status: { type: "complete" },
      content: [
        {
          type: "text",
          text: `[The file "${escapeLabel(
            source,
          )}" was added to the knowledge base and can be retrieved via query_data.]`,
        },
      ],
    };
  }

  async remove() {}
}