"use client";
import { useState } from "react";
import Link from "next/link";

const menu = [
  { label: "Home", icon: "⊞", active: false },
  { label: "My Classroom", icon: "◫", active: false },
  { label: "Assignments", icon: "📄", active: false },
  { label: "Exams", icon: "📋", active: true },
  { label: "My Library", icon: "◷", active: false },
];

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  if (collapsed) {
    return (
      <aside className="hidden lg:flex w-[64px] flex-col items-center bg-white rounded-[20px] shadow-sm py-4 gap-3 h-[calc(100vh-24px)] ml-3 my-3">
        <div className="w-10 h-10 bg-[#1F1F1F] rounded-xl flex items-center justify-center text-white font-bold text-lg">V</div>
        <div className="mt-4 w-10 h-10 bg-[#1F1F1F] rounded-full flex items-center justify-center text-white border-2 border-orange-400">✦</div>
        <div className="flex flex-col gap-4 mt-6">
          {menu.map(m => (
            <div key={m.label} className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm ${m.active ? "bg-gray-100" : "text-gray-400"}`}>{m.icon}</div>
          ))}
        </div>
        <div className="mt-auto w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center">»</div>
      </aside>
    );
  }
  return (
    <aside className="hidden lg:flex w-[280px] flex-col bg-white rounded-[20px] shadow-sm p-5 h-[calc(100vh-24px)] ml-3 my-3 shrink-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 bg-[#1F1F1F] rounded-xl flex items-center justify-center text-white font-bold text-lg">V</div>
          <span className="font-bold text-xl tracking-tight">VedaAI</span>
        </div>
        <button onClick={onToggle} className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:bg-gray-100">▢</button>
      </div>

        <button className="mt-6 w-full bg-[#1F1F1F] text-white rounded-full py-3 px-4 flex items-center justify-center gap-2 text-sm font-medium border-2 border-[#FF6B2C]">
        <span>✦</span> AI Teacher Toolkit
      </button>

      <nav className="mt-8 flex flex-col gap-1">
        {menu.map(m => (
          <Link href="/" key={m.label} className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm ${m.active ? "bg-[#F0F0F0] text-black font-medium" : "text-gray-500 hover:bg-gray-50"}`}>
            <span className="text-base w-5 text-center">{m.icon}</span> {m.label}
          </Link>
        ))}
      </nav>

      <div className="mt-auto pt-6 border-t border-transparent">
        <Link href="/" className="flex items-center gap-3 px-4 py-2 text-sm text-gray-500">
          <span className="text-base">⚙</span> Settings
        </Link>
        <div className="mt-4 bg-[#F0F0F0] rounded-2xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-green-700 border">🏫</div>
          <div>
            <div className="font-semibold text-sm">Delhi Public School</div>
            <div className="text-xs text-gray-500">Bokaro Steel City</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
