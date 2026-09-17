import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { ProviderBadge } from "@/components/ProviderBadge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { Provider } from "@/types";

export type ProviderSettingsState = "loading" | "error" | "ready";
export type SelectorKind = "answer" | "index";

export interface ProviderSettingsProps {
  state: ProviderSettingsState;
  providers: Provider[];
  answerProviderId: string;
  answerModel: string;
  indexProviderId: string;
  indexModel: string;
  /** Hosted provider awaiting confirmation, null when no dialog is open. */
  pendingProvider: Provider | null;
  onSelect: (kind: SelectorKind, providerId: string) => void;
  onModelChange: (kind: SelectorKind, model: string) => void;
  onConfirmHosted: () => void;
  onCancelHosted: () => void;
  onRetry: () => void;
}

export function ProviderSettings(props: ProviderSettingsProps) {
  const { state, providers, pendingProvider } = props;

  if (state === "loading") {
    return (
      <div className="mx-auto w-full max-w-[720px] space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="mx-auto w-full max-w-[720px]">
        <div className="card-surface space-y-3">
          <p>The provider list could not be loaded.</p>
          <Button type="button" variant="outline" size="sm" onClick={props.onRetry}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-[720px] space-y-6">
      <Selector
        kind="answer"
        heading="Answer model"
        description="Used to write answers on the Ask page."
        providers={providers}
        selectedId={props.answerProviderId}
        selectedModel={props.answerModel}
        onSelect={props.onSelect}
        onModelChange={props.onModelChange}
      />

      <Selector
        kind="index"
        heading="Index model"
        description="Used to index your CV and job descriptions for retrieval."
        providers={providers}
        selectedId={props.indexProviderId}
        selectedModel={props.indexModel}
        onSelect={props.onSelect}
        onModelChange={props.onModelChange}
      />

      <AlertDialog
        open={pendingProvider !== null}
        onOpenChange={(open) => {
          if (!open) props.onCancelHosted();
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Send your documents to {pendingProvider?.name}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Your CV and job descriptions will be sent to {pendingProvider?.name} to
              generate answers. They leave this machine. This is a normal way to run the
              tool. Choose it only if you are comfortable with that.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={props.onCancelHosted}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className={buttonVariants({ variant: "outline" })}
              onClick={props.onConfirmHosted}
            >
              Use {pendingProvider?.name}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function Selector({
  kind,
  heading,
  description,
  providers,
  selectedId,
  selectedModel,
  onSelect,
  onModelChange,
}: {
  kind: SelectorKind;
  heading: string;
  description: string;
  providers: Provider[];
  selectedId: string;
  selectedModel: string;
  onSelect: (kind: SelectorKind, providerId: string) => void;
  onModelChange: (kind: SelectorKind, model: string) => void;
}) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-base">{heading}</h2>
        <p className="text-muted-foreground">{description}</p>
      </div>

      <RadioGroup
        value={selectedId}
        onValueChange={(value) => onSelect(kind, value)}
        className="gap-3"
      >
        {providers.map((provider) => {
          const radioId = `${kind}-${provider.id}`;
          const reasonId = `${radioId}-reason`;
          const active = provider.id === selectedId;

          return (
            <div key={provider.id} className="card-surface space-y-3">
              <div className="flex items-start gap-3">
                <RadioGroupItem
                  id={radioId}
                  value={provider.id}
                  disabled={!provider.available}
                  aria-describedby={provider.available ? undefined : reasonId}
                  className="mt-1"
                />
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <label htmlFor={radioId} className="font-medium">
                      {provider.name}
                    </label>
                    <ProviderBadge provider={provider} model={provider.models[0] ?? ""} />
                  </div>

                  <p
                    id={reasonId}
                    className={
                      provider.available ? "font-normal text-muted-foreground" : "font-normal"
                    }
                  >
                    {provider.available
                      ? "Available on this machine."
                      : provider.unavailableReason}
                  </p>

                  <div className="w-[260px] max-w-full">
                    <Select
                      value={active ? selectedModel : (provider.models[0] ?? "")}
                      disabled={!provider.available || !active}
                      onValueChange={(value) => onModelChange(kind, value)}
                    >
                      <SelectTrigger aria-label={`${provider.name} model`}>
                        <SelectValue placeholder="Model" />
                      </SelectTrigger>
                      <SelectContent>
                        {provider.models.map((model) => (
                          <SelectItem key={model} value={model} className="font-mono">
                            {model}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </RadioGroup>
    </section>
  );
}
