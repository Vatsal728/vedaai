"use client";
import { useRef } from "react";

export default function UploadCard({
  title,
  file,
  onFile,
  onRemove,
  id,
}: {
  title: string;
  file: { name: string; size: string; pages: string } | null;
  onFile: (f: File) => void;
  onRemove: () => void;
  id: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const orange = title.includes("Question") ? "Question Paper" : "Answer Sheet";

  return (
    <div
      onClick={() => !file && inputRef.current?.click()}
      onDragOver={e => e.preventDefault()}
      onDrop={e => {
        e.preventDefault();
        const f = e.dataTransfer.files?.[0];
        if (f) onFile(f);
      }}
      className={`relative flex-1 min-h-[200px] bg-white rounded-[24px] border-2 border-dashed flex flex-col items-center justify-center p-6 cursor-pointer transition hover:border-orange-300 ${file ? "border-gray-200 border-solid" : "border-gray-300"}`}
    >
      <input
        ref={inputRef}
        type="file"
        id={id}
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        className="hidden"
        onChange={e => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
        }}
      />

      {!file ? (
        <>
          <div className="w-14 h-14 bg-[#F0F0F0] rounded-2xl flex items-center justify-center text-xl mb-4">⬆</div>
          <div className="font-semibold text-[15px]">
            Upload <span className="text-[#FF6B2C]">{orange}</span>
          </div>
          <div className="text-xs text-gray-400 mt-1">Max 10MB</div>
        </>
      ) : (
        <div className="relative bg-[#F7F7F7] rounded-2xl px-4 py-4 flex items-center gap-3 w-[85%] max-w-[320px]">
          <div className="w-10 h-10 bg-[#E53935] rounded-lg flex items-center justify-center text-white text-[10px] font-bold">PDF</div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold truncate">{file.name}</div>
            <div className="text-xs text-gray-500">{file.size} • {file.pages}</div>
          </div>
          <button
            onClick={e => {
              e.stopPropagation();
              onRemove();
              if (inputRef.current) inputRef.current.value = "";
            }}
            className="absolute -top-2 -right-2 w-7 h-7 bg-[#2D2D2D] text-white rounded-full flex items-center justify-center text-xs"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
