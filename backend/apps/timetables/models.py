import uuid
from django.db import models
from apps.academics.models import AcademicTerm, AcademicSection, Subject
from apps.faculty.models import Faculty
from apps.resources.models import Resource

class TimetableVersion(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('ARCHIVED', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='versions')
    version_number = models.SmallIntegerField(default=1)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')
    is_active = models.BooleanField(default=False)
    change_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('term', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.term} - v{self.version_number} ({self.status})"

class TimetableEntry(models.Model):
    SESSION_TYPES = [
        ('THEORY', 'Theory'),
        ('TUTORIAL', 'Tutorial'),
        ('PRACTICAL', 'Practical'),
        ('COUNSELLING', 'Counselling'),
        ('LIBRARY', 'Library'),
        ('SELF_LEARNING', 'Self Learning'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timetable_version = models.ForeignKey(TimetableVersion, on_delete=models.CASCADE, related_name='entries')
    section = models.ForeignKey(AcademicSection, on_delete=models.CASCADE, related_name='timetable_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetable_entries')
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_entries')
    resource = models.ForeignKey('resources.Resource', on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_entries')
    day_of_week = models.SmallIntegerField() # 0 = Monday ... 5 = Saturday
    start_time = models.TimeField()
    end_time = models.TimeField()
    session_type = models.CharField(max_length=30, choices=SESSION_TYPES, default='THEORY')
    source_sheet = models.CharField(max_length=50, blank=True, default='')
    source_cell = models.CharField(max_length=20, blank=True, default='')
    original_text = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        indexes = [
            models.Index(fields=['day_of_week', 'start_time', 'end_time']),
            models.Index(fields=['faculty', 'day_of_week']),
            models.Index(fields=['resource', 'day_of_week']),
        ]

    def __str__(self):
        return f"{self.section.full_name} | Day {self.day_of_week} {self.start_time}-{self.end_time} | {self.subject.name}"

class ScheduleException(models.Model):
    EXCEPTION_TYPES = [
        ('CANCEL', 'Cancel'),
        ('RESCHEDULE', 'Reschedule'),
        ('SUBSTITUTE', 'Substitute'),
        ('RESOURCE_CHANGE', 'Resource Change'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timetable_entry = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE, related_name='exceptions')
    exception_date = models.DateField()
    exception_type = models.CharField(max_length=30, choices=EXCEPTION_TYPES)
    replacement_faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name='replacement_exceptions')
    replacement_resource = models.ForeignKey('resources.Resource', on_delete=models.SET_NULL, null=True, blank=True, related_name='replacement_exceptions')
    new_start_time = models.TimeField(null=True, blank=True)
    new_end_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Exception on {self.exception_date} ({self.exception_type}) for entry {self.timetable_entry_id}"

class ImportBatch(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARSED', 'Parsed'),
        ('VALIDATING', 'Validating'),
        ('CONFLICTS_FOUND', 'Conflicts Found'),
        ('APPROVED', 'Approved'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    total_records = models.IntegerField(default=0)
    valid_records = models.IntegerField(default=0)
    critical_errors = models.IntegerField(default=0)
    warnings = models.IntegerField(default=0)
    error_summary = models.JSONField(null=True, blank=True)
    imported_version = models.ForeignKey(TimetableVersion, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
