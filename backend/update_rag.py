import re

with open('apps/assistant/rag_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add period parser
old_time = """        # Parse Time
        time_match = re.search(r'\\b(1[0-2]|0?[1-9]|1[3-9]|2[0-3])(?::([0-5][0-9]))?\\s*(am|pm)\\b|\\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\\b|\\bat\\s+([0-1]?[0-9]|2[0-3])\\b', prompt_lower)
        start_t = datetime.time(10, 10)
        end_t = datetime.time(11, 0)
        if time_match:"""

new_time = """        # Parse Period or Time
        period_match = re.search(r'\\bperiod\\s*([1-8])\\b', prompt_lower)
        start_t = datetime.time(10, 10)
        end_t = datetime.time(11, 0)
        if period_match:
            p_num = int(period_match.group(1))
            from apps.availability.services import PERIODS
            if p_num in PERIODS:
                start_t = PERIODS[p_num]['start']
                end_t = PERIODS[p_num]['end']
        elif re.search(r'\\b(1[0-2]|0?[1-9]|1[3-9]|2[0-3])(?::([0-5][0-9]))?\\s*(am|pm)\\b|\\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\\b|\\bat\\s+([0-1]?[0-9]|2[0-3])\\b', prompt_lower):
            time_match = re.search(r'\\b(1[0-2]|0?[1-9]|1[3-9]|2[0-3])(?::([0-5][0-9]))?\\s*(am|pm)\\b|\\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\\b|\\bat\\s+([0-1]?[0-9]|2[0-3])\\b', prompt_lower)"""

content = content.replace(old_time, new_time)

# Replace system instruction
old_sys = '''        system_instruction = (
            "You are the official Smart Campus AI Assistant for the Department of Artificial Intelligence & Machine Learning (ACSE) "
            "at Vignan\'s Foundation for Science, Technology and Research (VFSTR).\\n\\n"
            "STRICT GROUNDING RULES:\\n"
            "1. Answer the user\'s question accurately using ONLY the provided RETRIEVED ACADEMIC CONTEXT.\\n"
            "2. Never hallucinate, estimate, or invent timetable records, faculty assignments, or room occupancy.\\n"
            "3. If a room or faculty is OCCUPIED, explicitly mention the Subject, Section cohort, Room code, and exact Time slot.\\n"
            "4. If multiple faculty members are assigned to a practical lab session, name all of them.\\n"
            "5. If a facility is a shared resource and not scheduled for ACSE, explicitly explain that it is NOT_VERIFIED.\\n"
            "6. Present your answer clearly in formatted Markdown with bullet points where appropriate."
        )'''

new_sys = '''        system_instruction = (
            "You are the official Smart Campus AI Assistant for all academic departments and branches "
            "(CS, DS, CSBS, IoT, AIML, BS-DS, M.Sc-DS, and M.Tech) at Vignan\'s Foundation for Science, Technology and Research (VFSTR).\\n\\n"
            "STRICT GROUNDING RULES:\\n"
            "1. Answer the user\'s question accurately using ONLY the provided RETRIEVED ACADEMIC CONTEXT.\\n"
            "2. Never hallucinate, estimate, or invent timetable records, faculty assignments, or room occupancy.\\n"
            "3. For classrooms and laboratories, use strictly 'Occupied' or 'Unoccupied'. Do not use Not Verified, Unknown, or Pending.\\n"
            "4. If a room or faculty is Occupied, explicitly mention the Subject, Section cohort, Department, Room code, and exact Time slot.\\n"
            "5. If multiple faculty members are assigned to a session, name all of them.\\n"
            "6. Present your answer clearly in formatted Markdown with bullet points where appropriate."
        )'''

content = content.replace(old_sys, new_sys)

with open('apps/assistant/rag_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated apps/assistant/rag_service.py!')
