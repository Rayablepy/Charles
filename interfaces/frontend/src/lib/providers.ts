import { useSyncExternalStore } from "react";
import { INGEST_API_URL } from "@/lib/rag-upload";

export type Provider = {
  id: string;
  label: string;
  className: string;
  defaultModel: string;
  keyOptional?: boolean;
};

export type ConfiguredProvider = {
  provider: string;
  model: string;
  active: boolean;
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

export async function listProviders(): Promise<ConfiguredProvider[]> {
  const response = await fetch(`${INGEST_API_URL}/providers`);
  if (!response.ok) throw new Error(await readError(response));
  const body = (await response.json()) as { providers?: ConfiguredProvider[] };
  return body.providers ?? [];
}

export async function activateProvider(provider: string): Promise<void> {
  const response = await fetch(`${INGEST_API_URL}/provider/use`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
  if (!response.ok) throw new Error(await readError(response));
}

export async function removeProviderConfig(provider: string): Promise<void> {
  const response = await fetch(
    `${INGEST_API_URL}/provider/${encodeURIComponent(provider)}`,
    { method: "DELETE" },
  );
  if (!response.ok) throw new Error(await readError(response));
}

let providerVerified: boolean | null = null;
const providerListeners = new Set<() => void>();

function subscribeProvider(listener: () => void) {
  providerListeners.add(listener);
  return () => providerListeners.delete(listener);
}

function setProviderVerified(value: boolean) {
  if (providerVerified === value) return;
  providerVerified = value;
  for (const listener of providerListeners) listener();
}

export function useProviderVerified(): boolean | null {
  return useSyncExternalStore(subscribeProvider, () => providerVerified, () => null);
}

export async function verifyProvider(): Promise<boolean> {
  try {
    const response = await fetch(`${INGEST_API_URL}/provider/verify`, {
      method: "POST",
    });
    if (!response.ok) throw new Error(await readError(response));
    const body = (await response.json()) as { verified?: boolean };
    const verified = body.verified === true;
    setProviderVerified(verified);
    return verified;
  } catch (error) {
    setProviderVerified(false);
    throw error;
  }
}
