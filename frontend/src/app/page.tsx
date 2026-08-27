"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import UploadCard from "@/components/UploadCard";
import { createSession } from "@/lib/api";

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + "KB";
  return (bytes / (1024 * 1024)).toFixed(1) + "MB";
}

export default function UploadPage() {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [qFile, setQFile] = useState<File | null>(null);
  const [aFile, setAFile] = useState<File | null>(null);
  const [qInfo, setQInfo] = useState<{ name: string; size: string; pages: string } | null>(null);
  const [aInfo, setAInfo] = useState<{ name: string; size: string; pages: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleQ = (f: File) => {
    if (f.size > 10 * 1024 * 1024) { setError("File too large: Max 10MB"); return; }
    setQFile(f);
    setQInfo({ name: f.name, size: formatSize(f.size), pages: "• 2 Pages" });
    setError(null);
  };
  const handleA = (f: File) => {
    if (f.size > 10 * 1024 * 1024) { setError("File too large: Max 10MB"); return; }
    setAFile(f);
    setAInfo({ name: f.name, size: formatSize(f.size), pages: "• 6 Pages" });
    setError(null);
  };

  const canStart = !!qFile && !!aFile && !loading;

  async function onStart() {
    if (!canStart) return;
    setLoading(true);
    setError(null);
    try {
      const res = await createSession(qFile!, aFile!);
      router.push(`/result/${res.id}`);
    } catch (e: any) {
      setError(e.message || "Upload failed");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-[#F5F5F5]">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex-1 flex flex-col p-3 gap-3 min-w-0 lg:ml-0">
        <Header />
        <main className="flex-1 bg-[#F8F8F8] rounded-[24px] p-6 lg:p-10 overflow-auto">
          <div className="max-w-[1100px] mx-auto">
            <h1 className="text-center text-[28px] lg:text-[32px] font-bold">
              Upload <span className="bg-[#FFEDE0] text-[#FF6B2C] px-3 py-1 rounded-lg underline decoration-[#FF6B2C]/30">Question Paper & Answer Sheets</span>
            </h1>
            <p className="text-center text-gray-600 mt-3">Upload both files to get started</p>

            <div className="flex justify-center mt-8">
              <div className="relative w-36 h-36">
                <div className="absolute inset-0 bg-[#FFEDE0] rounded-full" />
                <div className="absolute inset-2 bg-[#FFD8C2] rounded-full" />
                <div className="absolute inset-4 bg-[#FFB89A] rounded-full flex items-center justify-center overflow-hidden">
                  <svg className="w-[50%] h-[50%] text-[#FF6B2C]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-7.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 19.5A2.5 2.5 0 016.5 17H20" />
                  </svg>
                </div>
                <div className="absolute -right-1 top-2 w-6 h-6 bg-white rounded-full shadow flex items-center justify-center text-[10px]">🎯</div>
                <div className="absolute -left-1 top-10 w-6 h-6 bg-white rounded-full shadow flex items-center justify-center text-[10px]">📄</div>
              </div>
            </div>

            <div className="mt-8 bg-white rounded-[24px] p-3 flex flex-col lg:flex-row gap-3 border border-gray-100">
              <UploadCard title="Question" file={qInfo} onFile={handleQ} onRemove={() => { setQFile(null); setQInfo(null); }} id="q" />
              <UploadCard title="Answer" file={aInfo} onFile={handleA} onRemove={() => { setAFile(null); setAInfo(null); }} id="a" />
            </div>

            {error && <div className="mt-4 text-center text-sm text-red-500 bg-red-50 rounded-xl py-3">{error}</div>}

            <div className="flex justify-center mt-8">
              <button
                onClick={onStart}
                disabled={!canStart}
                className={`rounded-full px-8 py-3 flex items-center gap-2 text-sm font-medium transition ${canStart ? "bg-black text-white hover:bg-gray-900" : "bg-[#D1D1D1] text-white cursor-not-allowed"}`}
              >
                {loading ? "Uploading…" : "Start Mapping"} <span>→</span>
              </button>
            </div>
            <p className="text-center text-xs text-gray-400 mt-4">Once both files are uploaded, you will able to map answers with questions</p>
          </div>
        </main>
      </div>
    </div>
  );
}
