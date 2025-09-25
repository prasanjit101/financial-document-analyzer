const STORAGE_KEY = "documents.jobMap";

type JobMap = Record<string, string>;

function readMap(): JobMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      return Object.fromEntries(Object.entries(parsed).filter(([key, value]) => typeof key === "string" && typeof value === "string")) as JobMap;
    }
    return {};
  } catch {
    return {};
  }
}

function writeMap(map: JobMap): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    /* ignore */
  }
}

export function getDocumentJobMap(): JobMap {
  return readMap();
}

export function getJobIdForDocument(documentId: string): string | null {
  const map = readMap();
  return map[documentId] ?? null;
}

export function setJobIdForDocument(documentId: string, jobId: string): void {
  if (!documentId || !jobId) return;
  const map = readMap();
  map[documentId] = jobId;
  writeMap(map);
}

export function removeJobIdForDocument(documentId: string): void {
  if (!documentId) return;
  const map = readMap();
  if (map[documentId]) {
    delete map[documentId];
    writeMap(map);
  }
}
