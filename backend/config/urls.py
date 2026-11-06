"""
URL configuration for Smart Campus AIML Department.
Versioned REST APIs under /api/v1/ and React SPA at /
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render

from apps.api_views import (
    get_current_availability,
    search_faculty_availability,
    search_resource_availability,
    find_common_free_slots_api,
    get_section_timetable,
    get_faculty_timetable,
    get_resource_timetable,
    list_all_resources,
    list_all_faculty,
    get_dashboard_live_status,
    list_sections,
    list_departments,
    list_periods_api,
    assistant_query
)

def index_view(request):
    return render(request, 'index.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index_view, name='index-app'),

    # Metadata & Reference APIs
    path('api/v1/academics/departments/', list_departments, name='list-departments'),
    path('api/v1/timetables/periods/', list_periods_api, name='list-periods'),
    path('api/v1/resources/all/', list_all_resources, name='list-all-resources'),
    path('api/v1/faculty/all/', list_all_faculty, name='list-all-faculty'),

    # Availability APIs
    path('api/v1/availability/current/', get_current_availability, name='avail-current'),
    path('api/v1/availability/live-dashboard/', get_dashboard_live_status, name='avail-live-dashboard'),
    path('api/v1/availability/faculty/', search_faculty_availability, name='avail-faculty'),
    path('api/v1/availability/resources/', search_resource_availability, name='avail-resources'),

    # Scheduling APIs
    path('api/v1/scheduling/common-slots/', find_common_free_slots_api, name='common-slots'),

    # Timetable APIs (Section-wise, Faculty-wise, Room-wise)
    path('api/v1/timetables/sections/', list_sections, name='list-sections'),
    path('api/v1/timetables/sections/<uuid:section_id>/', get_section_timetable, name='section-timetable'),
    path('api/v1/timetables/faculty/<uuid:faculty_id>/', get_faculty_timetable, name='faculty-timetable'),
    path('api/v1/timetables/resources/<uuid:resource_id>/', get_resource_timetable, name='resource-timetable'),

    # AI Assistant API
    path('api/v1/assistant/query/', assistant_query, name='assistant-query'),
]
