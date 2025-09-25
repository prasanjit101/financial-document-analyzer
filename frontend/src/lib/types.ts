
export type RegisterPayload = {
    username: string;
    password: string;
    full_name?: string | null;
};

export type LoginPayload = {
    username: string;
    password: string;
};

export type AuthTokenResponse = {
    access_token: string;
    token_type: string;
};

export type UserMe = {
    username: string;
    full_name?: string | null;
    role: string;
};

// ---- Documents API types ----
export type AnalyzeResponse = {
    status: string; // e.g., "queued"
    query: string;
    file_processed: string;
    documentId: string;
    jobId: string;
};

export type JobMeta = {
    id?: string;
    status: "queued" | "running" | "completed" | "failed" | string;
    progress?: number;
    user_id?: string;
    document_id?: string;
    result?: unknown;
    error?: string;
    analysis_id?: string;
};

export type DocumentItem = {
    _id: string;
    filename: string;
    path: string;
    size: number;
    mime?: string | null;
    uploadedBy: string;
    createdAt: string;
    latestJobId?: string | null;
};

export type DocumentsList = {
    items: DocumentItem[];
};

// ---- Analyses API types ----
export type Analysis = {
    _id: string;
    documentId: string;
    userId: string;
    query: string;
    summary: string; // markdown content produced by the LLM flow
    createdAt?: string;
};
