import type {
  LangChainMessage,
  LangChainMessageChunk,
  LangGraphStreamCallback,
} from "@assistant-ui/react-langgraph";

type WireMessage = {
  type?: string;
  content?: unknown;
  additional_kwargs?: Record<string, unknown>;
};

type ContentBlock = { type?: string } & Record<string, unknown>;

type ReasoningKwargs = {
  reasoning_content?: unknown;
  reasoning_details?: unknown;
  reasoning?: unknown;
};

const REASONING_BLOCK_TYPES = new Set(["reasoning", "thinking"]);

const REASONING_BLOCK_INDEX = 0;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object";

const readReasoningText = (kwargs: ReasoningKwargs | undefined): string => {
  if (!kwargs) return "";
  if (typeof kwargs.reasoning_content === "string") {
    const content = kwargs.reasoning_content.trim();
    if (content !== "") return kwargs.reasoning_content;
  }
  if (Array.isArray(kwargs.reasoning_details)) {
    const text = kwargs.reasoning_details
      .map((detail) => {
        if (!isRecord(detail) || typeof detail.text !== "string") return "";
        return detail.text;
      })
      .join("");
    if (text.trim() !== "") return text;
  }
  return "";
};

const hasReasoningBlock = (content: unknown): boolean =>
  Array.isArray(content) &&
  content.some(
    (block) => isRecord(block) && REASONING_BLOCK_TYPES.has(block.type as string),
  );

const toContentBlocks = (content: unknown): ContentBlock[] => {
  if (typeof content === "string") {
    return content === "" ? [] : [{ type: "text", text: content }];
  }
  if (!Array.isArray(content)) return [];
  return content.filter(isRecord);
};

export function withReasoningParts<TMessage extends WireMessage>(
  message: TMessage,
): TMessage {
  if (message.type !== "ai" && message.type !== "AIMessageChunk") {
    return message;
  }
  const kwargs = message.additional_kwargs as ReasoningKwargs | undefined;
  if (kwargs?.reasoning !== undefined) return message;
  const reasoning = readReasoningText(kwargs);
  if (reasoning === "") return message;
  if (hasReasoningBlock(message.content)) return message;
  return {
    ...message,
    content: [
      { type: "reasoning", reasoning, index: REASONING_BLOCK_INDEX },
      ...toContentBlocks(message.content),
    ],
  } as TMessage;
}

export function withReasoningInMessages<
  TMessage extends LangChainMessage | LangChainMessageChunk,
>(messages: TMessage[]): TMessage[] {
  return messages.map((message) =>
    withReasoningParts(message as TMessage & WireMessage),
  );
}

const withReasoningInState = (state: unknown): unknown => {
  if (!isRecord(state)) return state;
  if (Array.isArray(state.messages)) {
    return {
      ...state,
      messages: (state.messages as WireMessage[]).map(withReasoningParts),
    };
  }
  let changed = false;
  const next: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(state)) {
    if (isRecord(value) && Array.isArray(value.messages)) {
      next[key] = {
        ...value,
        messages: (value.messages as WireMessage[]).map(withReasoningParts),
      };
      changed = true;
      continue;
    }
    next[key] = value;
  }
  return changed ? next : state;
};

const withReasoningInEventData = (
  eventType: string,
  data: unknown,
): unknown => {
  const pipeIndex = eventType.indexOf("|");
  switch (pipeIndex === -1 ? eventType : eventType.slice(0, pipeIndex)) {
    case "messages": {
      if (!Array.isArray(data)) return data;
      const [message, metadata] = data;
      return [
        isRecord(message) ? withReasoningParts(message) : message,
        metadata,
      ];
    }
    case "messages/partial":
    case "messages/complete":
      return Array.isArray(data)
        ? (data as WireMessage[]).map(withReasoningParts)
        : data;
    case "values":
    case "updates":
      return withReasoningInState(data);
    default:
      return data;
  }
};

export function withReasoningEvents<TMessage extends LangChainMessage>(
  stream: LangGraphStreamCallback<TMessage>,
): LangGraphStreamCallback<TMessage> {
  return async (messages, config) => {
    const response = await stream(messages, config);
    return (async function* () {
      for await (const event of response) {
        yield {
          ...event,
          data: withReasoningInEventData(event.event, event.data),
        };
      }
    })();
  };
}