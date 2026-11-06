import re
import datetime
import json
from apps.availability.services import AvailabilityService
from apps.scheduling.services import SchedulingService
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.timetables.models import TimetableVersion, TimetableEntry

class AIAssistantService:
    @classmethod
    def handle_query(cls, user_prompt, conversation_id="default"):
        """
        Interprets natural-language queries using regex entity matching and
        deterministic tool invocations, returning grounded answers with evidence.
        """
        prompt_lower = user_prompt.lower()
        today = datetime.date.today()
        target_date = today

        # Check if user mentioned a specific day of week
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for idx, d_name in enumerate(day_names):
            if d_name in prompt_lower:
                days_ahead = (idx - today.weekday()) % 7
                target_date = today + datetime.timedelta(days=days_ahead)
                break

        tools_invoked = []
        evidence = []
        reply = ""

        # Parse times like "11 am", "11:00", "2 pm", "14:30", "8:15", "8:30"
        time_match = re.search(r'\b(1[0-2]|0?[1-9]|1[3-9]|2[0-3])(?::([0-5][0-9]))?\s*(am|pm)\b|\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b|\bat\s+([0-1]?[0-9]|2[0-3])\b', prompt_lower)
        start_t = datetime.time(10, 10)
        end_t = datetime.time(11, 0)
        if time_match:
            try:
                # Group extraction
                hr = None
                mn = 0
                if time_match.group(1):
                    hr = int(time_match.group(1))
                    mn = int(time_match.group(2) or 0)
                    ampm = time_match.group(3)
                    if ampm == 'pm' and hr < 12:
                        hr += 12
                    elif ampm == 'am' and hr == 12:
                        hr = 0
                elif time_match.group(4):
                    hr = int(time_match.group(4))
                    mn = int(time_match.group(5) or 0)
                elif time_match.group(6):
                    hr = int(time_match.group(6))
                    if hr in [1, 2, 3, 4]:
                        hr += 12 # Default afternoon for 1, 2, 3, 4

                if hr is not None and 0 <= hr <= 23:
                    start_t = datetime.time(hr, mn)
                    end_min = hr * 60 + mn + 50
                    end_t = datetime.time(min(end_min // 60, 23), end_min % 60)
            except Exception:
                pass

        # Detect Room query: e.g. "room 604", "room 619", "who is in 604"
        room_match = re.search(r'\b(?:room|lab)\s*([a-zA-Z0-9\-]+)\b', prompt_lower)
        target_room_code = None
        if room_match:
            target_room_code = room_match.group(1).upper()

        version = AvailabilityService.get_active_version()

        # 1. Room-specific query
        if target_room_code:
            res_obj = Resource.objects.filter(code__iexact=target_room_code).first()
            if res_obj:
                eval_res = AvailabilityService.evaluate_resource_status(res_obj, target_date, start_t, end_t)
                status = eval_res["status"]
                tools_invoked.append({
                    "tool_name": "get_resource_timetable",
                    "parameters": {"room": res_obj.code, "date": str(target_date), "start_time": str(start_t)}
                })

                if status == "OCCUPIED" and eval_res.get("evidence"):
                    ev = eval_res["evidence"]
                    facs = ev.get("faculty", "Assigned Faculty")
                    reply = f"**Room {res_obj.code}** is currently **OCCUPIED** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')}.\n\n• **Class:** {ev['section']}\n• **Subject:** {ev['subject']}\n• **Assigned Faculty:** {facs}\n• **Time Slot:** {ev['start_time']} – {ev['end_time']}"
                    evidence.append(ev)
                elif status == "AVAILABLE":
                    reply = f"**Room {res_obj.code}** is verified **AVAILABLE** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}."
                    evidence.append({"room": res_obj.code, "status": "AVAILABLE"})
                elif status == "UNSCHEDULED":
                    reply = f"**Room {res_obj.code}** is a **shared facility**. The AIML timetable shows no scheduled departmental class for this slot, but external non-AIML occupancy is **NOT VERIFIED**."
                    evidence.append({"room": res_obj.code, "status": "NOT_VERIFIED"})
                else:
                    reply = f"**Room {res_obj.code}** is currently **{status}**: {eval_res['reason']}."
                
                return {
                    "conversation_id": conversation_id,
                    "reply": reply,
                    "tools_invoked": tools_invoked,
                    "evidence": evidence
                }

        # 2. Specific Faculty Query: best match by token overlap
        fac_found = None
        best_score = 0
        for f in Faculty.objects.filter(is_active=True):
            f_tokens = [tok.lower() for tok in re.findall(r'[a-zA-Z]{3,}', f.full_name) if tok.lower() not in ["prof", "assistant", "associate"]]
            score = sum(1 for tok in f_tokens if tok in prompt_lower)
            if score > best_score:
                best_score = score
                fac_found = f

        if fac_found:
            eval_res = AvailabilityService.evaluate_faculty_status(fac_found, target_date, start_t, end_t)
            status = eval_res["status"]
            reason = eval_res["reason"]
            tools_invoked.append({
                "tool_name": "search_faculty_availability",
                "parameters": {"faculty": fac_found.full_name, "date": str(target_date), "start_time": str(start_t)}
            })

            if status == "OCCUPIED" and eval_res.get("evidence"):
                ev = eval_res["evidence"]
                reply = f"**{fac_found.full_name}** ({fac_found.faculty_code or 'Faculty'}) is currently **OCCUPIED** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')}.\n\n• **Teaching:** {ev['subject']}\n• **Section:** {ev['section']}\n• **Classroom/Lab:** Room {ev['room']}\n• **Duration:** {ev['start_time']} – {ev['end_time']}"
                evidence.append(ev)
            else:
                reply = f"**{fac_found.full_name}** ({fac_found.faculty_code or 'Faculty'}) is currently **AVAILABLE** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}. (Reason: {reason})"
                evidence.append({"faculty": fac_found.full_name, "status": status})

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # 3. General Faculty Availability Search
        if "faculty" in prompt_lower or "prof" in prompt_lower or "who is free" in prompt_lower:
            tools_invoked.append({
                "tool_name": "search_faculty_availability",
                "parameters": {"date": str(target_date), "start_time": str(start_t), "end_time": str(end_t)}
            })

            free_facs = []
            for f in Faculty.objects.filter(is_active=True).order_by('full_name'):
                eval_res = AvailabilityService.evaluate_faculty_status(f, target_date, start_t, end_t)
                if eval_res["status"] == "AVAILABLE":
                    free_facs.append(f"{f.full_name} ({f.faculty_code})")

            reply = f"The following AIML faculty members are verified **AVAILABLE** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')}:\n- " + "\n- ".join(free_facs[:8])
            evidence.append({"available_count": len(free_facs), "sample": free_facs[:8]})
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # 4. Classroom / Lab Availability Search
        if "classroom" in prompt_lower or "room" in prompt_lower or "lab" in prompt_lower:
            res_type = 'LABORATORY' if 'lab' in prompt_lower else 'CLASSROOM'
            tools_invoked.append({
                "tool_name": "search_classroom_availability",
                "parameters": {"date": str(target_date), "start_time": str(start_t), "end_time": str(end_t), "type": res_type}
            })

            recs = SchedulingService.recommend_classrooms(target_date, start_t, end_t, min_capacity=40, resource_type=res_type)
            if recs:
                rooms_str = "\n".join([f"• **Room {r['code']}** ({r['capacity']} seats) — Verified Free" for r in recs[:6]])
                reply = f"Verified available {res_type.lower()}s for {start_t.strftime('%I:%M %p')}–{end_t.strftime('%I:%M %p')}:\n\n{rooms_str}"
                evidence.extend(recs[:6])
            else:
                reply = f"No dedicated AIML {res_type.lower()}s are available at {start_t.strftime('%I:%M %p')}. Shared facilities are marked NOT_VERIFIED."

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # Fallback
        reply = "I can assist you with real-time AIML faculty availability, classroom schedules, laboratory bookings, and multi-faculty meeting slots. Try asking:\n• *'Where is Dr. Srikantha Reddy at 8:30 AM?'*\n• *'Who is teaching in Room 604 on Tuesday?'*\n• *'Find an available classroom at 10:10 AM'*"
        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "tools_invoked": tools_invoked,
            "evidence": evidence
        }
