import datetime
import json
from django.utils import timezone
from apps.resources.models import Resource, ResourceBlock
from apps.faculty.models import Faculty
from apps.timetables.models import TimetableVersion, TimetableEntry, ScheduleException

# Standard Academic Periods at VFSTR
PERIODS = {
    1: {'name': 'Period 1', 'start': datetime.time(8, 15), 'end': datetime.time(9, 5), 'label': 'Period 1 (08:15 - 09:05)'},
    2: {'name': 'Period 2', 'start': datetime.time(9, 5), 'end': datetime.time(9, 55), 'label': 'Period 2 (09:05 - 09:55)'},
    3: {'name': 'Period 3', 'start': datetime.time(10, 10), 'end': datetime.time(11, 0), 'label': 'Period 3 (10:10 - 11:00)'},
    4: {'name': 'Period 4', 'start': datetime.time(11, 0), 'end': datetime.time(11, 50), 'label': 'Period 4 (11:00 - 11:50)'},
    5: {'name': 'Period 5', 'start': datetime.time(11, 50), 'end': datetime.time(12, 40), 'label': 'Period 5 (11:50 - 12:40)'},
    6: {'name': 'Period 6', 'start': datetime.time(13, 40), 'end': datetime.time(14, 30), 'label': 'Period 6 (13:40 - 14:30)'},
    7: {'name': 'Period 7', 'start': datetime.time(14, 30), 'end': datetime.time(15, 20), 'label': 'Period 7 (14:30 - 15:20)'},
    8: {'name': 'Period 8', 'start': datetime.time(15, 20), 'end': datetime.time(16, 5), 'label': 'Period 8 (15:20 - 16:05)'},
}

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

class AvailabilityService:
    @staticmethod
    def get_active_version():
        return TimetableVersion.objects.filter(is_active=True).first()

    @classmethod
    def resolve_slot(cls, period=None, start_time=None, end_time=None):
        """
        Resolves period number or start/end time strings into datetime.time objects.
        """
        if period and int(period) in PERIODS:
            p_data = PERIODS[int(period)]
            return p_data['start'], p_data['end'], p_data['label'], int(period)

        req_start = datetime.time.fromisoformat(start_time) if isinstance(start_time, str) else (start_time or datetime.time(10, 10))
        req_end = datetime.time.fromisoformat(end_time) if isinstance(end_time, str) else (end_time or datetime.time(11, 0))

        # Check if matches any defined period
        detected_p = None
        for p_num, p_data in PERIODS.items():
            if p_data['start'] == req_start and p_data['end'] == req_end:
                detected_p = p_num
                break

        slot_label = f"{req_start.strftime('%H:%M')} - {req_end.strftime('%H:%M')}"
        if detected_p:
            slot_label = PERIODS[detected_p]['label']

        return req_start, req_end, slot_label, detected_p

    @classmethod
    def evaluate_resource_status(cls, resource, check_date=None, req_start=None, req_end=None, day_of_week=None):
        """
        Evaluates availability of a Classroom or Laboratory strictly based on imported timetable data.
        Returns ONLY:
          - "Occupied"
          - "Unoccupied"
        No "Not Verified", "Unknown", "Pending", or "Unscheduled".
        Considers all departments and branches (CS, DS, CSBS, IoT, AIML, BS, MSC, MTech).
        """
        version = cls.get_active_version()

        if day_of_week is None:
            day_of_week = check_date.weekday() if check_date else 0

        # Maintenance block check: if blocked, it is Occupied
        if check_date and req_start and req_end:
            dt_start = timezone.make_aware(datetime.datetime.combine(check_date, req_start))
            dt_end = timezone.make_aware(datetime.datetime.combine(check_date, req_end))
            block = ResourceBlock.objects.filter(
                resource=resource,
                start_datetime__lt=dt_end,
                end_datetime__gt=dt_start
            ).first()
            if block:
                return {
                    "status": "Occupied",
                    "reason": f"Maintenance block: {block.reason}",
                    "evidence": None
                }

        if not version:
            return {
                "status": "Unoccupied",
                "reason": "No active timetable sessions scheduled.",
                "evidence": None
            }

        # Check Active Timetable Entries across ALL departments and sections
        # Multi-period classes are naturally captured by interval overlap:
        # entry.start_time < req_end AND entry.end_time > req_start
        conflicting_entry = TimetableEntry.objects.filter(
            timetable_version=version,
            resource=resource,
            day_of_week=day_of_week,
            start_time__lt=req_end,
            end_time__gt=req_start,
            is_active=True
        ).select_related('section', 'section__department', 'subject', 'faculty').first()

        if conflicting_entry:
            # Check for schedule cancellation exception
            if check_date:
                exception = ScheduleException.objects.filter(
                    timetable_entry=conflicting_entry,
                    exception_date=check_date
                ).first()
                if exception and exception.exception_type in ['CANCEL', 'RESOURCE_CHANGE']:
                    return {
                        "status": "Unoccupied",
                        "reason": f"Session relieved via {exception.exception_type}: {exception.reason}",
                        "evidence": None
                    }

            fac_display = conflicting_entry.faculty.full_name if conflicting_entry.faculty else "Unassigned"
            all_facs = [fac_display] if conflicting_entry.faculty else []
            try:
                meta = json.loads(conflicting_entry.original_text)
                if isinstance(meta, dict) and meta.get("all_faculty"):
                    all_facs = meta["all_faculty"]
                    fac_display = ", ".join(all_facs)
            except Exception:
                pass

            dept_code = conflicting_entry.section.department.code if conflicting_entry.section.department else "AIML"

            return {
                "status": "Occupied",
                "reason": f"Scheduled class for {conflicting_entry.section.full_name}",
                "evidence": {
                    "section": conflicting_entry.section.full_name,
                    "department": dept_code,
                    "subject": conflicting_entry.subject.name,
                    "faculty": fac_display,
                    "all_faculty": all_facs,
                    "session_type": conflicting_entry.session_type,
                    "start_time": str(conflicting_entry.start_time),
                    "end_time": str(conflicting_entry.end_time)
                }
            }

        return {
            "status": "Unoccupied",
            "reason": "No classes scheduled during this period.",
            "evidence": None
        }

    @classmethod
    def evaluate_faculty_status(cls, faculty, check_date=None, req_start=None, req_end=None, day_of_week=None):
        """
        Determines availability of a faculty member across all departments and sections.
        Returns:
          - "Occupied" (if faculty has any class in that period)
          - "Available" (if no class is scheduled)
        """
        version = cls.get_active_version()
        if not version:
            return {"status": "Available", "reason": "No active timetable sessions scheduled.", "evidence": None}

        if day_of_week is None:
            day_of_week = check_date.weekday() if check_date else 0

        # Query all overlapping timetable entries across every department & section
        overlapping_entries = TimetableEntry.objects.filter(
            timetable_version=version,
            day_of_week=day_of_week,
            start_time__lt=req_end,
            end_time__gt=req_start,
            is_active=True
        ).select_related('section', 'section__department', 'subject', 'resource', 'faculty')

        matching_entry = None
        for entry in overlapping_entries:
            if entry.faculty == faculty:
                matching_entry = entry
                break
            
            # Check JSON metadata for multi-faculty lab sessions
            try:
                meta = json.loads(entry.original_text)
                if isinstance(meta, dict) and "all_faculty" in meta:
                    fac_name = faculty.full_name.upper().strip()
                    if any(fac_name in f.upper().strip() or f.upper().strip() in fac_name for f in meta["all_faculty"]):
                        matching_entry = entry
                        break
            except Exception:
                pass

        if matching_entry:
            # Check for CANCEL / SUBSTITUTE exception on specific date
            if check_date:
                exception = ScheduleException.objects.filter(
                    timetable_entry=matching_entry,
                    exception_date=check_date
                ).first()
                if exception and exception.exception_type in ['CANCEL', 'SUBSTITUTE']:
                    return {
                        "status": "Available",
                        "reason": f"Class relieved via {exception.exception_type}: {exception.reason}",
                        "evidence": None
                    }

            dept_code = matching_entry.section.department.code if matching_entry.section.department else "AIML"

            return {
                "status": "Occupied",
                "reason": f"Teaching {matching_entry.subject.name} for {matching_entry.section.full_name}",
                "evidence": {
                    "section": matching_entry.section.full_name,
                    "department": dept_code,
                    "subject": matching_entry.subject.name,
                    "room": matching_entry.resource.code if matching_entry.resource else "Unassigned",
                    "start_time": str(matching_entry.start_time),
                    "end_time": str(matching_entry.end_time)
                }
            }

        return {
            "status": "Available",
            "reason": "No assigned classes during this period.",
            "evidence": None
        }
