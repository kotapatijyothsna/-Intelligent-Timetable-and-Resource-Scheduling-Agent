import datetime
import json
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from apps.academics.models import AcademicSection, Subject, AcademicTerm, Department
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.timetables.models import TimetableVersion, TimetableEntry, ScheduleException
from apps.availability.services import AvailabilityService, PERIODS, DAY_NAMES
from apps.scheduling.services import SchedulingService
from apps.assistant.services import AIAssistantService
from apps.assistant.rag_service import TimetableRAGService

DAY_MAP = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
    'MON': 0, 'MONDAY': 0,
    'TUE': 1, 'TUESDAY': 1,
    'WED': 2, 'WEDNESDAY': 2,
    'THU': 3, 'THURSDAY': 3,
    'FRI': 4, 'FRIDAY': 4,
    'SAT': 5, 'SATURDAY': 5,
}

def resolve_day_and_date(request):
    """Resolves day_of_week and date from request query params."""
    day_param = request.GET.get('day', '').upper().strip()
    date_str = request.GET.get('date', '').strip()

    check_date = None
    if date_str:
        try:
            check_date = datetime.date.fromisoformat(date_str)
        except Exception:
            check_date = datetime.date.today()
    else:
        check_date = datetime.date.today()

    if day_param in DAY_MAP:
        day_of_week = DAY_MAP[day_param]
    elif check_date:
        day_of_week = check_date.weekday()
        if day_of_week > 5:
            day_of_week = 0
    else:
        day_of_week = 0

    day_name = DAY_NAMES[day_of_week] if 0 <= day_of_week < len(DAY_NAMES) else 'Monday'
    return day_of_week, day_name, check_date


# --- Metadata & Reference APIs ---

@api_view(['GET'])
def list_departments(request):
    """
    Returns all academic departments and branches.
    """
    depts = Department.objects.all().order_by('code')
    return Response([
        {
            "code": d.code,
            "name": d.name,
            "section_count": d.sections.count(),
            "faculty_count": d.faculty_members.count()
        }
        for d in depts
    ])

@api_view(['GET'])
def list_periods_api(request):
    """
    Returns standard academic period definitions.
    """
    return Response([
        {
            "period": p_num,
            "name": p_data["name"],
            "start_time": p_data["start"].strftime("%H:%M"),
            "end_time": p_data["end"].strftime("%H:%M"),
            "label": p_data["label"]
        }
        for p_num, p_data in sorted(PERIODS.items())
    ])


# --- Availability APIs ---

@api_view(['GET'])
def get_current_availability(request):
    """
    Returns immediate availability status for an entity at current system time.
    Query params: type ('faculty' or 'resource'), id (UUID)
    """
    entity_type = request.GET.get('type')
    entity_id = request.GET.get('id')
    now = datetime.datetime.now()
    check_date = now.date()
    req_start = now.time()
    end_dt = now + datetime.timedelta(minutes=50)
    req_end = end_dt.time()

    if entity_type == 'faculty':
        fac = Faculty.objects.filter(id=entity_id).first()
        if not fac:
            return Response({"error": "Faculty not found"}, status=status.HTTP_404_NOT_FOUND)
        res = AvailabilityService.evaluate_faculty_status(fac, check_date, req_start, req_end)
        return Response({"faculty": fac.full_name, "evaluation": res})

    elif entity_type == 'resource':
        res_obj = Resource.objects.filter(id=entity_id).first()
        if not res_obj:
            return Response({"error": "Resource not found"}, status=status.HTTP_404_NOT_FOUND)
        res = AvailabilityService.evaluate_resource_status(res_obj, check_date, req_start, req_end)
        return Response({"resource": res_obj.code, "evaluation": res})

    return Response({"error": "Invalid query params"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def search_faculty_availability(request):
    """
    Search all faculty availability for a day/date and period/slot.
    Supports filters:
      - period (1 to 8)
      - day ('Monday'..'Saturday' or 0..5)
      - date (ISO date)
      - name (faculty name search)
      - department (department code, e.g. AIML, CS, DS, CSBS, IOT)
    Guarantees each faculty profile appears strictly once (deduplicated).
    Returns status: 'Occupied' or 'Available'.
    """
    day_of_week, day_name, check_date = resolve_day_and_date(request)
    period_param = request.GET.get('period')
    start_str = request.GET.get('start_time')
    end_str = request.GET.get('end_time')

    req_start, req_end, slot_label, detected_period = AvailabilityService.resolve_slot(
        period=period_param, start_time=start_str, end_time=end_str
    )

    name_query = request.GET.get('name', '').strip()
    dept_filter = request.GET.get('department', '').strip()

    faculty_qs = Faculty.objects.filter(is_active=True).select_related('department')

    if dept_filter and dept_filter.upper() != 'ALL':
        faculty_qs = faculty_qs.filter(department__code__iexact=dept_filter)

    if name_query:
        faculty_qs = faculty_qs.filter(full_name__icontains=name_query)

    faculty_qs = faculty_qs.order_by('full_name')

    results = []
    seen_canonical = set()

    for fac in faculty_qs:
        # Extra deduplication guard by normalized name to guarantee single appearance
        norm_key = " ".join(fac.full_name.lower().split())
        if norm_key in seen_canonical:
            continue
        seen_canonical.add(norm_key)

        eval_res = AvailabilityService.evaluate_faculty_status(
            fac, check_date=check_date, req_start=req_start, req_end=req_end, day_of_week=day_of_week
        )

        results.append({
            "id": str(fac.id),
            "name": fac.full_name,
            "faculty_code": fac.faculty_code or '',
            "designation": fac.designation or 'Faculty',
            "department": fac.department.code if fac.department else 'AIML',
            "status": eval_res["status"],
            "reason": eval_res["reason"],
            "details": eval_res["evidence"]
        })

    return Response({
        "day": day_name,
        "day_of_week": day_of_week,
        "date": str(check_date),
        "period": detected_period,
        "slot": slot_label,
        "start_time": req_start.strftime("%H:%M"),
        "end_time": req_end.strftime("%H:%M"),
        "total_faculty": len(results),
        "faculty": results
    })


@api_view(['GET'])
def search_resource_availability(request):
    """
    Search classroom or laboratory availability across all departments and branches.
    Supports filters:
      - period (1 to 8)
      - day ('Monday'..'Saturday' or 0..5)
      - date (ISO date)
      - type ('CLASSROOM' or 'LABORATORY')
      - resource (search by classroom or lab code)
    Strictly returns status:
      - 'Occupied'
      - 'Unoccupied'
    No 'Not Verified', 'Unknown', or 'Pending'.
    """
    day_of_week, day_name, check_date = resolve_day_and_date(request)
    period_param = request.GET.get('period')
    start_str = request.GET.get('start_time')
    end_str = request.GET.get('end_time')

    req_start, req_end, slot_label, detected_period = AvailabilityService.resolve_slot(
        period=period_param, start_time=start_str, end_time=end_str
    )

    res_type = request.GET.get('type', 'CLASSROOM').upper().strip()
    if res_type not in ['CLASSROOM', 'LABORATORY']:
        res_type = 'CLASSROOM'

    resource_query = request.GET.get('resource', '').strip()

    resources_qs = Resource.objects.filter(resource_type=res_type)
    if resource_query:
        resources_qs = resources_qs.filter(
            models.Q(code__icontains=resource_query) | models.Q(name__icontains=resource_query)
        )

    resources_qs = resources_qs.order_by('code')

    results = []
    for r in resources_qs:
        eval_res = AvailabilityService.evaluate_resource_status(
            r, check_date=check_date, req_start=req_start, req_end=req_end, day_of_week=day_of_week
        )
        results.append({
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "capacity": r.capacity,
            "is_shared": r.is_shared,
            "status": eval_res["status"],
            "reason": eval_res["reason"],
            "details": eval_res["evidence"]
        })

    return Response({
        "day": day_name,
        "day_of_week": day_of_week,
        "date": str(check_date),
        "period": detected_period,
        "slot": slot_label,
        "start_time": req_start.strftime("%H:%M"),
        "end_time": req_end.strftime("%H:%M"),
        "resource_type": res_type,
        "total_resources": len(results),
        "resources": results
    })


# --- Scheduling APIs ---

@api_view(['POST'])
def find_common_free_slots_api(request):
    """
    POST body: { faculty_ids: [...], date: 'YYYY-MM-DD', min_duration: 50 }
    """
    data = request.data
    fac_ids = data.get('faculty_ids', [])
    date_str = data.get('date', str(datetime.date.today()))
    min_dur = int(data.get('min_duration', 50))

    check_date = datetime.date.fromisoformat(date_str)
    slots = SchedulingService.find_common_free_slots(fac_ids, check_date, min_duration=min_dur)
    return Response({
        "date": date_str,
        "faculty_count": len(fac_ids),
        "common_free_slots": slots
    })


# --- Timetables APIs ---

@api_view(['GET'])
def get_section_timetable(request, section_id):
    """
    Returns weekly schedule matrix for a specific section with matched faculty and rooms.
    """
    sec = AcademicSection.objects.filter(id=section_id).first()
    if not sec:
        return Response({"error": "Section not found"}, status=status.HTTP_404_NOT_FOUND)

    version = AvailabilityService.get_active_version()
    entries = TimetableEntry.objects.filter(
        timetable_version=version,
        section=sec,
        is_active=True
    ).select_related('subject', 'faculty', 'resource').order_by('day_of_week', 'start_time')

    schedule = []
    for e in entries:
        fac_name = e.faculty.full_name if e.faculty else "Unassigned"
        all_facs = [fac_name] if e.faculty else []
        is_multi = False
        try:
            meta = json.loads(e.original_text)
            if isinstance(meta, dict):
                is_multi = bool(meta.get("multi_period"))
                if meta.get("all_faculty"):
                    all_facs = meta["all_faculty"]
                    fac_name = ", ".join(all_facs)
        except Exception:
            pass

        schedule.append({
            "id": str(e.id),
            "day_of_week": e.day_of_week,
            "start_time": str(e.start_time),
            "end_time": str(e.end_time),
            "subject": e.subject.name,
            "faculty": fac_name,
            "all_faculty": all_facs,
            "room": e.resource.code if e.resource else "Unassigned",
            "session_type": e.session_type,
            "is_multi_period": is_multi,
            "original_cell": e.original_text
        })

    return Response({
        "section": sec.full_name,
        "department": sec.department.code if sec.department else 'AIML',
        "version": version.version_number if version else 0,
        "entries": schedule
    })


@api_view(['GET'])
def get_faculty_timetable(request, faculty_id):
    """
    Returns weekly schedule matrix for a specific faculty member across all cohorts and rooms.
    """
    fac = Faculty.objects.filter(id=faculty_id).first()
    if not fac:
        return Response({"error": "Faculty not found"}, status=status.HTTP_404_NOT_FOUND)

    version = AvailabilityService.get_active_version()
    entries = TimetableEntry.objects.filter(
        timetable_version=version,
        faculty=fac,
        is_active=True
    ).select_related('subject', 'section', 'resource').order_by('day_of_week', 'start_time')

    schedule = []
    for e in entries:
        is_multi = False
        try:
            meta = json.loads(e.original_text)
            if isinstance(meta, dict):
                is_multi = bool(meta.get("multi_period"))
        except Exception:
            pass

        schedule.append({
            "id": str(e.id),
            "day_of_week": e.day_of_week,
            "start_time": str(e.start_time),
            "end_time": str(e.end_time),
            "subject": e.subject.name,
            "section": e.section.full_name,
            "room": e.resource.code if e.resource else "Unassigned",
            "session_type": e.session_type,
            "is_multi_period": is_multi,
            "original_cell": e.original_text
        })

    return Response({
        "faculty": fac.full_name,
        "designation": fac.designation or 'Faculty',
        "department": fac.department.code if fac.department else 'AIML',
        "version": version.version_number if version else 0,
        "total_sessions": len(schedule),
        "entries": schedule
    })


@api_view(['GET'])
def get_resource_timetable(request, resource_id):
    """
    Returns weekly schedule matrix for a specific classroom or laboratory.
    """
    res_obj = Resource.objects.filter(id=resource_id).first()
    if not res_obj:
        return Response({"error": "Resource not found"}, status=status.HTTP_404_NOT_FOUND)

    version = AvailabilityService.get_active_version()
    entries = TimetableEntry.objects.filter(
        timetable_version=version,
        resource=res_obj,
        is_active=True
    ).select_related('subject', 'section', 'faculty').order_by('day_of_week', 'start_time')

    schedule = []
    for e in entries:
        fac_name = e.faculty.full_name if e.faculty else "Unassigned"
        try:
            meta = json.loads(e.original_text)
            if isinstance(meta, dict) and meta.get("all_faculty"):
                fac_name = ", ".join(meta["all_faculty"])
        except Exception:
            pass

        schedule.append({
            "id": str(e.id),
            "day_of_week": e.day_of_week,
            "start_time": str(e.start_time),
            "end_time": str(e.end_time),
            "subject": e.subject.name,
            "section": e.section.full_name,
            "faculty": fac_name,
            "session_type": e.session_type,
            "original_cell": e.original_text
        })

    return Response({
        "resource": res_obj.code,
        "name": res_obj.name,
        "type": res_obj.resource_type,
        "capacity": res_obj.capacity,
        "version": version.version_number if version else 0,
        "total_sessions": len(schedule),
        "entries": schedule
    })


@api_view(['GET'])
def list_all_resources(request):
    """
    Returns all resources (classrooms and laboratories) with basic metadata.
    """
    res_type = request.GET.get('type')
    qs = Resource.objects.all()
    if res_type and res_type.upper() in ['CLASSROOM', 'LABORATORY']:
        qs = qs.filter(resource_type=res_type.upper())
    qs = qs.order_by('resource_type', 'code')
    return Response([
        {
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "type": r.resource_type,
            "capacity": r.capacity
        }
        for r in qs
    ])


@api_view(['GET'])
def list_all_faculty(request):
    """
    Returns all deduplicated faculty members ordered by name.
    """
    dept = request.GET.get('department')
    qs = Faculty.objects.filter(is_active=True).select_related('department')
    if dept and dept.upper() != 'ALL':
        qs = qs.filter(department__code__iexact=dept)
    qs = qs.order_by('full_name')

    seen = set()
    result = []
    for f in qs:
        norm = " ".join(f.full_name.lower().split())
        if norm in seen:
            continue
        seen.add(norm)
        result.append({
            "id": str(f.id),
            "name": f.full_name,
            "designation": f.designation or 'Faculty',
            "department": f.department.code if f.department else 'AIML'
        })
    return Response(result)


@api_view(['GET'])
def get_dashboard_live_status(request):
    """
    Returns live campus availability snapshot based on the current system time & day.
    """
    now = datetime.datetime.now()
    check_date = now.date()
    day_of_week = check_date.weekday()
    if day_of_week > 5:
        day_of_week = 0  # Default to Monday if Sunday
    day_name = DAY_NAMES[day_of_week]

    # Detect current period or closest
    now_time = now.time()
    current_period = None
    for p_num, p_data in sorted(PERIODS.items()):
        if p_data["start"] <= now_time <= p_data["end"]:
            current_period = p_num
            req_start = p_data["start"]
            req_end = p_data["end"]
            slot_label = f"Period {p_num} ({req_start.strftime('%H:%M')} - {req_end.strftime('%H:%M')})"
            break

    # If before classes or after classes or between slots, default to Period 1 or current slot
    if not current_period:
        if now_time < PERIODS[1]["start"]:
            current_period = 1
        elif now_time > PERIODS[8]["end"]:
            current_period = 8
        else:
            # Find next upcoming period
            for p_num, p_data in sorted(PERIODS.items()):
                if p_data["start"] > now_time:
                    current_period = p_num
                    break
            if not current_period:
                current_period = 1

        req_start = PERIODS[current_period]["start"]
        req_end = PERIODS[current_period]["end"]
        slot_label = f"Period {current_period} ({req_start.strftime('%H:%M')} - {req_end.strftime('%H:%M')})"

    # Evaluate Classrooms
    classrooms = Resource.objects.filter(resource_type='CLASSROOM').order_by('code')
    occupied_classrooms = 0
    free_classrooms = []
    for r in classrooms:
        eval_res = AvailabilityService.evaluate_resource_status(
            r, check_date=check_date, req_start=req_start, req_end=req_end, day_of_week=day_of_week
        )
        if eval_res["status"] == "Occupied":
            occupied_classrooms += 1
        else:
            free_classrooms.append({"code": r.code, "name": r.name, "capacity": r.capacity})

    # Evaluate Laboratories
    labs = Resource.objects.filter(resource_type='LABORATORY').order_by('code')
    occupied_labs = 0
    free_labs = []
    for r in labs:
        eval_res = AvailabilityService.evaluate_resource_status(
            r, check_date=check_date, req_start=req_start, req_end=req_end, day_of_week=day_of_week
        )
        if eval_res["status"] == "Occupied":
            occupied_labs += 1
        else:
            free_labs.append({"code": r.code, "name": r.name, "capacity": r.capacity})

    # Evaluate Faculty
    faculty_members = Faculty.objects.filter(is_active=True).select_related('department').order_by('full_name')
    occupied_faculty = 0
    available_faculty = 0
    seen_fac = set()
    for f in faculty_members:
        norm = " ".join(f.full_name.lower().split())
        if norm in seen_fac:
            continue
        seen_fac.add(norm)
        eval_res = AvailabilityService.evaluate_faculty_status(
            f, check_date=check_date, req_start=req_start, req_end=req_end, day_of_week=day_of_week
        )
        if eval_res["status"] == "Occupied":
            occupied_faculty += 1
        else:
            available_faculty += 1

    return Response({
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "day": day_name,
        "day_of_week": day_of_week,
        "date": str(check_date),
        "current_period": current_period,
        "slot_label": slot_label,
        "classrooms": {
            "total": classrooms.count(),
            "occupied": occupied_classrooms,
            "unoccupied": len(free_classrooms),
            "free_list": free_classrooms[:8]
        },
        "laboratories": {
            "total": labs.count(),
            "occupied": occupied_labs,
            "unoccupied": len(free_labs),
            "free_list": free_labs[:8]
        },
        "faculty": {
            "total": len(seen_fac),
            "occupied": occupied_faculty,
            "available": available_faculty
        }
    })


@api_view(['GET'])
def list_sections(request):
    dept_param = request.GET.get('department')
    sections = AcademicSection.objects.all().select_related('department').order_by('year_level', 'section_code')
    if dept_param and dept_param.upper() != 'ALL':
        sections = sections.filter(department__code__iexact=dept_param)

    return Response([
        {
            "id": str(s.id),
            "full_name": s.full_name,
            "year": s.year_level,
            "code": s.section_code,
            "department": s.department.code if s.department else 'AIML',
            "department_name": s.department.name if s.department else ''
        }
        for s in sections
    ])


# --- AI Assistant RAG API ---

@api_view(['POST'])
def assistant_query(request):
    query = request.data.get('query', '')
    api_key = request.data.get('groq_api_key') or request.data.get('api_key')
    conv_id = request.data.get('conversation_id', 'default')
    if not query:
        return Response({"error": "Query prompt required"}, status=status.HTTP_400_BAD_REQUEST)

    result = TimetableRAGService.generate_rag_response(query, api_key=api_key, conversation_id=conv_id)
    return Response(result)
