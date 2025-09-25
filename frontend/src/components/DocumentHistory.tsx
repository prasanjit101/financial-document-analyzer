import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Separator } from "./ui/separator";
import { Skeleton } from "./ui/skeleton";
import { toast } from "sonner";
import { apiDeleteDocument, apiListDocuments } from "@/lib/api";
import { type DocumentItem } from "@/lib/types";
import { useAuthStore } from "@/lib/authStore";
import { getJobIdForDocument, removeJobIdForDocument } from "@/lib/documentJobs";

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "-";
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const power = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** power;
  return `${value.toFixed(value < 10 && power > 0 ? 1 : 0)} ${units[power]}`;
}

type DocumentHistoryProps = {
  title?: string;
  refreshKey?: number;
  className?: string;
};

export function DocumentHistory({ title = "Previous uploads", refreshKey, className }: DocumentHistoryProps) {
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const hasDocuments = useMemo(() => documents.length > 0, [documents]);

  const loadDocuments = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await apiListDocuments({ token });
      setDocuments(res.items);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments, refreshKey]);

  const handleOpen = useCallback((doc: DocumentItem) => {
    const jobId = doc.latestJobId || getJobIdForDocument(doc._id);
    if (!jobId) {
      toast.error("No analysis job found for this document yet.");
      return;
    }
    navigate(`/analysis/${jobId}`);
  }, [navigate]);

  const handleDelete = useCallback(async (doc: DocumentItem) => {
    if (!token) return;
    const confirmed = window.confirm(`Delete ${doc.filename}? This action cannot be undone.`);
    if (!confirmed) return;
    setDeletingId(doc._id);
    try {
      await apiDeleteDocument(doc._id, token);
      setDocuments((prev) => prev.filter((d) => d._id !== doc._id));
      removeJobIdForDocument(doc._id);
      toast.success("Document deleted");
    } catch (e: any) {
      toast.error(e?.message || "Failed to delete document");
    } finally {
      setDeletingId(null);
    }
  }, [token]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading && !hasDocuments && (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/6" />
          </div>
        )}
        {error && (
          <div className="text-sm text-red-500">{error}</div>
        )}
        {!loading && !hasDocuments && !error && (
          <div className="text-sm text-muted-foreground">No previous uploads yet.</div>
        )}
        {hasDocuments && (
          <div className="space-y-3">
            {documents.map((doc, index) => {
              const jobId = doc.latestJobId || getJobIdForDocument(doc._id);
              return (
                <div key={doc._id} className="space-y-2">
                  <div className="flex flex-col gap-2 rounded-md border border-border p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-medium leading-snug">{doc.filename}</div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(doc.createdAt).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                      <div>{formatBytes(doc.size)}</div>
                      <div>{doc.mime || "application/pdf"}</div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleOpen(doc)} disabled={!jobId}>
                        Open
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleDelete(doc)}
                        disabled={deletingId === doc._id}
                      >
                        {deletingId === doc._id ? "Deleting..." : "Delete"}
                      </Button>
                    </div>
                    {!jobId && (
                      <div className="text-xs text-amber-600">No analysis job metadata available yet.</div>
                    )}
                  </div>
                  {index < documents.length - 1 ? <Separator /> : null}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
