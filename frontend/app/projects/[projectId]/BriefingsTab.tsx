"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, FileText, Upload, Pencil, Trash2 } from "lucide-react";
import { getBriefings, uploadBriefing, updateBriefing, deleteBriefing } from "@/lib/api";
import { Briefing } from "@/types";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import Input from "@/components/ui/Input";
import Textarea from "@/components/ui/Textarea";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

interface Props { projectId: string }

export default function BriefingsTab({ projectId }: Props) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [editing, setEditing] = useState<Briefing | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [previewing, setPreviewing] = useState<Briefing | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [blobLoading, setBlobLoading] = useState(false);

  useEffect(() => {
    if (!previewing || previewing.file_type === "text") {
      setBlobUrl(null);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setBlobLoading(true);
    setBlobUrl(null);
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    fetch(`${base}/projects/${projectId}/briefings/${previewing.id}/file`, { credentials: "include" })
      .then(r => r.blob())
      .then(blob => {
        if (!cancelled) {
          objectUrl = URL.createObjectURL(blob);
          setBlobUrl(objectUrl);
          setBlobLoading(false);
        }
      })
      .catch(() => { if (!cancelled) setBlobLoading(false); });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [previewing?.id]);

  const { data: briefings, isLoading } = useQuery({
    queryKey: ["briefings", projectId],
    queryFn: () => getBriefings(projectId),
  });

  const upload = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append("title", title);
      if (description) fd.append("description", description);
      fd.append("file", file!);
      return uploadBriefing(projectId, fd);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["briefings", projectId] });
      setOpen(false);
      setTitle("");
      setDescription("");
      setFile(null);
    },
  });

  const rename = useMutation({
    mutationFn: () => updateBriefing(projectId, editing!.id, { title: editTitle, description: editDescription || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["briefings", projectId] });
      setEditing(null);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteBriefing(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["briefings", projectId] });
      setDeletingId(null);
    },
  });

  const openEdit = (b: Briefing) => {
    setEditing(b);
    setEditTitle(b.title);
    setEditDescription(b.description ?? "");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const fileTypeVariant = (t: string) =>
    t === "pdf" ? "error" : t === "image" ? "info" : "default";

  return (
    <>
      <div className="flex justify-end mb-5">
        <Button onClick={() => setOpen(true)}><Plus size={14} /> Upload Briefing</Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[1, 2].map(i => <div key={i} className="h-20 bg-zinc-100 rounded-lg animate-pulse" />)}</div>
      ) : !briefings?.length ? (
        <EmptyState icon={FileText} title="No briefings yet" description="Upload a product brief, taglines, or any marketing document to test with personas." action={<Button onClick={() => setOpen(true)}><Upload size={14} /> Upload Briefing</Button>} />
      ) : (
        <div className="space-y-3">
          {briefings.map(b => (
            <Card key={b.id} onClick={() => setPreviewing(b)}>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-zinc-100 flex items-center justify-center shrink-0">
                  <FileText size={14} className="text-zinc-500" strokeWidth={1.5} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium text-zinc-900 truncate">{b.title}</h3>
                    <Badge variant={fileTypeVariant(b.file_type)}>{b.file_type.toUpperCase()}</Badge>
                  </div>
                  {b.description && <p className="text-xs text-zinc-400 mt-0.5">{b.description}</p>}
                  <p className="text-xs text-zinc-300 mt-1">{formatDate(b.created_at)}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button onClick={e => { e.stopPropagation(); openEdit(b); }} className="p-1.5 rounded hover:bg-zinc-100 text-zinc-400 hover:text-zinc-600 transition-colors">
                    <Pencil size={13} />
                  </button>
                  <button onClick={e => { e.stopPropagation(); setDeletingId(b.id); }} className="p-1.5 rounded hover:bg-red-50 text-zinc-400 hover:text-red-500 transition-colors">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={!!previewing} onClose={() => setPreviewing(null)} title={previewing?.title ?? ""} width="max-w-3xl">
        <div>
          {previewing?.file_type === "text" ? (
            <div className="max-h-[60vh] overflow-y-auto rounded-lg bg-zinc-50 border border-zinc-100 p-4">
              <pre className="text-xs text-zinc-700 whitespace-pre-wrap font-mono leading-relaxed">{previewing.extracted_text || "No text extracted."}</pre>
            </div>
          ) : previewing?.file_type === "image" ? (
            <div className="space-y-4">
              <div className="flex items-center justify-center min-h-[200px] bg-zinc-50 rounded-lg border border-zinc-100">
                {blobLoading ? (
                  <div className="text-xs text-zinc-400">Loading image…</div>
                ) : blobUrl ? (
                  <img src={blobUrl} alt={previewing.title} className="max-h-[50vh] max-w-full rounded object-contain" />
                ) : (
                  <div className="text-xs text-zinc-400">Could not load image.</div>
                )}
              </div>
              {previewing.extracted_text && (
                <div>
                  <p className="text-xs font-medium text-zinc-500 mb-2">AI Analysis</p>
                  <div className="max-h-[20vh] overflow-y-auto rounded-lg bg-zinc-50 border border-zinc-100 p-3">
                    <p className="text-xs text-zinc-700 leading-relaxed">{previewing.extracted_text}</p>
                  </div>
                </div>
              )}
            </div>
          ) : previewing?.file_type === "pdf" ? (
            <div className="min-h-[60vh] bg-zinc-50 rounded-lg border border-zinc-100 flex items-center justify-center">
              {blobLoading ? (
                <div className="text-xs text-zinc-400">Loading PDF…</div>
              ) : blobUrl ? (
                <iframe src={blobUrl} className="w-full h-[60vh] rounded-lg" title={previewing.title} />
              ) : (
                <div className="text-xs text-zinc-400">Could not load PDF.</div>
              )}
            </div>
          ) : null}
        </div>
      </Modal>

      <Modal open={!!editing} onClose={() => setEditing(null)} title="Edit Briefing">
        <div className="space-y-4">
          <Input label="Title" value={editTitle} onChange={e => setEditTitle(e.target.value)} />
          <Textarea label="Description (optional)" rows={2} value={editDescription} onChange={e => setEditDescription(e.target.value)} />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={() => rename.mutate()} disabled={!editTitle || rename.isPending}>
              {rename.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title="Delete Briefing">
        <div className="space-y-4">
          <p className="text-sm text-zinc-600">This will permanently delete the briefing. Any simulations that used it will keep their existing results.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setDeletingId(null)}>Cancel</Button>
            <Button variant="danger" onClick={() => remove.mutate(deletingId!)} disabled={remove.isPending}>
              {remove.isPending ? "Deleting…" : "Delete"}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={open} onClose={() => setOpen(false)} title="Upload Briefing">
        <div className="space-y-4">
          <Input label="Title" placeholder="e.g. Q2 Campaign Brief" value={title} onChange={e => setTitle(e.target.value)} />
          <Textarea label="Description (optional)" placeholder="What does this document contain?" rows={2} value={description} onChange={e => setDescription(e.target.value)} />

          {/* Drop zone */}
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">File</label>
            <div
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${dragging ? "border-zinc-400 bg-zinc-50" : "border-zinc-200 hover:border-zinc-300"}`}
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={20} className="mx-auto text-zinc-300 mb-2" strokeWidth={1.5} />
              {file ? (
                <p className="text-sm text-zinc-700 font-medium">{file.name}</p>
              ) : (
                <>
                  <p className="text-sm text-zinc-500">Drop a file here or <span className="text-zinc-800 font-medium">browse</span></p>
                  <p className="text-xs text-zinc-300 mt-1">PDF, images, or plain text</p>
                </>
              )}
              <input ref={fileRef} type="file" className="hidden" accept=".pdf,.txt,.png,.jpg,.jpeg,.webp" onChange={e => { if (e.target.files?.[0]) setFile(e.target.files[0]); }} />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => upload.mutate()} disabled={!title || !file || upload.isPending}>
              {upload.isPending ? "Uploading…" : "Upload"}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
