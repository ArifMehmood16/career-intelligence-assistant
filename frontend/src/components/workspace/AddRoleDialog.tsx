import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export interface AddRoleDialogProps {
  open: boolean;
  disabled: boolean;
  submitting: boolean;
  errorMessage?: string | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (input: {
    title: string;
    company: string;
    description: string;
  }) => void;
}

export function AddRoleDialog({
  open,
  disabled,
  submitting,
  errorMessage = null,
  onOpenChange,
  onSubmit,
}: AddRoleDialogProps) {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileDescription, setFileDescription] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const displayedError = errorMessage ?? fileError;
  let uploadLabel = submitting ? "Adding…" : "Add role";
  if (reading) uploadLabel = "Reading file…";

  useEffect(() => {
    setFileDescription("");
    setFileError(null);
    setReading(false);
    if (!file) return;
    if (
      !file.name.toLowerCase().endsWith(".txt") ||
      file.size > 10 * 1024 * 1024
    ) {
      setFileError(
        "Choose a plain-text .txt file up to 10 MB, or paste the description.",
      );
      return;
    }
    const reader = new FileReader();
    setReading(true);
    reader.onload = () => {
      setReading(false);
      const text =
        typeof reader.result === "string" ? reader.result.trim() : "";
      if (!text || text.includes("\u0000")) {
        setFileError("The file must contain plain job-description text.");
        return;
      }
      setFileDescription(text);
    };
    reader.onerror = () => {
      setReading(false);
      setFileError(
        "Could not read that file. Choose it again or paste the description.",
      );
    };
    reader.readAsText(file);
    return () => {
      reader.onload = null;
      reader.onerror = null;
      if (reader.readyState === FileReader.LOADING) reader.abort();
    };
  }, [file]);

  useEffect(() => {
    if (open) return;
    setTitle("");
    setCompany("");
    setDescription("");
    setFile(null);
  }, [open]);

  const submit = (source: "file" | "text") => {
    const text = source === "file" ? fileDescription : description.trim();
    if (submitting || !title.trim() || !company.trim() || !text) return;
    onSubmit({
      title: title.trim(),
      company: company.trim(),
      description: text,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button type="button" size="sm" disabled={disabled}>
          Add role
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add role</DialogTitle>
          <DialogDescription>
            Upload a plain-text job description (.txt) or paste the text.
          </DialogDescription>
        </DialogHeader>

        {displayedError ? (
          <p className="text-sm text-muted-foreground" role="alert">
            {displayedError}
          </p>
        ) : null}

        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="role-title">Role title</Label>
            <Input
              id="role-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Senior Data Analyst"
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="role-company">Company</Label>
            <Input
              id="role-company"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              placeholder="Northwind Analytics"
            />
          </div>
        </div>

        <Tabs defaultValue="upload">
          <TabsList>
            <TabsTrigger value="upload">Upload file</TabsTrigger>
            <TabsTrigger value="paste">Paste text</TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="mt-3 space-y-3">
            <div className="grid gap-1.5">
              <Label htmlFor="role-file">Job description file</Label>
              <Input
                id="role-file"
                type="file"
                accept=".txt,text/plain"
                disabled={submitting}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </div>
            {file ? (
              <p className="font-mono text-sm text-muted-foreground">
                {file.name}
              </p>
            ) : null}
            <DialogFooter>
              <Button
                type="button"
                onClick={() => submit("file")}
                disabled={
                  submitting ||
                  reading ||
                  !title.trim() ||
                  !company.trim() ||
                  !fileDescription
                }
              >
                {uploadLabel}
              </Button>
            </DialogFooter>
          </TabsContent>

          <TabsContent value="paste" className="mt-3 space-y-3">
            <div className="grid gap-1.5">
              <Label htmlFor="role-text">Job description</Label>
              <Textarea
                id="role-text"
                rows={8}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Paste the job description here"
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                onClick={() => submit("text")}
                disabled={
                  submitting ||
                  !title.trim() ||
                  !company.trim() ||
                  !description.trim()
                }
              >
                {submitting ? "Adding…" : "Add role"}
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
