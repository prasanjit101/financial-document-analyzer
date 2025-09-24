import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { useAuthStore } from "../lib/authStore";
import { apiAnalyzeDocument } from "@/lib/api";
import { type AnalyzeResponse } from "@/lib/types";
import { toast } from "sonner";
import { Analysis } from "./Analysis";

type AnalysisView = {
  jobId: string;
  documentId: string;
  query: string;
};

export function Home() {
  const { user, token, logout } = useAuthStore();
  const navigate = useNavigate();

  const [file, setFile] = useState<File | null>(null);
  const [query, setQuery] = useState<string>("Analyze this financial document for investment insights");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [analysis, setAnalysis] = useState<AnalysisView | null>(null);
  // No local polling state in Home; delegated to Analysis component

  const canUpload = useMemo(() => !!file && !isUploading, [file, isUploading]);

  async function handleUpload() {
    if (!file || !token) return;
    setIsUploading(true);
    try {
      if (file.type && file.type !== "application/pdf") {
        toast.error("Only PDF files are allowed");
        setIsUploading(false);
        return;
      }
      const res: AnalyzeResponse = await apiAnalyzeDocument({ file, query, token });
      setAnalysis({ jobId: res.jobId, documentId: res.documentId, query: res.query });
      toast.success("File uploaded. Analysis started.");
      navigate(`/analysis/${res.jobId}`);
    } catch (e: any) {
      toast.error(e?.message || "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  function resetAnalysis() {
    setAnalysis(null);
  }

  return (
    <div className="flex flex-col max-w-xl mx-auto space-y-8">
      <Card>
        <CardHeader>
          <CardTitle>Welcome{user?.full_name ? `, ${user.full_name}` : ""}</CardTitle>
        </CardHeader>
        <CardContent>
          {!analysis ? (
            <div style={{ display: "grid", gap: 12 }}>
              <Input
                type="file"
                accept="application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                disabled={isUploading}
              />
              <Input
                placeholder="Enter a question or prompt (optional)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isUploading}
              />
              <div style={{ display: "flex", gap: 8 }}>
                <Button onClick={handleUpload} disabled={!canUpload}>
                  {isUploading ? "Uploading..." : "Upload & Analyze"}
                </Button>
                <Button variant="secondary" onClick={logout}>Logout</Button>
              </div>
            </div>
          ) : (
            <Analysis
              jobId={analysis.jobId}
              documentId={analysis.documentId}
              query={analysis.query}
              onBack={resetAnalysis}
            />
          )}
        </CardContent>
      </Card>
      {/* TODO: Past analyses as list items */}
    </div>
  );
}


