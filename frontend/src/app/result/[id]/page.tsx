"use client";
import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import { getSession, fileUrl, type Session, type Question, type Mapping, type Grading } from "@/lib/api";

function ScorePill({ score, max }: { score: number; max: number }) {
  const pct = max ? score / max : 0;
  let bg = "bg-green-100 text-green-700";
  if (pct === 0) bg = "bg-red-100 text-red-600";
  else if (pct < 0.6) bg = "bg-orange-100 text-orange-600";
  return <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${bg}`}>{score}/{max}</span>;
}

export default function ResultPage() {
  const params = useParams() as { id: string };
  const id = params.id;
  const [collapsed, setCollapsed] = useState(true);
  const [session, setSession] = useState<Session | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["q_2"]));
  const viewerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;
    let alive = true;
    async function poll() {
      try {
        const s = await getSession(id);
        if (!alive) return;
        setSession(s);
        if (!selected && s.questions.length) setSelected(s.questions[1]?.id || s.questions[0]?.id);
        if (s.status !== "done" && s.status !== "error") {
          setTimeout(poll, 1500);
        }
      } catch {}
    }
    poll();
    return () => { alive = false; };
  }, [id, selected]);

  // when selected changes, jump to its answer page
  useEffect(() => {
    if (!session || !selected) return;
    const m = session.mappings.find(x => x.questionId === selected);
    if (m && m.answerIds.length) {
      const ans = session.answers.find(a => a.id === m.answerIds[0]);
      if (ans && ans.bboxes.length) {
        setCurrentPage(ans.bboxes[0].pageIndex);
        // scroll viewer
        viewerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
  }, [selected, session]);

  if (!session) {
    return <div className="min-h-screen flex items-center justify-center bg-[#F5F5F5]">Loading...</div>;
  }

  if (session.status !== "done") {
    return (
      <div className="min-h-screen flex bg-[#F5F5F5]">
        <Sidebar collapsed={true} onToggle={() => setCollapsed(!collapsed)} />
        <div className="flex-1 flex flex-col p-3 gap-3">
          <Header />
          <div className="flex-1 bg-white rounded-[24px] flex flex-col items-center justify-center p-10">
            {/* Exact Vector layout matching Loading state.png */}
            <div className="relative w-32 h-32 mb-6 flex items-center justify-center">
              {/* Top main large sparkle star */}
              <div className="absolute top-2 animate-pulse" style={{ transform: 'scale(1.1)' }}>
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M32 0C32 17.6731 17.6731 32 0 32C17.6731 32 32 46.3269 32 64C32 46.369 46.3269 32 64 32C46.3269 32 32 17.6731 32 0Z" fill="url(#paint0_linear_sparkle)"/>
                  <defs>
                    <linearGradient id="paint0_linear_sparkle" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#FF6B2C"/>
                      <stop offset="1" stopColor="#FF8A54"/>
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              {/* Bottom-left secondary sparkle star */}
              <div className="absolute bottom-2 left-2 animate-bounce" style={{ animationDuration: '3s' }}>
                <svg width="36" height="36" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M32 0C32 17.6731 17.6731 32 0 32C17.6731 32 32 46.3269 32 64C32 46.3269 46.3269 32 64 32C46.3269 32 32 17.6731 32 0Z" fill="url(#paint1_linear_sparkle)"/>
                  <defs>
                    <linearGradient id="paint1_linear_sparkle" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#FF6B2C"/>
                      <stop offset="1" stopColor="#FF8A54"/>
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              {/* Tiny right support sparkle star */}
              <div className="absolute bottom-8 right-2 animate-pulse" style={{ animationDuration: '1.8s', transform: 'scale(0.5)' }}>
                <svg width="32" height="32" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M32 0C32 17.6731 17.6731 32 0 32C17.6731 32 32 46.3269 32 64C32 46.3269 46.3269 32 64 32C46.3269 32 32 17.6731 32 0Z" fill="#FF8A54"/>
                </svg>
              </div>
              {/* Left small circular accent */}
              <div className="absolute left-1 top-10 w-2.5 h-2.5 bg-[#FF6B2C] rounded-full animate-ping" style={{ animationDuration: '2.5s' }} />
            </div>
            <div className="font-bold text-[32px] text-gray-900 tracking-tight mt-4">Extracting...</div>
            <div className="text-gray-500 font-medium text-base mt-2">This may take a while</div>
            {session.error && <div className="mt-4 text-red-500 text-sm">{session.error}</div>}
          </div>
        </div>
      </div>
    );
  }

  const questions = session.questions;
  const gradingMap = new Map(session.grading.map(g => [g.questionId, g]));
  const mappingMap = new Map(session.mappings.map(m => [m.questionId, m]));
  const selectedMapping = selected ? mappingMap.get(selected) : null;
  const selectedAnswers = selectedMapping ? session.answers.filter(a => selectedMapping.answerIds.includes(a.id)) : [];
  const allBboxes = selectedAnswers.flatMap(a => a.bboxes).filter(b => b.pageIndex === currentPage);
  const totalPages = session.files.answerSheet.pages || 4;

  return (
    <div className="min-h-screen flex bg-[#F5F5F5]">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col p-3 gap-3 min-w-0">
        <Header />
        <div className="flex-1 flex flex-col lg:flex-row gap-3 min-h-0">
          {/* Left */}
          <div className="flex-1 lg:w-[48%] bg-[#F0F0F0] rounded-2xl p-4 overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-sm">Extracted Questions <span className="font-normal text-gray-500">(from question paper)</span></h2>
              <button
                onClick={() => {
                  if (expanded.size === questions.length) setExpanded(new Set());
                  else setExpanded(new Set(questions.map(q => q.id)));
                }}
                className="text-xs bg-white rounded-full px-4 py-1.5 border"
              >
                {expanded.size === questions.length ? "Collapse All" : "Expand All"}
              </button>
            </div>

            <div className="flex flex-col gap-3">
              {questions.map(q => {
                const isSelected = selected === q.id;
                const isExpanded = expanded.has(q.id);
                const g = gradingMap.get(q.id);
                const m = mappingMap.get(q.id);
                const status = m?.status;
                return (
                  <div
                    key={q.id}
                    onClick={() => setSelected(q.id)}
                    className={`bg-white rounded-2xl p-4 cursor-pointer border-2 transition ${isSelected ? "border-[#FF6B2C]" : "border-transparent"}`}
                  >
                    <div className="flex gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${isSelected ? "bg-[#FF6B2C] text-white" : "bg-[#2D2D2D] text-white"}`}>
                        {q.subLabel ? `${q.label}` : q.label}
                        {q.subLabel && <span className="ml-0.5 text-[10px]">{q.subLabel}.</span>}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[13px] leading-5 pr-2">
                          {q.subLabel ? <span className="inline-flex items-center justify-center w-5 h-5 bg-gray-100 rounded mr-2 text-[11px]">{q.subLabel}.</span> : null}
                          {q.text}
                        </div>
                        {status === "unanswered" && <div className="text-xs text-red-500 mt-2">Unanswered</div>}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {g && <ScorePill score={g.score} max={g.maxScore} />}
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            setExpanded(prev => {
                              const n = new Set(prev);
                              if (n.has(q.id)) n.delete(q.id); else n.add(q.id);
                              return n;
                            });
                          }}
                          className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs"
                        >
                          {isExpanded ? "▲" : "▼"}
                        </button>
                      </div>
                    </div>
                    {isExpanded && g && (
                      <div className="mt-3 bg-[#F7F7F7] rounded-xl p-3">
                        <div className="font-bold text-xs">AI Feedback</div>
                        <div className="text-xs text-gray-600 mt-1 leading-5">{g.feedback}</div>
                        {status === "answered" && selectedAnswers.length > 0 && (
                          <div className="text-xs text-gray-400 mt-2">Mapped to {selectedAnswers[0]?.detectedLabel || "answer"} • confidence {m?.confidence}</div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {session.summary && (
              <div className="mt-4 bg-white rounded-2xl p-4">
                <div className="font-bold text-sm">Summary</div>
                <div className="text-xs text-gray-600 mt-1">{session.summary.overallFeedback}</div>
                <div className="text-xs mt-2 font-medium">{session.summary.totalScore}/{session.summary.maxTotal} • {session.summary.answered} answered • {session.summary.unanswered} unanswered • {session.summary.orphan} unmatched</div>
              </div>
            )}
          </div>

          {/* Right */}
          <div className="flex-1 lg:w-[52%] bg-white rounded-2xl flex flex-col overflow-hidden">
            <div className="h-12 bg-[#2D2D2D] flex items-center justify-between px-4 text-white">
              <span className="text-sm font-medium">Answer Sheet</span>
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-2 bg-[#3A3A3A] rounded-full px-2 py-1">
                  <button onClick={() => setZoom(z => Math.max(50, z - 10))} className="w-6 h-6 flex items-center justify-center text-sm">-</button>
                  <span className="text-xs min-w-[40px] text-center">{zoom}%</span>
                  <button onClick={() => setZoom(z => Math.min(150, z + 10))} className="w-6 h-6 flex items-center justify-center text-sm">+</button>
                </div>
                <div className="flex items-center gap-1 bg-[#3A3A3A] rounded-full px-3 py-1.5 text-xs">
                  <button onClick={() => setCurrentPage(p => Math.max(0, p - 1))} className="px-1">◀</button>
                  <span>Page {currentPage + 1} of {totalPages}</span>
                  <button onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))} className="px-1">▶</button>
                </div>
              </div>
            </div>

            <div ref={viewerRef} className="flex-1 overflow-auto bg-[#FDFBF7] p-4 flex flex-col gap-4">
              <div className="relative bg-white shadow-sm rounded-lg overflow-hidden mx-auto w-full max-w-[640px]" style={{ transform: `scale(${zoom / 100})`, transformOrigin: "top center" }}>
                <img
                  src={fileUrl(id, "answer", currentPage)}
                  alt="answer sheet"
                  className="w-full h-auto"
                  draggable={false}
                />
                {/* BBoxes */}
                {allBboxes.map((b, idx) => (
                  <div
                    key={idx}
                    className="absolute border-2 border-green-500 bg-green-400/10 rounded-lg pointer-events-none"
                    style={{
                      left: `${b.x * 100}%`,
                      top: `${b.y * 100}%`,
                      width: `${b.w * 100}%`,
                      height: `${b.h * 100}%`,
                    }}
                  >
                    <span className="absolute -top-6 left-0 bg-green-500 text-white text-[10px] font-bold px-2 py-0.5 rounded">Q{questions.find(q => q.id === selected)?.displayNumber.replace(".", "") || "2"}</span>
                  </div>
                ))}
              </div>

              {/* Show thumbnails */}
              <div className="flex gap-2 justify-center pb-4">
                {Array.from({ length: totalPages }).map((_, i) => (
                  <button key={i} onClick={() => setCurrentPage(i)} className={`w-12 h-16 rounded border-2 overflow-hidden ${currentPage === i ? "border-[#FF6B2C]" : "border-transparent"}`}>
                    <img src={fileUrl(id, "answer", i)} alt={`page ${i}`} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
