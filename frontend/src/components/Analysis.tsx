import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { apiGetJob, apiGetAnalysis } from "@/lib/api";
import { type JobMeta, type Analysis as AnalysisType } from "@/lib/types";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { Streamdown } from 'streamdown';

type AnalysisProps = Partial<{
  jobId: string;
  documentId: string;
  query: string;
  onBack: () => void;
}>;

export function Analysis(props: AnalysisProps = {}) {
  const { token } = useAuthStore();
  const navigate = useNavigate();
  const params = useParams();
  const jobIdFromRoute = params.jobId;
  const jobId = useMemo(() => props.jobId || jobIdFromRoute || "", [props.jobId, jobIdFromRoute]);
  const [progress, setProgress] = useState<number>(0);
  const [jobStatus, setJobStatus] = useState<JobMeta["status"] | null>(null);
  const [analysisId, setAnalysisId] = useState<string>("");
  const [analysis, setAnalysis] = useState<AnalysisType | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);

  useEffect(() => {
    if (!jobId || !token) return;
    const currentJobId = jobId;
    const authToken = token;
    let cancelled = false;

    async function poll() {
      try {
        const meta = await apiGetJob(currentJobId, authToken);
        if (cancelled) return;
        setJobStatus(meta.status);
        const raw = meta.progress ?? 0;
        const pct = raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
        setProgress(Math.max(0, Math.min(100, pct)));
        if (meta.status === "completed") {
          // analysis id expected in job meta as analysis_id
          const aId = meta.analysis_id;
          if (aId) setAnalysisId(aId);
          return;
        }
        if (meta.status === "failed") return;
        setTimeout(poll, 1500);
      } catch (e: any) {
        if (!cancelled) toast.error(e?.message || "Failed to fetch job status");
      }
    }

    poll();
    return () => { cancelled = true; };
  }, [jobId, token]);

  // Fetch analysis when we obtain an analysisId
  useEffect(() => {
    if (!analysisId || !token) return;
    const id = analysisId;
    let cancelled = false;
    async function load() {
      setLoadingAnalysis(true);
      try {
        const a = await apiGetAnalysis(id, token!);
        if (!cancelled) setAnalysis(a);
      } catch (e: any) {
        if (!cancelled) toast.error(e?.message || "Failed to load analysis");
      } finally {
        if (!cancelled) setLoadingAnalysis(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [analysisId, token]);

  const showResult = jobStatus === "completed" && analysis;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{showResult ? "Analysis Result" : "Analyzing document"}</CardTitle>
      </CardHeader>
      <CardContent>
        {!showResult && (
          <>
            <div>Processing your file. This may take a moment.</div>
            <Progress value={progress} />
            <div>Status: {jobStatus || "unknown"} {progress ? `(${progress}%)` : null}</div>
            {jobStatus === "failed" && <div className="text-red-500">Job failed. Please try again.</div>}
          </>
        )}
        {showResult && !analysis && (
          <div>Finalizing analysis...</div>
        )}
        {showResult && analysis && (
          <Streamdown>
            {analysis.summary}
          </Streamdown>
        )}
        {loadingAnalysis && <div>Loading analysis...</div>}
        <Button onClick={() => (props.onBack ? props.onBack() : navigate(-1))} variant="secondary" style={{ marginTop: '1rem' }}>Back</Button>
      </CardContent>
    </Card>
  );
}


