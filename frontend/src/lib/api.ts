const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type SessionStatus = "uploading" | "extracting_questions" | "extracting_answers" | "mapping" | "grading" | "done" | "error";

export interface BBox { pageIndex: number; x: number; y: number; w: number; h: number; }
export interface Question {
  id: string; label: string; subLabel: string | null; displayNumber: string;
  text: string; order: number; maxScore: number | null; type?: string;
}
export interface AnswerRegion {
  id: string; detectedLabel: string | null; textPreview: string; bboxes: BBox[]; pages: number[];
}
export interface Mapping { questionId: string; answerIds: string[]; status: "answered"|"unanswered"|"orphan"; confidence: number; }
export interface Grading { questionId: string; score: number; maxScore: number; feedback: string; isCorrect: boolean | null; isUnanswered: boolean; }
export interface Summary { totalScore: number; maxTotal: number; answered: number; unanswered: number; orphan: number; overallFeedback: string; }
export interface Session {
  id: string; status: SessionStatus; progress: number; createdAt: string; updatedAt: string;
  files: {
    questionPaper: { name: string; pages: number; size: number; mime: string; imagesUrl: string[] };
    answerSheet: { name: string; pages: number; size: number; mime: string; imagesUrl: string[] };
  };
  questions: Question[]; answers: AnswerRegion[]; mappings: Mapping[]; grading: Grading[]; summary: Summary | null; error?: string; orphans?: any[];
}

export async function createSession(qFile: File, aFile: File): Promise<{id: string; status: string}> {
  const fd = new FormData();
  fd.append("questionPaper", qFile);
  fd.append("answerSheet", aFile);
  const res = await fetch(`${API_BASE}/api/v1/sessions`, { method: "POST", body: fd });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Upload failed ${res.status}`);
  }
  return res.json();
}

export async function getSession(id: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/api/v1/sessions/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Session not found");
  return res.json();
}

export function fileUrl(sessionId: string, type: "question"|"answer", pageIdx: number) {
  return `${API_BASE}/api/v1/sessions/${sessionId}/file/${type}/${pageIdx}`;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/api/v1/health`, { cache: "no-store" });
    return r.ok;
  } catch { return false; }
}
