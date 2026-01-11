from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import Counter
import sqlite3
import json
import os
import glob
import re
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
DB_NAME = "transfer_data.db"
DATA_DIR = "assist_data"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Using google/gemini-2.0-flash-001 which supports PDF document uploads
OPENROUTER_MODEL = "google/gemini-2.0-flash-001"

def normalize_course_code(course_code):
    """Normalize course codes for comparison (e.g., 'MATH 150' -> 'MATH150')"""
    if not course_code:
        return ""
    # Remove spaces and convert to uppercase
    normalized = re.sub(r'\s+', '', course_code.upper())
    return normalized

def normalize_university_name(name):
    """Convert common university abbreviations to full names"""
    name_upper = name.upper()
    mapping = {
        'UC BERKELEY': 'University of California, Berkeley',
        'BERKELEY': 'University of California, Berkeley',
        'UCLA': 'University of California, Los Angeles',
        'UC LOS ANGELES': 'University of California, Los Angeles',
        'UC SAN DIEGO': 'University of California, San Diego',
        'UCSD': 'University of California, San Diego',
        'UC IRVINE': 'University of California, Irvine',
        'UCI': 'University of California, Irvine',
        'UC DAVIS': 'University of California, Davis',
        'UCD': 'University of California, Davis',
        'UC SANTA BARBARA': 'University of California, Santa Barbara',
        'UCSB': 'University of California, Santa Barbara',
        'UC RIVERSIDE': 'University of California, Riverside',
        'UCR': 'University of California, Riverside',
        'UC SANTA CRUZ': 'University of California, Santa Cruz',
        'UCSC': 'University of California, Santa Cruz',
        'UC MERCED': 'University of California, Merced',
        'UCM': 'University of California, Merced',
    }
    
    for abbrev, full_name in mapping.items():
        if abbrev in name_upper:
            return full_name
    
    return name  # Return original if no mapping found

def search_agreements(target_university, target_major, source_college_id=None):
    """Search for relevant articulation agreements"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Normalize university name
    normalized_uni = normalize_university_name(target_university)
    
    # Create flexible major search - handle variations like "Computer Science" matching "COMPUTER SCIENCE, B.S."
    # Split major into words and create a more flexible search
    major_words = target_major.upper().split()
    major_query = f"%{target_major.upper()}%"
    
    # Also try searching for just the first two words (e.g., "COMPUTER SCIENCE" from "Computer Science")
    if len(major_words) >= 2:
        major_query_alt = f"%{major_words[0]}%{major_words[1]}%"
    else:
        major_query_alt = major_query
    
    # Search by receiving university and major (case-insensitive for major)
    uni_query = f"%{normalized_uni}%"
    
    # Try primary search first
    sql = '''
        SELECT sending_id, sending_name, receiving_id, receiving_name, major_name, agreement_key
        FROM agreements
        WHERE receiving_name LIKE ? AND (UPPER(major_name) LIKE ? OR UPPER(major_name) LIKE ?)
    '''
    params = [uni_query, major_query, major_query_alt]
    
    if source_college_id:
        sql += " AND sending_id = ?"
        params.append(source_college_id)
    
    cursor.execute(sql, params)
    results = cursor.fetchall()
    
    # If no results, try a more lenient search (just university match)
    if len(results) == 0:
        print(f"[DEBUG] No exact matches, trying lenient search...")
        sql = '''
            SELECT sending_id, sending_name, receiving_id, receiving_name, major_name, agreement_key
            FROM agreements
            WHERE receiving_name LIKE ?
        '''
        params = [uni_query]
        
        if source_college_id:
            sql += " AND sending_id = ?"
            params.append(source_college_id)
        
        cursor.execute(sql, params)
        all_uni_results = cursor.fetchall()
        
        # Filter by major in Python for more flexibility
        major_upper = target_major.upper()
        results = [
            row for row in all_uni_results 
            if major_upper in row[4].upper() or any(word in row[4].upper() for word in major_words if len(word) > 3)
        ]
    
    conn.close()
    
    print(f"[DEBUG] Search: '{target_university}' -> '{normalized_uni}', major: '{target_major}' -> found {len(results)} agreements")
    if results:
        print(f"[DEBUG] Sample result: {results[0][3]} - {results[0][4]}")
    
    # Format results
    return [
        {
            'sending_id': row[0],
            'sending_name': row[1],
            'receiving_id': row[2],
            'receiving_university': row[3],
            'major': row[4],
            'agreement_key': row[5]
        }
        for row in results
    ]

def build_assist_url(sending_id, receiving_id, year_id):
    """Build a direct link to the assist.org agreement page.
    
    Note: The viewByKey parameter requires an agreement key from assist.org's API
    which is not available in our JSON data export. Without it, users are taken
    to the institution pair's agreement page where they can select their major.
    """
    # This URL takes users to the agreement page for the institution pair
    # They can then click on their specific major to view the full agreement
    return f"https://assist.org/transfer/results?year={year_id}&institution={sending_id}&agreement={receiving_id}&agreementType=to&viewAgreementsOptions=true&view=agreement&viewBy=major&viewSendingAgreements=false"

def load_agreement_json(agreement_key):
    """Load full agreement JSON file by agreement key"""
    # Agreement key format: "filename_major" (e.g., "51_to_79_master.json_Computer Science, B.A.")
    files = glob.glob(os.path.join(DATA_DIR, "*_master.json"))
    
    # Extract filename and major from agreement_key
    # The format is: "{filename}_{major_name}"
    # We need to find the last occurrence of "_master.json_" to split correctly
    if '_master.json_' in agreement_key:
        parts = agreement_key.split('_master.json_', 1)
        if len(parts) == 2:
            filename_part = parts[0] + '_master.json'
            major_name = parts[1]
            
            # Find matching file
            for file_path in files:
                if os.path.basename(file_path) == filename_part:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, dict) and 'result' in data:
                                result = data['result']
                                
                                # Extract institution IDs and year for assist.org URL
                                sending_id = None
                                receiving_id = None
                                year_id = None
                                try:
                                    sending_inst = json.loads(result.get('sendingInstitution', '{}'))
                                    receiving_inst = json.loads(result.get('receivingInstitution', '{}'))
                                    academic_year = json.loads(result.get('academicYear', '{}'))
                                    
                                    sending_id = sending_inst.get('id')
                                    receiving_id = receiving_inst.get('id')
                                    year_id = academic_year.get('id')
                                except Exception as e:
                                    print(f"[DEBUG] Could not parse institution/year data: {e}")
                                
                                # Build assist.org URL
                                assist_url = build_assist_url(sending_id, receiving_id, year_id) if sending_id and receiving_id and year_id else None
                                
                                # Parse templateAssets to find matching major
                                template_assets_str = result.get('templateAssets', '[]')
                                try:
                                    template_assets = json.loads(template_assets_str) if isinstance(template_assets_str, str) else template_assets_str
                                except:
                                    template_assets = []
                                
                                # Try exact match first
                                for major in template_assets:
                                    if major.get('name') == major_name:
                                        # Return the major data along with the full result for context
                                        return {
                                            'major_data': major,
                                            'full_result': result,
                                            'agreement_key': agreement_key,
                                            'assist_url': assist_url
                                        }
                                
                                # If no exact match, try case-insensitive match
                                major_name_upper = major_name.upper()
                                for major in template_assets:
                                    if major.get('name', '').upper() == major_name_upper:
                                        return {
                                            'major_data': major,
                                            'full_result': result,
                                            'agreement_key': agreement_key,
                                            'assist_url': assist_url
                                        }
                                
                                # If still no match, return the full result anyway (user can browse all majors)
                                print(f"[DEBUG] Major '{major_name}' not found in templateAssets, returning full result")
                                return {
                                    'full_result': result,
                                    'agreement_key': agreement_key,
                                    'requested_major': major_name,
                                    'assist_url': assist_url
                                }
                            elif isinstance(data, list):
                                for item in data:
                                    if item.get('key') == agreement_key:
                                        return item
                    except Exception as e:
                        print(f"[DEBUG] Error loading file {file_path}: {e}")
                        continue
    
    # Fallback: search all files for exact key match
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if item.get('key') == agreement_key:
                            return item
        except Exception as e:
            continue
    
    print(f"[DEBUG] Could not load agreement for key: {agreement_key}")
    return None

def get_major_cell_ids(agreement_data):
    """
    Get all cell IDs that belong to the selected major's requirement groups.
    This is needed because a single agreement file contains articulations for ALL majors.
    """
    cell_ids = set()
    
    if not isinstance(agreement_data, dict):
        return cell_ids
    
    # Try to get the major-specific templateAssets
    major_data = agreement_data.get('major_data')
    template_assets = None
    
    if major_data and isinstance(major_data, dict):
        template_assets_raw = major_data.get('templateAssets', [])
        if isinstance(template_assets_raw, str):
            try:
                template_assets = json.loads(template_assets_raw)
            except:
                template_assets = []
        else:
            template_assets = template_assets_raw
    
    if not template_assets:
        # Fall back to full_result and find the requested major
        full_result = agreement_data.get('full_result', {})
        template_assets_str = full_result.get('templateAssets', '[]')
        
        try:
            raw_assets = json.loads(template_assets_str) if isinstance(template_assets_str, str) else template_assets_str
        except:
            raw_assets = []
        
        if raw_assets and isinstance(raw_assets, list) and raw_assets[0].get('name'):
            # This is a list of majors
            requested_major = agreement_data.get('requested_major', '')
            for major in raw_assets:
                if major.get('name', '').upper() == requested_major.upper():
                    template_assets = major.get('templateAssets', [])
                    break
            if not template_assets and raw_assets:
                template_assets = raw_assets[0].get('templateAssets', [])
        else:
            template_assets = raw_assets
    
    if not template_assets:
        return cell_ids
    
    # Extract all cell IDs from RequirementGroups
    for asset in template_assets:
        if asset.get('type') == 'RequirementGroup':
            for section in asset.get('sections', []):
                for row in section.get('rows', []):
                    for cell in row.get('cells', []):
                        cell_id = cell.get('id', '')
                        if cell_id:
                            cell_ids.add(cell_id)
    
    return cell_ids


def extract_articulation_mappings(agreement_data):
    """
    Extract articulation mappings from agreement JSON.
    Returns a list of mappings: each mapping contains:
    - receiving_course: The university requirement
    - sending_courses: List of community college courses that satisfy it
    - template_cell_id: ID linking to the requirement group
    
    IMPORTANT: Only returns articulations for the selected major, not all majors in the file.
    """
    mappings = []
    
    if not isinstance(agreement_data, dict):
        return mappings
    
    # Get cell IDs for the selected major to filter articulations
    major_cell_ids = get_major_cell_ids(agreement_data)
    print(f"[DEBUG] Major has {len(major_cell_ids)} cell IDs")
    
    full_result = agreement_data.get('full_result')
    
    if full_result:
        articulations_str = full_result.get('articulations', '[]')
        try:
            articulations = json.loads(articulations_str) if isinstance(articulations_str, str) else articulations_str
            if isinstance(articulations, list):
                total_articulations = len(articulations)
                for articulation in articulations:
                    art_data = articulation.get('articulation', {})
                    template_cell_id = articulation.get('templateCellId', '')
                    
                    # FILTER: Only include articulations for this major's cells
                    if major_cell_ids and template_cell_id not in major_cell_ids:
                        continue
                    
                    # Get the receiving university's required course
                    receiving_course = None
                    if art_data.get('type') == 'Course':
                        course = art_data.get('course', {})
                        prefix = course.get('prefix', '')
                        course_number = course.get('courseNumber', '')
                        course_title = course.get('courseTitle', '')
                        
                        if prefix and course_number:
                            receiving_course = {
                                'course_code': f"{prefix} {course_number}".strip(),
                                'course_name': course_title or '',
                                'normalized_code': normalize_course_code(f"{prefix} {course_number}"),
                                'template_cell_id': template_cell_id
                            }
                    elif art_data.get('type') == 'Series':
                        # Handle series (multiple courses as one requirement)
                        series = art_data.get('series', {})
                        series_name = series.get('name', '')
                        if series_name:
                            receiving_course = {
                                'course_code': series_name,
                                'course_name': 'Course Series',
                                'normalized_code': normalize_course_code(series_name),
                                'template_cell_id': template_cell_id,
                                'is_series': True
                            }
                    
                    # Get the sending community college's equivalent courses
                    sending_courses = []
                    sending_articulation = art_data.get('sendingArticulation', {})
                    items = sending_articulation.get('items', [])
                    
                    for item in items:
                        if item.get('type') == 'CourseGroup':
                            sub_items = item.get('items', [])
                            for sub_item in sub_items:
                                if sub_item.get('type') == 'Course':
                                    prefix = sub_item.get('prefix', '')
                                    course_number = sub_item.get('courseNumber', '')
                                    course_title = sub_item.get('courseTitle', '')
                                    
                                    if prefix and course_number:
                                        sending_courses.append({
                                            'course_code': f"{prefix} {course_number}".strip(),
                                            'course_name': course_title or '',
                                            'normalized_code': normalize_course_code(f"{prefix} {course_number}")
                                        })
                        elif item.get('type') == 'Course':
                            prefix = item.get('prefix', '')
                            course_number = item.get('courseNumber', '')
                            course_title = item.get('courseTitle', '')
                            
                            if prefix and course_number:
                                sending_courses.append({
                                    'course_code': f"{prefix} {course_number}".strip(),
                                    'course_name': course_title or '',
                                    'normalized_code': normalize_course_code(f"{prefix} {course_number}")
                                })
                    
                    if receiving_course and sending_courses:
                        mappings.append({
                            'receiving_course': receiving_course,
                            'sending_courses': sending_courses,
                            'template_cell_id': template_cell_id
                        })
                
                print(f"[DEBUG] Filtered to {len(mappings)} articulations for this major (from {total_articulations} total)")
        except Exception as e:
            print(f"[DEBUG] Error parsing articulations: {e}")
    
    return mappings


def infer_subject_from_courses(cells, sections):
    """
    Infer a subject name from course prefixes and departments in a requirement group.
    Returns a human-readable subject name.
    """
    # Collect prefixes and departments from courses
    prefixes = []
    departments = []
    
    for section in sections:
        rows = section.get('rows', [])
        for row in rows:
            row_cells = row.get('cells', [])
            for cell in row_cells:
                cell_type = cell.get('type', '')
                
                if cell_type == 'Course':
                    course = cell.get('course', {})
                    prefix = course.get('prefix', '')
                    dept = course.get('department', '')
                    if prefix:
                        prefixes.append(prefix.upper())
                    if dept:
                        departments.append(dept)
                
                elif cell_type == 'Series':
                    series = cell.get('series', {})
                    for c in series.get('courses', []):
                        prefix = c.get('prefix', '')
                        dept = c.get('department', '')
                        if prefix:
                            prefixes.append(prefix.upper())
                        if dept:
                            departments.append(dept)
    
    # Subject mapping from common prefixes
    prefix_to_subject = {
        'MATH': 'Mathematics',
        'MAT': 'Mathematics',
        'PHYS': 'Physics',
        'PHY': 'Physics',
        'CHEM': 'Chemistry',
        'CHE': 'Chemistry',
        'BIO': 'Biology',
        'BIOL': 'Biology',
        'ECS': 'Computer Science',
        'CISP': 'Computer Science',
        'CIS': 'Computer Science',
        'CS': 'Computer Science',
        'CSCI': 'Computer Science',
        'ENG': 'Engineering',
        'ENGR': 'Engineering',
        'EEC': 'Electrical Engineering',
        'ECE': 'Electrical Engineering',
        'EECS': 'Electrical Engineering & CS',
        'CMN': 'Communication',
        'COMM': 'Communication',
        'SPCH': 'Communication',
        'ENL': 'English',
        'ENGL': 'English',
        'UWP': 'Writing',
        'COM': 'Comparative Literature',
        'ACCT': 'Accounting',
        'MGT': 'Management',
        'BUS': 'Business',
        'ECON': 'Economics',
        'STAT': 'Statistics',
        'NAS': 'Native American Studies',
        'HIST': 'History',
        'PHIL': 'Philosophy',
        'PSYC': 'Psychology',
        'SOC': 'Sociology',
    }
    
    # Count prefix occurrences
    prefix_counts = Counter(prefixes)
    
    if prefix_counts:
        # Get the most common prefix
        most_common_prefix = prefix_counts.most_common(1)[0][0]
        
        # Check if we have a mapping
        if most_common_prefix in prefix_to_subject:
            return prefix_to_subject[most_common_prefix]
        
        # Try partial matches
        for prefix_key, subject in prefix_to_subject.items():
            if most_common_prefix.startswith(prefix_key) or prefix_key.startswith(most_common_prefix):
                return subject
    
    # Fall back to department names
    if departments:
        dept_counts = Counter(departments)
        most_common_dept = dept_counts.most_common(1)[0][0]
        return most_common_dept
    
    return None


def extract_requirement_groups(agreement_data):
    """
    Extract requirement groups from templateAssets to understand selection rules.
    Returns a dict mapping group_id to:
    - instruction_type: 'Following' (all required) or 'NFromArea' (select N)
    - amount: How many courses/units needed (for NFromArea)
    - amount_unit_type: 'Course' or 'QuarterUnit' etc.
    - courses: List of course IDs in this group
    - title: The section title
    """
    groups = {}
    
    if not isinstance(agreement_data, dict):
        return groups
    
    # Try to get template assets from major_data first (nested structure)
    # or from full_result (flat structure like the ASSIST API response)
    template_assets = None
    
    major_data = agreement_data.get('major_data')
    if major_data and isinstance(major_data, dict):
        # The file has nested structure: result.templateAssets is a list of majors,
        # each with their own templateAssets
        template_assets_raw = major_data.get('templateAssets', [])
        if isinstance(template_assets_raw, str):
            try:
                template_assets = json.loads(template_assets_raw)
            except:
                template_assets = []
        else:
            template_assets = template_assets_raw
    
    if not template_assets:
        # Fall back to full_result.templateAssets
        full_result = agreement_data.get('full_result', {})
        template_assets_str = full_result.get('templateAssets', '[]')
        
        try:
            raw_assets = json.loads(template_assets_str) if isinstance(template_assets_str, str) else template_assets_str
        except:
            raw_assets = []
        
        if not isinstance(raw_assets, list):
            return groups
        
        # Check if this is a list of majors (nested structure) or direct requirement assets
        if raw_assets and isinstance(raw_assets[0], dict):
            first_item = raw_assets[0]
            if 'name' in first_item and 'templateAssets' in first_item:
                # This is a list of majors - find the requested major
                requested_major = agreement_data.get('requested_major', '')
                for major in raw_assets:
                    if major.get('name', '').upper() == requested_major.upper():
                        template_assets = major.get('templateAssets', [])
                        break
                
                # If no match, use the first major's assets
                if not template_assets and raw_assets:
                    template_assets = raw_assets[0].get('templateAssets', [])
            else:
                # Direct requirement assets (flat structure)
                template_assets = raw_assets
    
    if not template_assets or not isinstance(template_assets, list):
        print(f"[DEBUG] No template assets found for requirement groups")
        return groups
    
    print(f"[DEBUG] Parsing {len(template_assets)} template assets")
    
    # First pass: collect titles by position
    titles_by_position = {}
    for asset in template_assets:
        if asset.get('type') == 'RequirementTitle':
            position = asset.get('position', 0)
            content = asset.get('content', '')
            titles_by_position[position] = content
    
    # Second pass: process requirement groups
    for asset in template_assets:
        if asset.get('type') != 'RequirementGroup':
            continue
        
        group_id = asset.get('groupId', '')
        instruction = asset.get('instruction', {})
        position = asset.get('position', 0)
        
        # Find the closest title before this group
        group_title = ''
        for pos in sorted(titles_by_position.keys(), reverse=True):
            if pos <= position:
                group_title = titles_by_position[pos]
                break
        
        # List of generic/non-subject titles we want to replace
        generic_titles = [
            'REQUIRED FOR ADMISSION',
            'ADDITIONAL MAJOR PREPARATION COURSES',
            'PREPARATION COURSES FOR THE MAJOR',
            'HIGHLY RECOMMENDED',
            'RECOMMENDED',
            'TECHNICAL ELECTIVES',
            'REQUIREMENTS',
            'THE MAJOR PROGRAM',
            'SELECTIVE MAJOR REQUIREMENTS ADMISSIONS INFORMATION',
            'TRANSFER ADMISSIONS GUARANTEE (TAG)',
            'GENERAL INFORMATION',
        ]
        
        # Get sections for subject inference
        sections = asset.get('sections', [])
        
        # If title is generic or empty, try to infer from courses
        if not group_title or group_title.upper() in [t.upper() for t in generic_titles]:
            inferred_subject = infer_subject_from_courses([], sections)
            if inferred_subject:
                group_title = inferred_subject
        
        # Parse instruction type
        instruction_type = instruction.get('type', 'Following')
        selection_type = instruction.get('selectionType', 'Complete')
        amount = instruction.get('amount', 0)
        amount_unit_type = instruction.get('amountUnitType', 'Course')
        
        # Extract course cell IDs from this group, tracking section-level rules
        course_cell_ids = []
        section_rules = []  # Track per-section selection rules
        
        for section in sections:
            # Skip non-Section types (like SectionHeader)
            if section.get('type') != 'Section':
                continue
            
            section_cell_ids = []
            rows = section.get('rows', [])
            for row in rows:
                cells = row.get('cells', [])
                for cell in cells:
                    cell_id = cell.get('id', '')
                    if cell_id:
                        section_cell_ids.append(cell_id)
                        course_cell_ids.append(cell_id)
            
            # Check section-level advisements for "NFollowing" rules
            # This handles cases like "Select 1 from: Biology OR Chemistry OR Physics"
            section_advisements = section.get('advisements', [])
            section_required = len(section_cell_ids)  # Default: all required
            section_is_select_n = False
            
            for adv in section_advisements:
                adv_type = adv.get('type', '')
                if adv_type == 'NFollowing':
                    adv_amount = adv.get('amount', 0)
                    adv_unit_type = adv.get('amountUnitType', 'Course')
                    if adv_unit_type == 'Course':
                        section_required = int(adv_amount) if adv_amount else len(section_cell_ids)
                    else:
                        section_required = max(1, int(adv_amount / 4)) if adv_amount else len(section_cell_ids)
                    section_is_select_n = True
                    break
            
            if section_cell_ids:
                section_rules.append({
                    'cell_ids': section_cell_ids,
                    'required': section_required,
                    'total_options': len(section_cell_ids),
                    'is_select_n': section_is_select_n
                })
        
        # Calculate total required count respecting section-level rules
        total_required = 0
        for sec in section_rules:
            total_required += sec['required']
        
        # If no section rules or group-level NFromArea overrides
        if instruction_type == 'NFromArea' and not any(s.get('is_select_n') for s in section_rules):
            if amount_unit_type == 'Course':
                total_required = int(amount) if amount else len(course_cell_ids)
            else:
                total_required = max(1, int(amount / 4)) if amount else len(course_cell_ids)
        elif total_required == 0:
            total_required = len(course_cell_ids)
        
        groups[group_id] = {
            'instruction_type': instruction_type,
            'selection_type': selection_type,
            'amount': amount,
            'amount_unit_type': amount_unit_type,
            'course_cell_ids': course_cell_ids,
            'required_count': total_required,
            'total_options': len(course_cell_ids),
            'title': group_title,
            'attributes': asset.get('attributes', []),
            'section_rules': section_rules  # Include section-level rules for comparison
        }
    
    print(f"[DEBUG] Extracted {len(groups)} requirement groups")
    return groups

def extract_courses_from_agreement(agreement_data):
    """Extract required courses and prerequisites from agreement JSON (legacy function)"""
    required_courses = []
    prerequisites = []
    
    if not isinstance(agreement_data, dict):
        return required_courses, prerequisites
    
    # Use the new articulation mappings
    mappings = extract_articulation_mappings(agreement_data)
    for mapping in mappings:
        receiving = mapping.get('receiving_course')
        if receiving:
            required_courses.append(receiving)
    
    # Fallback: Try standard keys (for backwards compatibility)
    if len(required_courses) == 0:
        courses_data = (
            agreement_data.get('courses') or
            agreement_data.get('requirements') or
            agreement_data.get('courseRequirements') or
            agreement_data.get('requiredCourses') or
            []
        )
        
        if isinstance(courses_data, list):
            for course in courses_data:
                if isinstance(course, dict):
                    course_code = course.get('courseCode') or course.get('code') or course.get('course_code')
                    course_name = course.get('courseName') or course.get('name') or course.get('course_name')
                    is_prereq = course.get('isPrerequisite', False) or course.get('prerequisite', False)
                    
                    if course_code:
                        course_info = {
                            'course_code': course_code,
                            'course_name': course_name or '',
                            'normalized_code': normalize_course_code(course_code)
                        }
                        
                        if is_prereq:
                            prerequisites.append(course_info)
                        else:
                            required_courses.append(course_info)
    
    print(f"[DEBUG] Extracted {len(required_courses)} required courses, {len(prerequisites)} prerequisites")
    return required_courses, prerequisites

def compare_transcript_to_agreement(student_courses, agreement_data):
    """
    Compare student courses against agreement requirements using articulation mappings
    and requirement groups to properly handle 'select N from list' requirements.
    """
    
    # Get articulation mappings and requirement groups
    all_mappings = extract_articulation_mappings(agreement_data)
    requirement_groups = extract_requirement_groups(agreement_data)
    
    # Normalize student courses into a set for quick lookup
    student_course_set = set()
    student_course_map = {}
    for course in student_courses:
        code = course.get('course_code', '')
        normalized = normalize_course_code(code)
        if normalized:
            student_course_set.add(normalized)
            student_course_map[normalized] = course
    
    print(f"[DEBUG] Student courses normalized: {list(student_course_set)[:10]}...")
    
    # Build a mapping from template_cell_id to articulation
    cell_to_mapping = {}
    for mapping in all_mappings:
        cell_id = mapping.get('template_cell_id', '')
        if cell_id:
            cell_to_mapping[cell_id] = mapping
    
    # Map each course to its group
    cell_to_group = {}
    for group_id, group_info in requirement_groups.items():
        for cell_id in group_info.get('course_cell_ids', []):
            cell_to_group[cell_id] = group_id
    
    # Process each requirement group to determine satisfaction
    group_results = {}
    completed_required = []
    missing_required = []
    
    for group_id, group_info in requirement_groups.items():
        instruction_type = group_info.get('instruction_type', 'Following')
        required_count = group_info.get('required_count', 0)
        course_cell_ids = group_info.get('course_cell_ids', [])
        group_title = group_info.get('title', '')
        section_rules = group_info.get('section_rules', [])
        
        # Build cell_id to completion status map
        cell_completion_map = {}
        cell_course_info_map = {}
        
        for cell_id in course_cell_ids:
            mapping = cell_to_mapping.get(cell_id)
            if not mapping:
                continue
            
            receiving_course = mapping.get('receiving_course', {})
            sending_courses = mapping.get('sending_courses', [])
            
            # Check if student has taken any of the sending courses
            matched = False
            matched_student_course = None
            
            for sending in sending_courses:
                sending_normalized = sending.get('normalized_code', '')
                if sending_normalized in student_course_set:
                    matched = True
                    matched_student_course = student_course_map.get(sending_normalized, {})
                    break
            
            course_info = {
                'course_code': receiving_course.get('course_code', ''),
                'course_name': receiving_course.get('course_name', ''),
                'normalized_code': receiving_course.get('normalized_code', ''),
                'group_id': group_id,
                'group_title': group_title,
                'cell_id': cell_id
            }
            
            if matched:
                course_info['satisfied_by'] = matched_student_course.get('course_code', '') if matched_student_course else ''
                course_info['student_grade'] = matched_student_course.get('grade', '') if matched_student_course else ''
                course_info['student_credits'] = matched_student_course.get('credits', 0) if matched_student_course else 0
                cell_completion_map[cell_id] = True
            else:
                cc_options = ', '.join([s.get('course_code', '') for s in sending_courses[:3]])
                if len(sending_courses) > 3:
                    cc_options += f" (+{len(sending_courses) - 3} more)"
                course_info['can_be_satisfied_by'] = cc_options
                cell_completion_map[cell_id] = False
            
            cell_course_info_map[cell_id] = course_info
        
        # Process sections with their individual rules
        completed_in_group = []
        missing_in_group = []
        effective_completed = 0
        effective_required = 0
        
        if section_rules:
            for section in section_rules:
                section_cell_ids = section.get('cell_ids', [])
                section_required = section.get('required', len(section_cell_ids))
                is_select_n = section.get('is_select_n', False)
                
                # Count completions in this section
                section_completed = []
                section_missing = []
                
                for cid in section_cell_ids:
                    course_info = cell_course_info_map.get(cid)
                    if not course_info:
                        continue
                    if cell_completion_map.get(cid, False):
                        section_completed.append(course_info)
                    else:
                        section_missing.append(course_info)
                
                section_completed_count = len(section_completed)
                
                if is_select_n:
                    # "Select N from list" section - cap contributions at required amount
                    effective_completed += min(section_completed_count, section_required)
                    effective_required += section_required
                    
                    # Add completed courses
                    completed_in_group.extend(section_completed[:section_required])
                    
                    # For missing: only show what's needed, as a choice
                    if section_completed_count < section_required:
                        needed = section_required - section_completed_count
                        # Create a "Select N" entry showing options
                        if section_missing:
                            alternatives = [m.get('course_name', m.get('course_code', '')) for m in section_missing[:5]]
                            choice_entry = {
                                'course_code': f"Select {needed}",
                                'course_name': ' OR '.join(alternatives) + ('...' if len(section_missing) > 5 else ''),
                                'is_choice': True,
                                'choice_count': needed,
                                'alternatives': section_missing,
                                'group_id': group_id,
                                'group_title': group_title
                            }
                            missing_in_group.append(choice_entry)
                else:
                    # All required section
                    effective_completed += section_completed_count
                    effective_required += section_required
                    completed_in_group.extend(section_completed)
                    missing_in_group.extend(section_missing)
        else:
            # No section rules - simple processing (fallback)
            for cid, completed in cell_completion_map.items():
                course_info = cell_course_info_map.get(cid)
                if not course_info:
                    continue
                if completed:
                    completed_in_group.append(course_info)
                else:
                    missing_in_group.append(course_info)
            
            effective_completed = len(completed_in_group)
            effective_required = required_count
        
        # Determine group satisfaction
        if effective_required > 0:
            group_satisfied = effective_completed >= effective_required
        else:
            group_satisfied = True
        
        remaining_needed = max(0, effective_required - effective_completed)
        
        # Check if any section has select-N rules
        has_select_n = any(s.get('is_select_n', False) for s in section_rules) if section_rules else False
        display_instruction = 'NFromArea' if has_select_n or instruction_type == 'NFromArea' else instruction_type
        
        group_results[group_id] = {
            'title': group_title,
            'instruction_type': display_instruction,
            'required_count': effective_required,
            'total_options': len(course_cell_ids),
            'completed_count': effective_completed,
            'satisfied': group_satisfied,
            'remaining_needed': remaining_needed,
            'completed_courses': completed_in_group,
            'missing_courses': missing_in_group
        }
        
        # Add to overall completed/missing lists
        completed_required.extend(completed_in_group)
        
        # For groups with select-N sections, missing_in_group already contains the choice entries
        # So we just add them directly
        missing_required.extend(missing_in_group)
    
    # Handle any articulations not in a known group (fallback)
    ungrouped_completed = []
    ungrouped_missing = []
    
    for mapping in all_mappings:
        cell_id = mapping.get('template_cell_id', '')
        if cell_id and cell_id in cell_to_group:
            continue  # Already processed in a group
        
        receiving_course = mapping.get('receiving_course', {})
        sending_courses = mapping.get('sending_courses', [])
        
        matched = False
        matched_student_course = None
        
        for sending in sending_courses:
            sending_normalized = sending.get('normalized_code', '')
            if sending_normalized in student_course_set:
                matched = True
                matched_student_course = student_course_map.get(sending_normalized, {})
                break
        
        if matched:
            ungrouped_completed.append({
                'course_code': receiving_course.get('course_code', ''),
                'course_name': receiving_course.get('course_name', ''),
                'normalized_code': receiving_course.get('normalized_code', ''),
                'satisfied_by': matched_student_course.get('course_code', '') if matched_student_course else '',
                'student_grade': matched_student_course.get('grade', '') if matched_student_course else '',
                'student_credits': matched_student_course.get('credits', 0) if matched_student_course else 0
            })
        else:
            cc_options = ', '.join([s.get('course_code', '') for s in sending_courses[:3]])
            if len(sending_courses) > 3:
                cc_options += f" (+{len(sending_courses) - 3} more)"
            ungrouped_missing.append({
                'course_code': receiving_course.get('course_code', ''),
                'course_name': receiving_course.get('course_name', ''),
                'normalized_code': receiving_course.get('normalized_code', ''),
                'can_be_satisfied_by': cc_options
            })
    
    completed_required.extend(ungrouped_completed)
    missing_required.extend(ungrouped_missing)
    
    # Deduplicate results by normalized_code
    seen_completed = set()
    deduped_completed = []
    for course in completed_required:
        key = course.get('normalized_code', '')
        if key and key not in seen_completed:
            seen_completed.add(key)
            deduped_completed.append(course)
    
    seen_missing = set()
    deduped_missing = []
    for course in missing_required:
        key = course.get('normalized_code', '')
        if key and key not in seen_missing:
            seen_missing.add(key)
            deduped_missing.append(course)
    
    completed_required = deduped_completed
    missing_required = deduped_missing
    
    # Calculate progress at the group level
    # Use weighted progress: sum of (completed / required) for each group
    total_groups = len(requirement_groups) if requirement_groups else max(1, len(all_mappings))
    satisfied_groups = sum(1 for g in group_results.values() if g.get('satisfied', False))
    
    # If no groups parsed, fall back to course-level calculation
    if not requirement_groups:
        total_required = len(all_mappings)
        completed_count = len(completed_required)
        progress_percentage = (completed_count / total_required * 100) if total_required > 0 else 0
    else:
        # Calculate weighted progress: average of group completion percentages
        # This gives partial credit for groups that are partially complete
        group_progress_sum = 0
        for g in group_results.values():
            req = g.get('required_count', 1)
            completed = g.get('completed_count', 0)
            if req > 0:
                group_progress_sum += min(1.0, completed / req)  # Cap at 100% per group
            else:
                group_progress_sum += 1.0  # Empty group counts as complete
        
        progress_percentage = (group_progress_sum / total_groups * 100) if total_groups > 0 else 0
    
    # Also calculate simple course-level progress for comparison
    course_level_progress = 0
    total_courses_needed = len(completed_required) + len(missing_required)
    if total_courses_needed > 0:
        course_level_progress = round(len(completed_required) / total_courses_needed * 100, 1)
    
    print(f"[DEBUG] Group-level progress: {satisfied_groups}/{total_groups} groups satisfied")
    print(f"[DEBUG] Weighted progress: {round(progress_percentage, 1)}%")
    print(f"[DEBUG] Course-level: {len(completed_required)} completed, {len(missing_required)} remaining ({course_level_progress}%)")
    
    return {
        'progress_percentage': round(progress_percentage, 1),
        'course_progress_percentage': course_level_progress,  # Simple X/Y courses
        'prereq_progress': 100,  # Not tracking separately
        'completed_required': completed_required,
        'missing_required': missing_required,
        'completed_prerequisites': [],
        'missing_prerequisites': [],
        'total_required': len(completed_required) + len(missing_required),
        'total_prerequisites': 0,
        'group_results': group_results,  # Detailed per-group breakdown
        'total_groups': total_groups,
        'satisfied_groups': satisfied_groups
    }

@app.route('/api/analyze-transcript', methods=['POST'])
def analyze_transcript():
    """Analyze transcript and compare against agreements"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        target_university = request.form.get('university', '')
        target_major = request.form.get('major', '')
        
        if not target_university or not target_major:
            return jsonify({'error': 'University and major are required'}), 400
        
        if not OPENROUTER_API_KEY:
            return jsonify({'error': 'OpenRouter API key not configured'}), 500
        
        # Read file content
        file_content = file.read()
        file_name = file.filename
        
        # Determine MIME type
        mime_type = 'application/pdf'
        if file_name.endswith('.txt'):
            mime_type = 'text/plain'
        elif file_name.endswith('.csv'):
            mime_type = 'text/csv'
        
        # Prepare prompt for structured extraction - also extract the college name
        prompt = """Extract information from this transcript and return ONLY valid JSON with no other text:
{
  "college_name": "Name of the community college",
  "courses": [
    {
      "course_code": "MATH 150",
      "course_name": "Calculus I",
      "credits": 4,
      "grade": "A",
      "completed": true
    }
  ]
}

Extract the college/institution name and ALL courses with their codes, names, credits, and grades.
Return only the JSON object, no explanations or markdown formatting."""
        
        # Create base64 encoded file data for OpenRouter
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # Build the message content with file attachment
        # OpenRouter uses OpenAI-compatible format with image_url for document uploads
        message_content = [
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{file_base64}"
                }
            }
        ]
        
        # Make request to OpenRouter API
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Transcript Analyzer"
        }
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": message_content
                }
            ]
        }
        
        api_response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )
        
        if api_response.status_code != 200:
            error_msg = api_response.json().get('error', {}).get('message', 'Unknown error')
            return jsonify({'error': f'OpenRouter API error: {error_msg}'}), 500
        
        response_data = api_response.json()
        response_text = response_data['choices'][0]['message']['content'].strip()
        
        # Clean up response (remove markdown code blocks if present)
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text, flags=re.MULTILINE)
            response_text = re.sub(r'\s*```\s*$', '', response_text, flags=re.MULTILINE)
        
        # Parse JSON
        try:
            parsed_data = json.loads(response_text)
            # Handle both old format (list) and new format (dict with college_name and courses)
            if isinstance(parsed_data, dict):
                student_courses = parsed_data.get('courses', [])
                detected_college = parsed_data.get('college_name', '')
            elif isinstance(parsed_data, list):
                student_courses = parsed_data
                detected_college = ''
            else:
                student_courses = []
                detected_college = ''
            
            print(f"[DEBUG] Detected college: {detected_college}")
            print(f"[DEBUG] Extracted {len(student_courses)} courses from transcript")
            if student_courses:
                print(f"[DEBUG] Sample courses: {[c.get('course_code') for c in student_courses[:3]]}")
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON parse error: {e}")
            print(f"[DEBUG] Raw response: {response_text[:500]}")
            return jsonify({'error': f'Failed to parse course data: {str(e)}', 'raw_response': response_text}), 500
        
        # Search for relevant agreements - prioritize student's college if detected
        all_agreements = search_agreements(target_university, target_major)
        print(f"[DEBUG] Found {len(all_agreements)} total agreements for {target_university} - {target_major}")
        
        # Filter and prioritize agreements from the detected college
        if detected_college:
            # Find agreements from the student's college first
            college_agreements = [a for a in all_agreements if detected_college.lower() in a.get('sending_name', '').lower()]
            other_agreements = [a for a in all_agreements if detected_college.lower() not in a.get('sending_name', '').lower()]
            
            # If we found agreements from the student's college, use only those
            if college_agreements:
                agreements = college_agreements
                print(f"[DEBUG] Filtered to {len(agreements)} agreements from {detected_college}")
            else:
                # If no exact match, still prioritize similar names
                agreements = all_agreements
                print(f"[DEBUG] No exact college match, using all {len(agreements)} agreements")
        else:
            agreements = all_agreements
        
        # Compare against each agreement
        comparison_results = []
        for agreement in agreements:
            agreement_key = agreement.get('agreement_key')
            if not agreement_key:
                print(f"[DEBUG] Skipping agreement - no key")
                continue
            
            agreement_data = load_agreement_json(agreement_key)
            if not agreement_data:
                print(f"[DEBUG] Could not load agreement JSON for key: {agreement_key}")
                continue
            
            print(f"[DEBUG] Comparing against agreement: {agreement_key}")
            comparison = compare_transcript_to_agreement(student_courses, agreement_data)
            print(f"[DEBUG] Comparison result: {comparison['progress_percentage']}% progress, {len(comparison['completed_required'])}/{comparison['total_required']} courses completed")
            
            comparison_results.append({
                **agreement,
                'comparison': comparison,
                'agreement_data': agreement_data
            })
        
        return jsonify({
            'student_courses': student_courses,
            'agreements': comparison_results,
            'target_university': target_university,
            'target_major': target_major,
            'detected_college': detected_college
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search-agreements', methods=['GET'])
def search_agreements_endpoint():
    """Search agreements by university and major"""
    try:
        target_university = request.args.get('university', '')
        target_major = request.args.get('major', '')
        source_college = request.args.get('source_college', None, type=int)
        
        if not target_university or not target_major:
            return jsonify({'error': 'University and major are required'}), 400
        
        agreements = search_agreements(target_university, target_major, source_college)
        return jsonify(agreements)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agreement/<agreement_key>', methods=['GET'])
def get_agreement(agreement_key):
    """Get full agreement details"""
    try:
        agreement_data = load_agreement_json(agreement_key)
        if not agreement_data:
            return jsonify({'error': 'Agreement not found'}), 404
        
        return jsonify(agreement_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'db_exists': os.path.exists(DB_NAME)})

@app.route('/api/test-search', methods=['GET'])
def test_search():
    """Test search endpoint for debugging"""
    try:
        university = request.args.get('university', 'UC Berkeley')
        major = request.args.get('major', 'Computer Science')
        
        # Test the search
        agreements = search_agreements(university, major)
        
        # Also test what's in the database
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        normalized_uni = normalize_university_name(university)
        cursor.execute('''
            SELECT COUNT(*) FROM agreements 
            WHERE receiving_name LIKE ? AND UPPER(major_name) LIKE ?
        ''', [f"%{normalized_uni}%", f"%{major.upper()}%"])
        count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT receiving_name, major_name FROM agreements 
            WHERE receiving_name LIKE ? AND UPPER(major_name) LIKE ?
            LIMIT 5
        ''', [f"%{normalized_uni}%", f"%{major.upper()}%"])
        sample_results = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'search_params': {
                'university': university,
                'normalized_university': normalized_uni,
                'major': major
            },
            'database_count': count,
            'search_results_count': len(agreements),
            'sample_database_results': [
                {'university': r[0], 'major': r[1]} for r in sample_results
            ],
            'search_results': agreements[:5]  # First 5 results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files', methods=['GET'])
def list_files():
    """List all available agreement files"""
    try:
        files = glob.glob(os.path.join(DATA_DIR, "*_master.json"))
        file_list = []
        for file_path in files:
            filename = os.path.basename(file_path)
            # Extract sending and receiving IDs from filename (e.g., "10_to_1_master.json")
            parts = filename.replace('_master.json', '').split('_to_')
            if len(parts) == 2:
                file_list.append({
                    'filename': filename,
                    'sending_id': parts[0],
                    'receiving_id': parts[1],
                    'path': file_path
                })
        return jsonify({
            'total_files': len(file_list),
            'files': file_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/<filename>', methods=['GET'])
def get_file(filename):
    """Get raw file data by filename"""
    try:
        # Security: ensure filename doesn't contain path traversal
        if '..' in filename or '/' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/institutions', methods=['GET'])
def list_institutions():
    """List all unique sending and receiving institutions"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get unique sending institutions
        cursor.execute('SELECT DISTINCT sending_id, sending_name FROM agreements ORDER BY sending_name')
        sending = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        
        # Get unique receiving institutions
        cursor.execute('SELECT DISTINCT receiving_id, receiving_name FROM agreements ORDER BY receiving_name')
        receiving = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'sending_institutions': sending,
            'receiving_institutions': receiving
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/majors', methods=['GET'])
def list_majors():
    """List all unique majors"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT major_name FROM agreements ORDER BY major_name')
        majors = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'majors': majors,
            'total': len(majors)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-recommendations', methods=['POST'])
def generate_recommendations():
    """Generate AI-powered recommendations based on student progress"""
    try:
        data = request.get_json()
        
        student_courses = data.get('student_courses', [])
        completed_requirements = data.get('completed_requirements', [])
        missing_requirements = data.get('missing_requirements', [])
        target_university = data.get('target_university', '')
        target_major = data.get('target_major', '')
        gpa = data.get('gpa', 0)
        progress_percentage = data.get('progress_percentage', 0)
        detected_college = data.get('detected_college', '')
        
        # Build context for the AI
        completed_list = ', '.join([c.get('course_code', '') for c in completed_requirements]) or 'None yet'
        missing_list = ', '.join([f"{c.get('course_code', '')} (take {c.get('can_be_satisfied_by', 'N/A')})" for c in missing_requirements]) or 'None - all complete!'
        course_list = ', '.join([f"{c.get('course_code', '')} ({c.get('grade', 'N/A')})" for c in student_courses[:15]])
        
        prompt = f"""You are a helpful academic advisor. Be brief and direct.

STUDENT: {detected_college or 'CC'} → {target_major} at {target_university}
GPA: {gpa} | Progress: {progress_percentage}%
Completed: {completed_list}
Needed: {missing_list}

Give a SHORT response (max 150 words total) with these sections:

**Nice work** - One sentence compliment about their progress.

**Next steps** - 2-3 bullet points of specific actions (which courses to take, what to do).

**Tip** - One practical tip about transferring to {target_university}.

Keep it brief, no emojis, no fluff. Be specific to their situation."""

        # Make request to OpenRouter API
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Transfer Advisor"
        }
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 300
        }
        
        api_response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )
        
        if api_response.status_code != 200:
            error_msg = api_response.json().get('error', {}).get('message', 'Unknown error')
            return jsonify({'error': f'AI API error: {error_msg}'}), 500
        
        response_data = api_response.json()
        recommendation_text = response_data['choices'][0]['message']['content'].strip()
        
        return jsonify({
            'recommendations': recommendation_text,
            'success': True
        })
        
    except Exception as e:
        print(f"[ERROR] Recommendations generation failed: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)

