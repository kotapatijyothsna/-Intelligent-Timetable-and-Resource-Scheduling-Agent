import React from 'react';

export default function AdminDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Department Administration & Governance</h2>
        <p className="text-xs text-slate-500">Timetable version control, schedule exceptions, and conflict audit</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Active Version Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Version</span>
            <span className="bg-emerald-100 text-emerald-800 text-3xs font-bold px-2 py-0.5 rounded-full">ACTIVE</span>
          </div>
          <h3 className="text-lg font-extrabold text-slate-900">Version 7.0</h3>
          <p className="text-xs text-slate-500 mt-1">Source: ACSE TIMETABLE (V7) - W.e.f 17-8-2026.xlsx</p>
          <div className="mt-4 pt-3 border-t border-slate-100 text-3xs text-slate-600 space-y-1">
            <p>• 24 Verified Academic Sections</p>
            <p>• 628 Active Weekly Sessions</p>
            <p>• Concurrency Locking: Enforced</p>
          </div>
        </div>

        {/* Conflict Audit Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Conflict Engine</span>
            <span className="bg-indigo-100 text-indigo-800 text-3xs font-bold px-2 py-0.5 rounded-full">VERIFIED</span>
          </div>
          <h3 className="text-lg font-extrabold text-emerald-600">0 Overlap Conflicts</h3>
          <p className="text-xs text-slate-500 mt-1">Full cross-section interval scan passed</p>
          <div className="mt-4 pt-3 border-t border-slate-100 text-3xs text-slate-600 space-y-1">
            <p>• Faculty Overlaps: 0 Detected</p>
            <p>• Room Collisions: 0 Detected</p>
            <p>• Shared Lab Warnings: 11 Indexed</p>
          </div>
        </div>

        {/* Exception Manager Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Schedule Exceptions</span>
            <span className="bg-slate-100 text-slate-700 text-3xs font-bold px-2 py-0.5 rounded-full">SUBSTITUTIONS</span>
          </div>
          <h3 className="text-lg font-extrabold text-slate-900">Leave & Swap Manager</h3>
          <p className="text-xs text-slate-500 mt-1">Log cancellations, room reallocations, and guest lectures</p>
          <button className="mt-4 w-full bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold py-2 rounded-lg transition">
            Create Schedule Exception
          </button>
        </div>
      </div>

      {/* Audit Log Table Preview */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
        <div className="bg-slate-50 px-6 py-3 border-b border-slate-200">
          <h3 className="font-bold text-xs text-slate-800 uppercase tracking-wider">System Audit Trail (Latest Actions)</h3>
        </div>
        <div className="p-4 overflow-x-auto text-xs">
          <table className="w-full text-left">
            <thead>
              <tr className="text-slate-400 border-b border-slate-100 text-3xs uppercase">
                <th className="pb-2">Timestamp</th>
                <th className="pb-2">Actor</th>
                <th className="pb-2">Action</th>
                <th className="pb-2">Target Entity</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              <tr>
                <td className="py-2.5 font-mono text-3xs">2026-11-05 14:11:32</td>
                <td>System Import Job</td>
                <td><span className="font-bold text-emerald-600">BULK_IMPORT</span></td>
                <td>TimetableVersion (v1)</td>
                <td><span className="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded text-3xs font-bold">COMMITTED</span></td>
              </tr>
              <tr>
                <td className="py-2.5 font-mono text-3xs">2026-11-05 14:03:16</td>
                <td>Conflict Detector</td>
                <td><span className="font-bold text-indigo-600">INTERVAL_AUDIT</span></td>
                <td>628 Entries Scanned</td>
                <td><span className="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded text-3xs font-bold">ZERO CONFLICTS</span></td>
              </tr>
              <tr>
                <td className="py-2.5 font-mono text-3xs">2026-11-05 14:02:56</td>
                <td>Data Pipeline</td>
                <td><span className="font-bold text-slate-900">NORMALIZATION</span></td>
                <td>24 Sections Extracted</td>
                <td><span className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded text-3xs font-bold">COMPLETED</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
