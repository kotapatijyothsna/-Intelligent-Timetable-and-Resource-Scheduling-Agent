"""
Smart Campus - Retrieval-Augmented Generation (RAG) Service for AIML Timetable
Powered by Groq LLM (e.g. LLaMA-3.3-70B) & Structured Academic Database Retrieval.
"""

import os
import re
import json
import datetime
from django.utils import timezone
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.academics.models import AcademicSection, Subject
from apps.timetables.models import TimetableVersion, TimetableEntry
from apps.availability.services import AvailabilityService
from apps.scheduling.services import SchedulingService

class TimetableRAGService:
    @classmethod
    def retrieve_context(cls, query_text):
        """
        Retrieval Step: Fetches relevant timetable sessions, faculty allocations,
        and room vacancies matching the query from the verified database.
        """
        prompt_lower = query_text.lower()
        today = datetime.date.today()
        target_date = today

        # Parse Day of week
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        matched_day_idx = None
        for idx, d_name in enumerate(day_names):
            if d_name in prompt_lower:
                days_ahead = (idx - today.weekday()) % 7
                target_date = today + datetime.timedelta(days=days_ahead)
                matched_day_idx = idx
                break

        # Parse Period or Time
        period_match = re.search(r'\bperiod\s*([1-8])\b', prompt_lower)
        start_t = datetime.time(10, 10)
        end_t = datetime.time(11, 0)
        if period_match:
            p_num = int(period_match.group(1))
            from apps.availability.services import PERIODS
            if p_num in PERIODS:
                start_t = PERIODS[p_num]['start']
                end_t = PERIODS[p_num]['end']
        elif re.search(r'\b(1[0-2]|0?[1-9]|1[3-9]|2[0-3])(?::([0-5][0-9]))?\s*(am|pm)\b|\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b|\bat\s+([0-1]?[0-9]|2[0-3])\b', prompt_lower):
            time_match = re.search(r'\b(1[0-2]|0?[1-9]|1[3-9]|2[0-3])(?::([0-5][0-9]))?\s*(am|pm)\b|\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b|\bat\s+([0-1]?[0-9]|2[0-3])\b', prompt_lower)
            try:
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
                        hr += 12
                if hr is not None and 0 <= hr <= 23:
                    start_t = datetime.time(hr, mn)
                    end_min = hr * 60 + mn + 50
                    end_t = datetime.time(min(end_min // 60, 23), end_min % 60)
            except Exception:
                pass

        version = AvailabilityService.get_active_version()
        retrieved_documents = []

        # 1. Check Faculty Match
        fac_candidates = []
        for f in Faculty.objects.filter(is_active=True):
            f_tokens = [tok.lower() for tok in re.findall(r'[a-zA-Z]{3,}', f.full_name) if tok.lower() not in ["prof", "assistant", "associate", "dr.", "mr.", "ms."]]
            score = sum(1 for tok in f_tokens if tok in prompt_lower)
            if score > 0 or (f.faculty_code and f.faculty_code.lower() in prompt_lower):
                fac_candidates.append((score, f))

        fac_candidates.sort(key=lambda x: x[0], reverse=True)
        if fac_candidates:
            target_faculty = fac_candidates[0][1]
            eval_res = AvailabilityService.evaluate_faculty_status(target_faculty, target_date, start_t, end_t)
            
            # Fetch faculty weekly schedule
            faculty_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                faculty=target_faculty,
                is_active=True
            ).select_related('section', 'subject', 'resource').order_by('day_of_week', 'start_time')[:8]

            schedule_summary = []
            for fe in faculty_entries:
                schedule_summary.append(
                    f"Day {day_names[fe.day_of_week].capitalize()} {fe.start_time.strftime('%H:%M')}-{fe.end_time.strftime('%H:%M')}: {fe.subject.name} for {fe.section.full_name} in Room {fe.resource.code if fe.resource else 'Unassigned'}"
                )

            retrieved_documents.append({
                "type": "FACULTY_PROFILE_AND_SCHEDULE",
                "entity": target_faculty.full_name,
                "faculty_code": target_faculty.faculty_code,
                "evaluated_slot": f"{target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')}) {start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
                "status": eval_res["status"],
                "reason": eval_res["reason"],
                "evidence": eval_res.get("evidence"),
                "sample_weekly_classes": schedule_summary
            })

        # 2. Check Room / Lab Match
        room_match = re.search(r'\b(?:room|lab)\s*([a-zA-Z0-9\-]+)\b', prompt_lower)
        if room_match:
            rcode = room_match.group(1).upper()
            res_obj = Resource.objects.filter(code__iexact=rcode).first()
            if res_obj:
                eval_res = AvailabilityService.evaluate_resource_status(res_obj, target_date, start_t, end_t)
                room_entries = TimetableEntry.objects.filter(
                    timetable_version=version,
                    resource=res_obj,
                    is_active=True
                ).select_related('section', 'subject', 'faculty').order_by('day_of_week', 'start_time')[:8]

                room_sched = []
                for re_entry in room_entries:
                    room_sched.append(
                        f"Day {day_names[re_entry.day_of_week].capitalize()} {re_entry.start_time.strftime('%H:%M')}-{re_entry.end_time.strftime('%H:%M')}: {re_entry.subject.name} ({re_entry.section.full_name})"
                    )

                retrieved_documents.append({
                    "type": "RESOURCE_OCCUPANCY",
                    "room_code": res_obj.code,
                    "name": res_obj.name,
                    "capacity": res_obj.capacity,
                    "is_shared": res_obj.is_shared,
                    "evaluated_slot": f"{target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')}) {start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
                    "status": eval_res["status"],
                    "reason": eval_res["reason"],
                    "evidence": eval_res.get("evidence"),
                    "weekly_occupancy": room_sched
                })

        # 3. Check Section Match (e.g. "II ACSE-A", "IV CS", "III DS-B", "II CSBS", "II IOT")
        sec_obj = None
        # Try ACSE section match
        sec_match = re.search(r'\b(ii|iii|iv)\s*acse-?([a-l])\b', prompt_lower)
        if sec_match:
            sec_full = f"{sec_match.group(1).upper()} ACSE-{sec_match.group(2).upper()}"
            sec_obj = AcademicSection.objects.filter(full_name=sec_full).first()
        # Try other branch matches: CS, DS, CSBS, IOT
        if not sec_obj:
            branch_match = re.search(r'\b(ii|iii|iv)\s*(cs|ds|csbs|iot|mtech)\b', prompt_lower)
            if branch_match:
                yr = branch_match.group(1).upper()
                br = branch_match.group(2).upper()
                sec_obj = AcademicSection.objects.filter(full_name__istartswith=f"{yr} {br}").first()
        # Try generic section name search
        if not sec_obj:
            for sec_candidate in AcademicSection.objects.all():
                if sec_candidate.full_name.lower().replace('-', ' ').replace('  ', ' ') in prompt_lower:
                    sec_obj = sec_candidate
                    break
        if sec_obj:
                s_entries = TimetableEntry.objects.filter(
                    timetable_version=version,
                    section=sec_obj,
                    is_active=True
                ).select_related('subject', 'faculty', 'resource').order_by('day_of_week', 'start_time')

                day_filter = matched_day_idx if matched_day_idx is not None else target_date.weekday()
                day_classes = [
                    f"{e.start_time.strftime('%H:%M')}-{e.end_time.strftime('%H:%M')}: {e.subject.name} | Faculty: {e.faculty.full_name if e.faculty else 'Department Faculty'} | Room: {e.resource.code if e.resource else 'Unassigned'}"
                    for e in s_entries.filter(day_of_week=day_filter)
                ]

                retrieved_documents.append({
                    "type": "SECTION_SCHEDULE",
                    "section": sec_obj.full_name,
                    "day": day_names[day_filter].capitalize(),
                    "classes": day_classes
                })

        # 4. Check General Classroom Recommendations
        if "classroom" in prompt_lower or "free room" in prompt_lower or "available room" in prompt_lower or "lab" in prompt_lower:
            res_type = 'LABORATORY' if 'lab' in prompt_lower else 'CLASSROOM'
            recs = SchedulingService.recommend_classrooms(target_date, start_t, end_t, min_capacity=40, resource_type=res_type)
            retrieved_documents.append({
                "type": "AVAILABLE_RESOURCES_LIST",
                "resource_type": res_type,
                "slot": f"{target_date.strftime('%Y-%m-%d')} {start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
                "available_rooms": recs[:8]
            })

        # 5. Check Free Faculty List
        if "who is free" in prompt_lower or "free faculty" in prompt_lower or "available faculty" in prompt_lower:
            free_facs = []
            for f in Faculty.objects.filter(is_active=True).order_by('full_name'):
                eval_res = AvailabilityService.evaluate_faculty_status(f, target_date, start_t, end_t)
                if eval_res["status"] == "AVAILABLE":
                    free_facs.append(f"{f.full_name} ({f.faculty_code or 'ID Unassigned'})")
            retrieved_documents.append({
                "type": "AVAILABLE_FACULTY_LIST",
                "slot": f"{target_date.strftime('%Y-%m-%d')} {start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
                "total_available": len(free_facs),
                "free_faculty_sample": free_facs[:12]
            })

        return {
            "query": query_text,
            "target_date": str(target_date),
            "target_slot": f"{start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}",
            "retrieved_documents": retrieved_documents
        }

    @classmethod
    def generate_rag_response(cls, user_prompt, api_key=None, conversation_id="default"):
        """
        Augmentation & Generation Step:
        Builds grounded context from retrieved database records and executes
        high-speed inference with Groq LLM (LLaMA-3.3-70B).
        """
        from django.conf import settings
        groq_api_key = api_key or os.environ.get("GROQ_API_KEY") or getattr(settings, 'GROQ_API_KEY', None)

        # Step 1: Retrieve ground-truth documents from database
        context_data = cls.retrieve_context(user_prompt)
        docs = context_data["retrieved_documents"]

        # Step 2: Fallback to deterministic engine if no Groq API key is available
        if not groq_api_key:
            from apps.assistant.services import AIAssistantService
            fallback_res = AIAssistantService.handle_query(user_prompt, conversation_id)
            fallback_res["rag_metadata"] = {
                "rag_mode": "DETERMINISTIC_FALLBACK (No Groq API Key provided)",
                "retrieved_documents_count": len(docs),
                "retrieved_context": docs
            }
            fallback_res["reply"] += "\n\n*(Note: Groq LLM RAG mode is ready. Provide your Groq API key to activate real-time LLaMA-3.3-70B generation.)*"
            return fallback_res

        # Step 3: Format Context for Groq LLM
        context_str = json.dumps(docs, indent=2)

        system_instruction = (
            "You are the official Smart Campus AI Assistant for all academic departments and branches "
            "(CS, DS, CSBS, IoT, AIML, BS-DS, M.Sc-DS, and M.Tech) at Vignan's Foundation for Science, Technology and Research (VFSTR).\n\n"
            "STRICT GROUNDING RULES:\n"
            "1. Answer the user's question accurately using ONLY the provided RETRIEVED ACADEMIC CONTEXT.\n"
            "2. Never hallucinate, estimate, or invent timetable records, faculty assignments, or room occupancy.\n"
            "3. For classrooms and laboratories, use strictly 'Occupied' or 'Unoccupied'. Do not use Not Verified, Unknown, or Pending.\n"
            "4. If a room or faculty is Occupied, explicitly mention the Subject, Section cohort, Department, Room code, and exact Time slot.\n"
            "5. If multiple faculty members are assigned to a session, name all of them.\n"
            "6. Present your answer clearly in formatted Markdown with bullet points where appropriate."
        )

        user_content = (
            f"User Question: {user_prompt}\n\n"
            f"Evaluated Target Date: {context_data['target_date']}\n"
            f"Evaluated Target Time Slot: {context_data['target_slot']}\n\n"
            f"=== RETRIEVED VERIFIED TIMETABLE CONTEXT (Source of Truth) ===\n"
            f"{context_str}\n"
            f"=== END CONTEXT ==="
        )

        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)

            # Available active models on this Groq account
            model_to_use = "qwen/qwen3.8-27b"

            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content}
                ],
                model=model_to_use,
                temperature=0.1,
                max_tokens=600
            )

            llm_reply = chat_completion.choices[0].message.content

            return {
                "conversation_id": conversation_id,
                "reply": llm_reply,
                "tools_invoked": [
                    {
                        "tool_name": "groq_timetable_rag_retrieval",
                        "model": model_to_use,
                        "documents_retrieved": len(docs)
                    }
                ],
                "evidence": docs,
                "rag_metadata": {
                    "rag_mode": f"ACTIVE (Groq {model_to_use})",
                    "retrieved_documents_count": len(docs)
                }
            }

        except Exception as e:
            # Graceful error handling
            return {
                "conversation_id": conversation_id,
                "reply": f"Groq RAG Generation Encountered an Error: {str(e)}",
                "tools_invoked": [{"tool_name": "groq_api_error"}],
                "evidence": docs,
                "rag_metadata": {"error": str(e)}
            }
