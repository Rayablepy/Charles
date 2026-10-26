import { INGEST_API_URL } from "@/lib/rag-upload";

export type Provider = {
  id: string;
  label: string;
  className: string;
  defaultModel: string;
  keyOptional?: boolean;
};

// Featured LangChain chat integrations; Vertex AI, Cohere, Hugging Face excluded
export const FEATURED_PROVIDERS: Provider[] = [
  {
    id: "azure-openai",
    label: "Azure OpenAI",
    className: "AzureChatOpenAI",
    defaultModel: "gpt-4o",
  },
  {
    id: "openai",
    label: "OpenAI",
    className: "ChatOpenAI",
    defaultModel: "gpt-4.1",
  },
  {
    id: "anthropic",
    label: "Anthropic",
    className: "ChatAnthropic",
    defaultModel: "claude-sonnet-4-5",
  },
  {
    id: "google",
    label: "Google",
    className: "ChatGoogleGenerativeAI",
    defaultModel: "gemini-2.5-pro",
  },
  {
    id: "ollama",
    label: "Ollama",
    className: "ChatOllama",
    defaultModel: "llama3.2",
    keyOptional: true,
  },
  {
    id: "groq",
    label: "Groq",
    className: "ChatGroq",
    defaultModel: "llama-3.3-70b-versatile",
  },
  {
    id: "litellm",
    label: "LiteLLM",
    className: "ChatLiteLLM",
    defaultModel: "openai/gpt-4.1",
  },
  {
    id: "mistral",
    label: "Mistral AI",
    className: "ChatMistralAI",
    defaultModel: "mistral-large-latest",
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    className: "ChatOpenRouter",
    defaultModel: "openrouter/auto",
  },
  {
    id: "xai",
    label: "xAI",
    className: "ChatXAI",
    defaultModel: "grok-4",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    className: "ChatDeepSeek",
    defaultModel: "deepseek-chat",
  },
  {
    id: "databricks",
    label: "Databricks",
    className: "ChatDatabricks",
    defaultModel: "databricks-meta-llama-3-3-70b-instruct",
  },
  {
    id: "nvidia",
    label: "NVIDIA",
    className: "ChatNVIDIA",
    defaultModel: "meta/llama-3.3-70b-instruct",
  },
  {
    id: "together",
    label: "Together AI",
    className: "ChatTogether",
    defaultModel: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
  },
  {
    id: "amazon-nova",
    label: "Amazon Nova",
    className: "ChatAmazonNova",
    defaultModel: "amazon.nova-pro-v1:0",
  },
];

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail) return body.detail;
  } catch {
    /* response was not JSON */
  }
  return `request failed (${response.status})`;
}

/*ingest API, not LangGraph*/
export async function saveProviderConfig(
  provider: string,
  model: string,
  apiKey: string,
): Promise<void> {
  const response = await fetch(`${INGEST_API_URL}/provider`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model, api_key: apiKey }),
  });
  if (!response.ok) throw new Error(await readError(response));
}
