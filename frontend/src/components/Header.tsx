"use client";
export default function Header() {
  return (
    <header className="h-[56px] bg-white rounded-2xl flex items-center justify-between px-5 shadow-sm">
      <div className="flex items-center gap-3">
        <button className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-gray-100">←</button>
        <span className="flex items-center gap-2 text-sm text-gray-500"><span className="w-5 h-5 flex items-center justify-center">📋</span> Exams</span>
      </div>
      <div className="flex items-center gap-3">
        <button className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm">?</button>
        <button className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center relative">
          <span>🔔</span>
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-orange-500 rounded-full" />
        </button>
        <button className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">✦</button>
        <div className="flex items-center gap-2 ml-2">
          <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-600">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <span className="text-sm font-medium hidden sm:inline">Teacher</span>
          <span className="text-gray-400">⌄</span>
        </div>
      </div>
    </header>
  );
}
