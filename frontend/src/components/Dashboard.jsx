import React, { useState, useEffect } from 'react';

export default function Dashboard({ setActiveTab, openChat, stats }) {
  const [liveData, setLiveData] = useState(null);
  const [liveLoading, setLiveLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/availability/live-dashboard/')
      .then(res => res.json())
      .then(data => {
        setLiveData(data);
        setLiveLoading(false);
      })
      .catch(() => setLiveLoading(false));
  }, []);

  const cards = [
    {
      title: 'Academic Cohorts',
      value: '44 Sections',
      subtitle: 'AIML (24), CS (4), DS (5), CSBS (2), IOT (2), BS/MSC/MTech (7)',
      color: 'border-blue-500',
      action: () => setActiveTab('timetable')
    },
    {
      title: 'Teaching Faculty',
      value: '217 Members',
      subtitle: 'Deduplicated Faculty, TAs & Staff across all branches',
      color: 'border-emerald-500',
      action: () => setActiveTab('faculty')
    },
    {
      title: 'Academic Resources',
      value: '46 Facilities',
      subtitle: '23 Classrooms & 23 Computing Labs',
      color: 'border-purple-500',
      action: () => setActiveTab('resources')
    },
    {
      title: 'Active Timetable',
      value: 'Version 7',
      subtitle: 'Effective 17-08-2026 • Multi-Department',
      color: 'border-amber-500',
      action: () => setActiveTab('admin')
    }
  ];

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-3xl">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 mb-4">
            Semester I • Academic Year 2026–27
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Campus Timetable & Resource Availability Engine
          </h2>
          <p className="mt-3 text-sm sm:text-base text-slate-300 leading-relaxed">
            Real-time availability tracker and scheduling platform for all departments and branches at VFSTR: CS, DS, CSBS, IoT, AIML, BS(DS), M.Sc(DS), and M.Tech.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => setActiveTab('faculty')}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-md transition"
            >
              Check Faculty Availability
            </button>
            <button
              onClick={() => setActiveTab('resources')}
              className="bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 px-4 py-2 rounded-lg text-sm font-semibold transition"
            >
              Explore Classrooms & Labs
            </button>
          </div>
        </div>
        <div className="absolute -right-12 -bottom-12 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Live Campus Availability Status Widget (Current Day and Time) */}
      <div className="bg-white border-2 border-indigo-500/30 rounded-2xl p-6 shadow-md relative overflow-hidden">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-200">
          <div className="flex items-center space-x-3">
            <span className="relative flex h-3.5 w-3.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500"></span>
            </span>
            <div>
              <h3 className="font-extrabold text-slate-900 text-base sm:text-lg flex items-center gap-2">
                Live Campus Availability Dashboard
                <span className="text-3xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                  REAL-TIME
                </span>
              </h3>
              <p className="text-xs text-slate-500">
                Calculated dynamically from current system clock & timetable allocations
              </p>
            </div>
          </div>

          {liveData && (
            <div className="bg-indigo-50 border border-indigo-200 text-indigo-900 px-3 py-1.5 rounded-lg text-xs font-bold shadow-2xs">
              📅 {liveData.day} • {liveData.slot_label}
            </div>
          )}
        </div>

        {liveLoading ? (
          <div className="p-8 text-center text-slate-500 text-sm">Evaluating live campus occupancy...</div>
        ) : liveData ? (
          <div className="mt-5 space-y-6">
            {/* Live occupancy status cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* Classrooms */}
              <div
                onClick={() => setActiveTab('resources')}
                className="bg-slate-50 hover:bg-indigo-50/50 border border-slate-200 rounded-xl p-4 cursor-pointer transition shadow-2xs"
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold text-slate-600">Classrooms</span>
                  <span className="text-3xs font-bold bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
                    Total: {liveData.classrooms.total}
                  </span>
                </div>
                <div className="mt-3 flex items-baseline gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span className="text-xl font-black text-emerald-700">{liveData.classrooms.unoccupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">Unoccupied</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                    <span className="text-xl font-black text-rose-700">{liveData.classrooms.occupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">Occupied</span>
                  </div>
                </div>
              </div>

              {/* Laboratories */}
              <div
                onClick={() => setActiveTab('resources')}
                className="bg-slate-50 hover:bg-indigo-50/50 border border-slate-200 rounded-xl p-4 cursor-pointer transition shadow-2xs"
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold text-slate-600">Laboratories</span>
                  <span className="text-3xs font-bold bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
                    Total: {liveData.laboratories.total}
                  </span>
                </div>
                <div className="mt-3 flex items-baseline gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span className="text-xl font-black text-emerald-700">{liveData.laboratories.unoccupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">Unoccupied</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                    <span className="text-xl font-black text-rose-700">{liveData.laboratories.occupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">Occupied</span>
                  </div>
                </div>
              </div>

              {/* Faculty Members */}
              <div
                onClick={() => setActiveTab('faculty')}
                className="bg-slate-50 hover:bg-indigo-50/50 border border-slate-200 rounded-xl p-4 cursor-pointer transition shadow-2xs"
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold text-slate-600">Faculty Members</span>
                  <span className="text-3xs font-bold bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
                    Total: {liveData.faculty.total}
                  </span>
                </div>
                <div className="mt-3 flex items-baseline gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span className="text-xl font-black text-emerald-700">{liveData.faculty.available}</span>
                    <span className="text-3xs font-semibold text-slate-500">Available</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                    <span className="text-xl font-black text-rose-700">{liveData.faculty.occupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">In Class</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Glance Available Resources */}
            <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Ready-for-Use Classrooms Right Now
                </h4>
                <button
                  onClick={() => setActiveTab('resources')}
                  className="text-3xs font-bold text-indigo-600 hover:text-indigo-800"
                >
                  View All Facilities →
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {liveData.classrooms.free_list.map((r, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 bg-white border border-emerald-300 text-emerald-800 text-xs font-mono font-bold px-2.5 py-1 rounded-md shadow-2xs"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                    Room {r.code} ({r.capacity} seats)
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c, i) => (
          <div
            key={i}
            onClick={c.action}
            className={`bg-white border-l-4 ${c.color} border border-slate-200/80 rounded-xl p-5 shadow-xs hover:shadow-md transition-all cursor-pointer`}
          >
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{c.title}</p>
            <h3 className="text-2xl font-black text-slate-900 mt-1">{c.value}</h3>
            <p className="text-3xs text-slate-500 mt-2 leading-tight">{c.subtitle}</p>
          </div>
        ))}
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h4 className="font-bold text-base text-slate-900">Period-Wise Classroom Tracker</h4>
            <p className="text-xs text-slate-500 mt-1">
              Select specific academic periods (1 to 8) to instantly view Occupied and Unoccupied classrooms across all academic blocks.
            </p>
          </div>
          <button
            onClick={() => setActiveTab('resources')}
            className="mt-4 text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>Track Classrooms →</span>
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h4 className="font-bold text-base text-slate-900">Period-Wise Laboratory Tracker</h4>
            <p className="text-xs text-slate-500 mt-1">
              Check computing laboratories and practical session allocations for any period with instant Occupied/Unoccupied detection.
            </p>
          </div>
          <button
            onClick={() => setActiveTab('resources')}
            className="mt-4 text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>Track Laboratories →</span>
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h4 className="font-bold text-base text-slate-900">Deduplicated Faculty Directory</h4>
            <p className="text-xs text-slate-500 mt-1">
              Search faculty availability by department, day, and period without profile duplicates, preserving all teaching schedules.
            </p>
          </div>
          <button
            onClick={() => setActiveTab('faculty')}
            className="mt-4 text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>Check Faculty →</span>
          </button>
        </div>
      </div>
    </div>
  );
}