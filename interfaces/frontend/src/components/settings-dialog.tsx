"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeftIcon,
  CheckIcon,
  EyeIcon,
  EyeOffIcon,
  MoonIcon,
  PaletteIcon,
  PlugIcon,
  SettingsIcon,
  SunIcon,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { applyTheme, readTheme, type Theme } from "@/lib/theme";
import {
  FEATURED_PROVIDERS,
  saveProviderConfig,
  verifyProvider,
  type Provider,
} from "@/lib/providers";

type SettingsTab = "appearance" | "providers";

type ProviderConfig = {
  model: string;
  apiKey: string;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

const TABS: { id: SettingsTab; label: string; icon: typeof PaletteIcon }[] = [
  { id: "appearance", label: "Appearance", icon: PaletteIcon },
  { id: "providers", label: "Providers", icon: PlugIcon },
];

export function SettingsDialog() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<SettingsTab>("appearance");
  const [theme, setTheme] = useState<Theme>(() => readTheme());
  const [configured, setConfigured] = useState<ProviderConfig | null>(null);
  const [configuredProviderId, setConfiguredProviderId] = useState<
    string | null
  >(null);
  const [activeProviderId, setActiveProviderId] = useState<string | null>(null);
  const [lockedNotice, setLockedNotice] = useState("");
  const [draftModel, setDraftModel] = useState("");
  const [draftKey, setDraftKey] = useState("");
  const [keyVisible, setKeyVisible] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const configuredProvider =
    FEATURED_PROVIDERS.find(
      (provider) => provider.id === configuredProviderId,
    ) ?? null;
  const activeProvider =
    FEATURED_PROVIDERS.find((provider) => provider.id === activeProviderId) ??
    null;
  const activeConfig =
    activeProvider && activeProvider.id === configuredProviderId
      ? configured
      : null;

  const canSave =
    activeProvider !== null &&
    draftModel.trim().length > 0 &&
    (activeProvider.keyOptional === true || draftKey.trim().length > 0);

  const closeProvider = () => {
    setActiveProviderId(null);
    setKeyVisible(false);
    setSaveError("");
  };

  const startProvider = (provider: Provider) => {
    if (configuredProvider && configuredProvider.id !== provider.id) {
      setLockedNotice(
        `Remove ${configuredProvider.label} before choosing another provider.`,
      );
      return;
    }
    const existing = provider.id === configuredProviderId ? configured : null;
    setLockedNotice("");
    setActiveProviderId(provider.id);
    setDraftModel(existing?.model ?? "");
    setDraftKey(existing?.apiKey ?? "");
    setKeyVisible(false);
    setSaveError("");
  };

  const saveProvider = async () => {
    if (!activeProvider || !canSave || saving) return;
    setSaving(true);
    setSaveError("");
    try {
      await saveProviderConfig(
        activeProvider.id,
        draftModel.trim(),
        draftKey.trim(),
      );
      const verified = await verifyProvider();
      if (!verified) {
        setSaveError("Provider could not be verified.");
        return;
      }
      setConfigured({
        model: draftModel.trim(),
        apiKey: draftKey.trim(),
      });
      setConfiguredProviderId(activeProvider.id);
      setLockedNotice("");
      closeProvider();
    } catch (error) {
      setSaveError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const removeProvider = () => {
    if (!activeProvider) return;
    setConfigured(null);
    setConfiguredProviderId(null);
    setLockedNotice("");
    closeProvider();
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) closeProvider();
      }}
    >
      <DialogTrigger
        className="app-settings-trigger"
        aria-label="Open settings"
        title="Settings"
      >
        <SettingsIcon className="size-4" />
      </DialogTrigger>
      <DialogContent className="app-settings-dialog">
        <aside className="app-settings-rail">
          <div className="app-settings-rail-header">
            <DialogTitle className="app-settings-rail-title">
              Settings
            </DialogTitle>
            <DialogDescription className="sr-only">
              Manage appearance and model providers.
            </DialogDescription>
          </div>
          <nav className="app-settings-nav" aria-label="Settings sections">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                className={cn(
                  "app-settings-nav-item",
                  tab === id && "app-settings-nav-item-active",
                )}
                onClick={() => {
                  setTab(id);
                  closeProvider();
                }}
                aria-current={tab === id ? "true" : undefined}
              >
                <Icon className="size-4" />
                <span>{label}</span>
                {id === "providers" && configuredProviderId && (
                  <span className="app-settings-nav-count">1</span>
                )}
              </button>
            ))}
          </nav>
        </aside>

        <section className="app-settings-main">
          {tab === "appearance" ? (
            <div className="app-settings-panel">
              <header className="app-settings-header">
                <h2 className="app-settings-title">Appearance</h2>
                <p className="app-settings-note">
                  Choose how Charles looks while you work.
                </p>
              </header>
              <div className="app-settings-card">
                <div className="app-settings-card-text">
                  <p className="app-settings-card-title">Theme</p>
                  <p className="app-settings-card-note">
                    Switch between light and dark mode.
                  </p>
                </div>
                <div
                  className="app-theme-switch"
                  role="group"
                  aria-label="Theme"
                >
                  <button
                    type="button"
                    className={cn(
                      "app-theme-option",
                      theme === "light" && "app-theme-option-active",
                    )}
                    onClick={() => setTheme("light")}
                    aria-pressed={theme === "light"}
                  >
                    <SunIcon className="size-3.5" />
                    <span>Light</span>
                  </button>
                  <button
                    type="button"
                    className={cn(
                      "app-theme-option",
                      theme === "dark" && "app-theme-option-active",
                    )}
                    onClick={() => setTheme("dark")}
                    aria-pressed={theme === "dark"}
                  >
                    <MoonIcon className="size-3.5" />
                    <span>Dark</span>
                  </button>
                </div>
              </div>
            </div>
          ) : activeProvider ? (
            <div className="app-settings-panel">
              <button
                type="button"
                className="app-settings-back"
                onClick={closeProvider}
              >
                <ArrowLeftIcon className="size-3.5" />
                <span>All providers</span>
              </button>
              <header className="app-settings-header">
                <h2 className="app-settings-title">{activeProvider.label}</h2>
              </header>
              <form
                className="app-settings-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void saveProvider();
                }}
              >
                <div className="app-field">
                  <label className="app-field-label" htmlFor="provider-model">
                    Model name
                  </label>
                  <input
                    id="provider-model"
                    autoFocus
                    className="app-field-input"
                    value={draftModel}
                    onChange={(event) => setDraftModel(event.target.value)}
                    placeholder={activeProvider.defaultModel}
                    autoComplete="off"
                  />
                </div>
                <div className="app-field">
                  <label className="app-field-label" htmlFor="provider-key">
                    API key
                    {activeProvider.keyOptional ? " (optional)" : ""}
                  </label>
                  <span className="app-field-row">
                    <input
                      id="provider-key"
                      className="app-field-row-input"
                      type={keyVisible ? "text" : "password"}
                      value={draftKey}
                      onChange={(event) => setDraftKey(event.target.value)}
                      placeholder={
                        activeProvider.keyOptional ? "Not required" : "sk-..."
                      }
                      autoComplete="off"
                    />
                    <button
                      type="button"
                      className="app-field-eye"
                      onClick={() => setKeyVisible((current) => !current)}
                      aria-label={
                        keyVisible ? "Hide API key" : "Show API key"
                      }
                    >
                      {keyVisible ? (
                        <EyeOffIcon className="size-3.5" />
                      ) : (
                        <EyeIcon className="size-3.5" />
                      )}
                    </button>
                  </span>
                </div>
                <p className="app-field-hint">
                  Keys are sent to the local ingest API when you save.
                </p>
                {saveError && (
                  <p className="app-settings-error">{saveError}</p>
                )}
                <div className="app-settings-actions">
                  {activeConfig && (
                    <button
                      type="button"
                      className="app-dialog-btn app-settings-remove"
                      onClick={removeProvider}
                    >
                      Remove
                    </button>
                  )}
                  <button
                    type="button"
                    className="app-dialog-btn"
                    onClick={closeProvider}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="app-dialog-btn app-dialog-btn-primary"
                    disabled={!canSave || saving}
                  >
                    {saving ? "Saving…" : "Save"}
                  </button>
                </div>
              </form>
            </div>
          ) : (
            <div className="app-settings-panel">
              <header className="app-settings-header">
                <h2 className="app-settings-title">Providers</h2>
                <p className="app-settings-note">
                  Pick one featured provider, then set its model and API key.
                </p>
              </header>
              {lockedNotice && (
                <p
                  className="app-settings-note app-provider-notice"
                  role="status"
                >
                  {lockedNotice}
                </p>
              )}
              <div className="app-provider-grid">
                {FEATURED_PROVIDERS.map((provider) => {
                  const enabled = provider.id === configuredProviderId;
                  const locked = configuredProviderId !== null && !enabled;
                  return (
                    <button
                      key={provider.id}
                      type="button"
                      className={cn(
                        "app-provider-card",
                        enabled && "app-provider-card-enabled",
                        locked && "app-provider-card-locked",
                      )}
                      onClick={() => startProvider(provider)}
                      aria-disabled={locked || undefined}
                    >
                      <span className="app-provider-info">
                        <span className="app-provider-name">
                          {provider.label}
                        </span>
                      </span>
                      {enabled && (
                        <CheckIcon className="app-provider-check" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </section>
      </DialogContent>
    </Dialog>
  );
}
