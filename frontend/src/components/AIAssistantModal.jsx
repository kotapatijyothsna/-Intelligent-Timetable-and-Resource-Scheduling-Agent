import React, { useState } from 'react';

export default function AIAssistantModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hello! I am the AIML Smart Campus Scheduling Agent. I provide deterministic timetable intelligence and resource availability queries grounded directly in verified department data.',
      evidence: null
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const sampleQueries = [
    "Which AIML faculty are free at 11 AM today?",
    "Find an available classroom for 50 students at 10:10 AM",
    "Is Dr. Sudha Rani teaching any class at 2 PM?",
    "Are any computer labs free on Friday morning?"
  ];

  const sendQuery = async (queryText) => {
    const q = queryText || inputQuery;
    if (!q.trim()) return;

    const userMsg = { role: 'user', text: q };
    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await fetch('/api/v1/assistant/query/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q })
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            text: data.reply,
            tools: data.tools_invoked,
            evidence: data.evidence
          }
        ]);
      }
    } catch (e) {
      console.error(e);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: 'Error contacting AI assistant service. Please check connection.',
          evidence: null
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl flex flex-col h-[580px] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-700 to-indigo-700 p-4 text-white flex justify-between items-center">
          <div className="flex items-center space-x-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
            <div>
              <h3 className="font-bold text-sm tracking-wide">Intelligent Scheduling Agent</h3>
              <p className="text-3xs text-purple-200">Grounded in VFSTR AIML Verified Timetable</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white text-lg font-bold px-2 py-0.5 rounded-md hover:bg-white/10"
          >
            ✕
          </button>
        </div>

        {/* Message Container */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50/50">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-xl p-3 text-xs leading-relaxed shadow-2xs ${
                  m.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-none'
                    : 'bg-white text-slate-800 border border-slate-200 rounded-bl-none'
                }`}
              >
                <div className="whitespace-pre-line">{m.text}</div>

                {/* Evidence attribution card */}
                {m.tools && m.tools.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-100 text-3xs text-slate-500 font-mono">
                    <span className="font-bold text-indigo-600">Tool Executed:</span> {m.tools[0].tool_name}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-center space-x-2 text-xs text-slate-400 italic p-2">
              <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce"></span>
              <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:0.4s]"></span>
              <span>Evaluating schedule intervals...</span>
            </div>
          )}
        </div>

        {/* Sample queries pills */}
        <div className="px-4 py-2 bg-white border-t border-slate-100 flex items-center space-x-1.5 overflow-x-auto">
          {sampleQueries.map((sq, i) => (
            <button
              key={i}
              onClick={() => sendQuery(sq)}
              className="text-3xs whitespace-nowrap bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-600 px-2.5 py-1 rounded-full transition"
            >
              {sq}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 bg-white border-t border-slate-200 flex items-center space-x-2">
          <input
            type="text"
            placeholder="Ask about faculty availability, classrooms, or labs..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendQuery()}
            className="flex-1 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={() => sendQuery()}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-bold transition disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
