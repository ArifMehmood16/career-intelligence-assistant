import { useState } from "react";
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
  onOpenChange,
  onSubmit,
}: AddRoleDialogProps) {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [filename, setFilename] = useState("");

  const reset = () => {
    setTitle("");
    setCompany("");
    setDescription("");
    setFilename("");
  };

  const submit = (source: "file" | "text") => {
    if (!title.trim() || !company.trim()) return;
    onSubmit({
      title: title.trim(),
      company: company.trim(),
      description: source === "file" ? filename : description.trim(),
    });
    reset();
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogTrigger asChild>
        <Button type="button" size="sm" disabled={disabled}>
          Add role
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add role</DialogTitle>
          <DialogDescription>
            Upload a job description file or paste the text.
          </DialogDescription>
        </DialogHeader>

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
                accept=".pdf,.docx,.txt"
                onChange={(event) =>
                  setFilename(event.target.files?.[0]?.name ?? "")
                }
              />
            </div>
            {filename ? (
              <p className="font-mono text-sm text-muted-foreground">
                {filename}
              </p>
            ) : null}
            <DialogFooter>
              <Button
                type="button"
                onClick={() => submit("file")}
                disabled={
                  submitting || !title.trim() || !company.trim() || !filename
                }
              >
                {submitting ? "Adding…" : "Add role"}
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
