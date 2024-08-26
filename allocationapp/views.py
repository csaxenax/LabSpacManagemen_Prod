
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views  import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
import traceback
from datetime import datetime
import json
import traceback,requests
import os,re
from collections import defaultdict
import urllib3 
import logging
from .UserAuthentication import GetUserData
from django.db.models import Max
import sys
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
from .serializers import BoardAllocationDataModelSerializer,BroadcastSerializer
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)
logger= logging.getLogger('django')
logger_error = logging.getLogger('error_logger')

# Local imports
from .models import AllocationDetailsModel,LabModel,ProgramsModel,\
                    VendorsModel,TeamsModel,SkuModel,UserModel, \
                        UserRolesModel,UserRequestModel,SuggestionsModel,ApproverUserModel,BoardAllocationDataModel,BroadcastModel,FunctionModel
from .mail import Email,UserModuleMail,SuggestionsMail,BroadcastMail

from .ldapvalidate import validate_user_mail
# Create your views here.

FROM = 'LabSpaceManager@intel.com'
CC=[]
TO = []
#-------------------HOME PAGE VIEWS ---------------------------#
class LPVSummaryView(APIView):
    """
        This View Used for fetching Program , Lab and Vendor Summary in Home Page
    """
    def post(self,request,slug):
        if slug == "Location":
            try:
                team = request.data.get('team', None)
                is_all_teams = team == 'CCG'
                lab_filter_query = LabModel.objects.filter().values('Name')
                lab_filter_query_list = [each_query['Name'] for each_query in lab_filter_query if "TOE" not in each_query['Name']]
                lab_data = LabModel.objects.filter(Name__in=lab_filter_query_list).values()
                locations = sorted(list(set([ '-'.join(str(each_lab['Name']).split('-')[0:2])   for each_lab in lab_data])))
                category_list = ["Allocated","Unallocated"]
                master_list = []
                for each_category in category_list:
                    master_dict ={}
                    master_count = 0
                    breakdown_list=[]
                    for each_location in locations:
                        lab_data = LabModel.objects.filter(Name__icontains=each_location)
                        breakdown_dict = {}
                        counts = 0
                        for each_lab in lab_data:
                            if each_lab.BenchDetails is not None:
                                for each_row_no in range(len(each_lab.BenchDetails)):
                                    for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == team or is_all_teams and each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] != 'Non-SIV':
                                            rack_detail = each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['RackDetail']
                                            if each_category == 'Allocated':
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated']==True:
                                                    counts += 1
                                                    master_count += 1
                                                if rack_detail:
                                                    rack_details_count = sum(1 for rack_details in rack_detail if rack_details.get('IsAllocated'))
                                                    counts += rack_details_count
                                                    master_count += rack_details_count
                                            elif each_category == 'Unallocated':
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                                    each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
                                                    counts += 1
                                                    master_count += 1
                                                elif each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                                    each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "PSE":
                                                    counts += 1
                                                    master_count += 1
                                                elif each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                                    each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "CLSS":
                                                    counts += 1
                                                    master_count += 1
                                                elif each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                                    each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "C4S":
                                                    counts += 1
                                                    master_count += 1
                        if counts!=0:
                            breakdown_dict['category'] = each_location
                            breakdown_dict['value']= counts
                            breakdown_list.append(breakdown_dict)
                    if breakdown_list:
                        master_dict['category'] = each_category
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        master_list.append(master_dict)
                return Response({"Location":master_list},status=status.HTTP_200_OK)
            except Exception as e:
                logger_error.error(str(e))
                return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        elif slug == "Program":
            try:
                """
                    Returns the Counts for Program/Team chart
                """
                team = request.data.get('team', None)
                is_all_teams = team == 'CCG'
                sku_list = SkuModel.objects.select_related('ProgramName__ProgramShortName').filter().values('ProgramName__ProgramShortName')
                program_sku_list = [each_program_sku['ProgramName__ProgramShortName'] for each_program_sku in sku_list]
                program_sku_list = [*set(program_sku_list)]
                filtered_program_sku_list = program_sku_list.copy()
                program_sku_list.insert(0, "All")
                
                teams_list = TeamsModel.objects.filter().values()
                teams_list = sorted(list(set([each_team['TeamName'] for each_team in teams_list])))
                lab_data = LabModel.objects.filter()
                # Calclate the counts
                master_list = []
                for each_program_sku in program_sku_list:
                    if each_program_sku=="All":
                        master_dict = {}
                        breakdown_list = []
                        master_count =  0
                        for each_team in teams_list:
                            breakdown_dict = {}
                            for each_filtered_program_sku  in filtered_program_sku_list:
                                breakdown_dict[each_filtered_program_sku] = 0
                                filter_program = each_filtered_program_sku
                                
                                for each_lab in lab_data:
                                    if (each_lab.BenchDetails is not None) and ("TOE" not in each_lab.Name):
                                        for each_row_no in range(len(each_lab.BenchDetails)):
                                            for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == team or is_all_teams and each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] != 'Non-SIV':
                                                    rack_detail = each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['RackDetail']
                                                    if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == filter_program and \
                                                                each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Team'] == each_team:
                                                            breakdown_dict[each_filtered_program_sku] += 1
                                                            master_count += 1
                                                        # if rack_detail:
                                                        #     for rack in rack_detail:
                                                        #         if rack['AllocationData']:
                                                        #             allocation = rack['AllocationData'][0]
                                                        #             if allocation['Team'] == each_team and allocation['Program'] == filter_program:
                                                        #                 breakdown_dict[each_filtered_program_sku] += 1
                                                        #                 master_count += 1
                                if  breakdown_dict[each_filtered_program_sku] == 0:
                                    breakdown_dict.pop(each_filtered_program_sku)
                            if breakdown_dict:
                                breakdown_dict['category'] = each_team
                                breakdown_list.append(breakdown_dict)
                        if breakdown_list:
                            master_dict['category'] = each_program_sku
                            master_dict['value'] = master_count
                            master_dict['breakdown'] = breakdown_list
                            master_list.append(master_dict)
                    else:
                        program = str(each_program_sku)
                        master_dict = {}
                        master_count = 0
                        
                        breakdown_list=[]
                        lab_data = LabModel.objects.filter()
                        for each_team in teams_list:
                            breakdown_dict = {}
                            breakdowncount = 0
                            for each_lab in lab_data:
                                if (each_lab.BenchDetails is not None) and ("TOE" not in each_lab.Name):
                                    for each_row_no in range(len(each_lab.BenchDetails)):
                                        for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == team or is_all_teams and each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] != 'Non-SIV':
                                                rack_detail = each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['RackDetail']
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                    if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == program and \
                                                        each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Team'] == each_team:
                                                        breakdowncount += 1
                                                        master_count += 1
                                                # if rack_detail:
                                                #     for rack in rack_detail:
                                                #         if rack['AllocationData']:
                                                #             allocation = rack['AllocationData'][0]
                                                #             if allocation['Team'] == each_team and allocation['Program'] == program:
                                                #                 breakdowncount += 1
                                                #                 master_count += 1
                            if breakdowncount != 0:
                                breakdown_dict['category'] = each_team
                                breakdown_dict['value'] = breakdowncount
                                breakdown_list.append(breakdown_dict)
                        if breakdown_list:
                            master_dict['category'] = each_program_sku
                            master_dict['value'] = master_count
                            master_dict['breakdown'] = breakdown_list
                            master_list.append(master_dict)


                return Response(master_list,status=status.HTTP_200_OK)
            except Exception as e:
                logger_error.error(str(e))
                return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        elif slug == "Vendor":
            """
                Returns the counts for Vendor/Location chart
            """
            vendor_dict = {}
            category_list = ["All","Non-SIV","Allocated","Free"]
            try:
                teams = request.data.get('team', None)
                is_all_teams = teams == 'CCG'

                # Fetch all lab names
                lab_data = LabModel.objects.values_list('Name', 'BenchDetails')

                # Filter and exclude lab names containing "TOE"
                lab_names_list = sorted(set(['-'.join(str(name).split('-')[0:2]) for name, bench_details in lab_data if bench_details and not any("TOE" in str(name) for name in bench_details)]))

                # Fetch distinct program names
                vendor_query = VendorsModel.objects.filter().values()
                vendor_names_list = list(set([each_vendor['VendorName'] for each_vendor in vendor_query]))
                filtered_vendor_names_list = vendor_names_list.copy()
                vendor_names_list.insert(0, "All")

                # Fetch all allocation data once
                allocation_data = AllocationDetailsModel.objects.filter(status='allocated').select_related('Location').values(
                    'id', 'Program', 'Sku', 'Team', 'Function', 'Vendor', 'FromWW', 'ToWW', 'Duration', 'AllocatedTo', 'Remarks', 'approvedBy', 'Location__Name', 'BenchData',
                    'Function', 'Department'
                )

                # Initialize data structures
                bench_labels = set()
                all_breakdown_dict = defaultdict(lambda: defaultdict(int))
                all_report = []

                # Process bench details and populate all_breakdown_dict and bench_labels
                for each_location in lab_names_list:
                    for name, bench_details in lab_data:
                        if name.startswith(each_location) and bench_details:
                            for row in bench_details:
                                for seat in row.get('seats', []):
                                    if seat['team'] == teams or (is_all_teams and seat['team'] != 'Non-SIV'):
                                        label_no = seat.get('labelNo')
                                        if seat.get('AllocationData'):
                                            program = seat['AllocationData'][0]['Vendor']
                                            all_breakdown_dict[each_location][program] += 1
                                            if label_no:
                                                bench_labels.add((label_no, name))

                # Filter all_breakdown_dict to include only vendors present in vendor_names_list
                filtered_all_breakdown_dict = {
                    location: {program: count for program, count in breakdown.items() if program in vendor_names_list}
                    for location, breakdown in all_breakdown_dict.items()
                }

                # Create "All" category entry in master_list
                all_value = sum(filtered_all_breakdown_dict[location][program] for location in filtered_all_breakdown_dict for program in filtered_all_breakdown_dict[location])

                all_breakdown = [
                    {
                        'category': location,
                        **{program: filtered_all_breakdown_dict[location][program] for program in filtered_all_breakdown_dict[location]}
                    }
                    for location in filtered_all_breakdown_dict
                ]

                # Ensure vendor_names_list order is preserved and "All" category is first
                vendor_names_list.insert(0, 'All')

                all_report = [
                    allocation for allocation in allocation_data
                    if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
                ]

                all_master_dict = {
                    'category': "All",
                    'value': all_value,
                    'breakdown': all_breakdown,
                    'Report': all_report
                }
                master_list = [all_master_dict]

                # Process each vendor and populate master_list
                for each_program_vendor in filtered_vendor_names_list:
                    if each_program_vendor == "All":
                        continue  # Skip processing "All" vendor

                    program_breakdown_dict = defaultdict(int)
                    filtered_allocation_data = []

                    for each_location in lab_names_list:
                        for name, bench_details in lab_data:
                            if name.startswith(each_location) and bench_details:
                                for row in bench_details:
                                    for seat in row.get('seats', []):
                                        if seat['team'] == teams or (is_all_teams and seat['team'] != 'Non-SIV'):
                                            label_no = seat.get('labelNo')
                                            if seat.get('AllocationData') and seat['AllocationData'][0]['Vendor'] == each_program_vendor:
                                                program_breakdown_dict[each_location] += 1
                                                if label_no:
                                                    bench_labels.add((label_no, name))

                    # Filter allocation data for this specific vendor
                    filtered_allocation_data = [
                        allocation for allocation in allocation_data
                        if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
                        and allocation['Vendor'] == each_program_vendor
                    ]

                    if sum(program_breakdown_dict.values()) > 0:
                        program_master_dict = {
                            'category': each_program_vendor,
                            'value': sum(program_breakdown_dict.values()),
                            'breakdown': [
                                {'category': location, 'value': program_breakdown_dict[location]}
                                for location in program_breakdown_dict
                            ],
                            'Report': filtered_allocation_data
                        }
                        master_list.append(program_master_dict)

                return Response(master_list, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(str(e))
                logger.error(traceback.format_exc())
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LabWiseSummaryView(APIView):
    """
        This View gives the Labwise Allocated and Free Counts
    """
    def post(self, request):
        data = request.data
        try:
            lab = data['LabName']
            program = data['Program']
            if program != "All":
                program = str(data['Program']).split('-')[0]
                sku = str(data['Program']).split('-')[1]
            else:
                sku=" "
            vendor = data['Vendor']

            if program == "All":
                program_filter = "All"
            else:
                program_filter = program
            
            if vendor == "All":
                vendor_filter = "All"
            else:
                vendor_filter = vendor
            lab_data = LabModel.objects.filter(Q(Name__icontains=lab)).values()
            lab_names_list = [ '-'.join(str(each_lab['Name']).split('-')[2:])   for each_lab in lab_data]
            response_data = []
            for each_lab_name in lab_names_list:
                for each_lab in lab_data:
                    allocated_counts=0
                    free_counts=0
                    temp_dict = {}
                    if (each_lab_name == "-".join(str(each_lab['Name']).split('-')[2:])) and \
                        (each_lab['BenchDetails'] is not None):
                        temp_dict['Category'] = each_lab_name
                        for each_row_no in range(len(each_lab['BenchDetails'])):
                            for each_column_no in range(len(each_lab['BenchDetails'][each_row_no]['seats'])):
                                if (each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['AllocationData'] is None) and \
                                    each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['team'] in ['SIV','Non-SIV']:
                                    free_counts += 1
                                if each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['AllocationData']:
                                    if program_filter == "All" and vendor_filter=="All":
                                        allocated_counts+= 1
                                    elif program_filter == "All" and vendor_filter != "All":
                                        if each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['AllocationData'][0]['Vendor'] == vendor:
                                            allocated_counts+= 1
                                    elif program_filter != "All" and vendor_filter == "All":
                                        if (each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['AllocationData'][0]['Program'] == program) and \
                                            (each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['AllocationData'][0]['SKU'] == sku):
                                            
                                            allocated_counts += 1
                                    elif program_filter != "All" and vendor_filter != "All":
                                        if (each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['AllocationData'][0]['Vendor'] == vendor) and \
                                            (each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['AllocationData'][0]['Program'] == program) and \
                                            (each_lab['BenchDetails'][each_row_no]['seats'][each_column_no]['AllocationData'][0]['SKU'] == sku):
                                            allocated_counts += 1
                        
                        temp_dict["Allocated"] = allocated_counts
                        temp_dict['Free'] = free_counts
                        response_data.append(temp_dict)
            return Response({"Location":response_data},status= status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)   

class GetDrillDownChartData(APIView):
    def post(self, request):
        """ API to get the drill down data for home page location vs counts (Allocated, Free, Non-SIV) chart """
        try:
            team = request.data.get('team', None)
            is_all_teams = team == 'CCG'
            category_list = ["All", "Allocated", "Free"]
            lab_filter_query = LabModel.objects.filter().values('Name')
            lab_filter_query_list = [each_query['Name'] for each_query in lab_filter_query if "TOE" not in each_query['Name']]
            lab_data = LabModel.objects.filter(Name__in=lab_filter_query_list).values('Name')
            lab_names_list = sorted(list(set(['-'.join(str(each_lab['Name']).split('-')[0:2]) for each_lab in lab_data])))
            master_list = []
            allocation_data = AllocationDetailsModel.objects.filter(status="allocated").order_by('-created').values(
                'id', 'Program', 'Sku', 'Vendor', 'FromWW', 'ToWW', "Duration", "AllocatedTo", "NumberOfbenches", "Remarks",
                "Team", "Location__Name", "BenchData", "approvedBy", "Function","Department"
            )
            if is_all_teams:
                teams = set()
                labs_dict = {name: {} for name in lab_names_list}
                all_breakdown = {name: {'PV': 0, 'PSE': 0, 'CLSS': 0, 'C4S': 0} for name in lab_names_list}
                all_teams = ['CLSS', 'C4S', 'PSE', 'PV']

                def resolve_team_name(team_name):
                    return 'PV' if team_name == 'SIV' else team_name

                # Consolidate lab data fetch
                lab_data_all = LabModel.objects.all()  # Fetch all LabModel objects once

                for each_location in lab_names_list:
                    filtered_lab_data = lab_data_all.filter(Name__icontains=each_location)  # Filter for each_location
                    
                    for each_lab in filtered_lab_data:
                        if each_lab.BenchDetails is None or "TOE" in each_lab.Name or "SRR-1-CRD-15-VPG_LINUX" in each_lab.Name:
                            continue
                        for each_row in each_lab.BenchDetails:
                            for seat in each_row['seats']:
                                team_name = seat['team']
                                if team_name and (team_name == team or is_all_teams) and team_name not in ['Non-SIV', 'Piller']:
                                    team_name = resolve_team_name(team_name)
                                    teams.add(team_name)
                                    labs_dict[each_location].setdefault(team_name, {'free': 0, 'allocated': 0})
                                    if seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                        labs_dict[each_location][team_name]['allocated'] += 1
                                    elif seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                        labs_dict[each_location][team_name]['free'] += 1
                                    if seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                            all_breakdown[each_location][team_name] += 1

                master_list = []
                for each_team in all_teams:
                    master_dict = {'category': each_team, 'value': 0, 'breakdown': [], 'Report': [{"Allocated": [], "Free": []}]}
                    breakdown_list = []
                    master_count = 0
                    free_report = {}
                    allocated_bench_labels = set()
                    bench_labels = set()
                    relevant_labs = set()

                    for each_location in lab_names_list:
                        counts = labs_dict[each_location]
                        team_counts = counts.get(each_team, {'free': 0, 'allocated': 0})
                        count = team_counts['free'] + team_counts['allocated']
                        master_count += count
                        breakdown_list.append({'category': each_location, 'value': count})

                        free_report_lab_dict = {}
                        for each_lab in lab_data_all:
                            if each_lab.BenchDetails is None or "TOE" in each_lab.Name or "SRR-1-CRD-15-VPG_LINUX" in each_lab.Name:
                                continue
                            if each_lab.Name.lower().find(each_location.lower()) != -1:
                                for each_row in each_lab.BenchDetails:
                                    for seat in each_row['seats']:
                                        if seat['team'] == each_team or (each_team == 'PV' and seat['team'] == 'SIV'):
                                            label_no = seat['labelNo']
                                            lab_name = each_lab.Name
                                            if not seat['IsAllocated'] and seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                                free_report_lab_dict.setdefault(each_lab.Name, []).append(label_no)
                                            # print(f"Debug: seat['labelNo'] = {seat.get('labelNo')}")
                                            if seat.get('IsAllocated') and label_no and seat.get('labelNo') != 'A16-Rack':
                                                bench_labels.add((label_no, lab_name))
                                                # print(f"After Debug: seat['labelNo'] = {seat.get('labelNo')}")
                                                # bench_labels.add(label_no)
                                                # relevant_labs.add(each_lab.Name)

                        if each_location not in free_report:
                            free_report[each_location] = []
                        for lab_name, labels in free_report_lab_dict.items():
                            free_report[each_location].append({lab_name: labels})

                    master_dict['value'] = master_count
                    master_dict['breakdown'] = breakdown_list
                    allocated_data = []
                    for allocation in allocation_data:
                        if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData']):
                            filtered_allocation = {
                                key: value for key, value in allocation.items() if key != 'BenchData'
                            }
                            filtered_allocation['BenchData'] = [bench for bench in allocation['BenchData'] if bench != 'A16-Rack' and 'Rack' not in bench]
                            allocated_data.append(filtered_allocation)
                    if master_count > 0:
                        master_dict['Report'][0]['Free'] = [free_report]
                        master_dict['Report'][0]['Allocated'] = allocated_data

                    master_list.append(master_dict)

                all_dict = {'category': 'All', 'value': 0, 'breakdown': [], 'Report': [{'Allocated': [], 'Free': []}]}
                all_free_report = {}
                all_count = 0

                for each_location, counts in all_breakdown.items():
                    breakdown_entry = {'category': each_location}
                    breakdown_entry.update(counts)
                    all_dict['breakdown'].append(breakdown_entry)
                    all_count += sum(counts.values())

                    free_report_lab_dict = {}
                    for each_lab in lab_data_all:
                        if each_lab.BenchDetails is None or "TOE" in each_lab.Name or "SRR-1-CRD-15-VPG_LINUX" in each_lab.Name:
                            continue
                        if each_lab.Name.lower().find(each_location.lower()) != -1:
                            for each_row in each_lab.BenchDetails:
                                for seat in each_row['seats']:
                                    team_name = seat['team']
                                    team_name = seat['team']
                                    if team_name == 'SIV':
                                        team_name = 'PV'
                                    if team_name in all_teams and  seat['team'] != 'Non-SIV':
                                        label_no = seat['labelNo']
                                        if not seat['IsAllocated']:
                                            if seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                                free_report_lab_dict.setdefault(each_lab.Name, []).append(seat['labelNo'])
                                        is_allocated = seat['IsAllocated']
                                        if seat.get('IsAllocated') and label_no and seat.get('labelNo') != 'A16-Rack':
                                            bench_labels.add((label_no, lab_name))
                                            print(f"After Debug: seat['labelNo'] = {seat.get('labelNo')} {each_lab.Name} ")
                                                
                                    # team_name = resolve_team_name(team_name)
                                    # if team_name in all_teams and  seat['team'] != 'Non-SIV':
                                    #     label_no = seat['labelNo']
                                    #     if not seat['IsAllocated'] and seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                    #         free_report_lab_dict.setdefault(each_lab.Name, []).append(label_no)
                
                    if each_location not in all_free_report:
                        all_free_report[each_location] = []
                    for lab_name, labels in free_report_lab_dict.items():
                        all_free_report[each_location].append({lab_name: labels})

                allocated_data = []
                # `for allocation in allocation_data:
                #     if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData']):
                #             filtered_allocation = {
                #                 key: value for key, value in allocation.items() if key != 'BenchData'
                #             }
                #             filtered_allocation['BenchData'] = [bench for bench in allocation['BenchData'] if bench != 'A16-Rack']
                #             allocated_data.append(filtered_allocation)`
                for team_report in master_list:
                    allocated_data.extend(team_report['Report'][0]['Allocated'])
                all_dict['value'] = all_count
                all_dict['Report'][0]['Free'] = [all_free_report]
                all_dict['Report'][0]['Allocated'] = allocated_data
                master_list.insert(0, all_dict)

            else:
                for each_category in category_list:
                    master_dict = {'category': each_category, 'value': 0, 'breakdown': []}
                    breakdown_list = []
                    report_list = []
                    report_dict = {}
                    master_count = 0
                    bench_labels = set()
                    if each_category == "All":
                        # Initialize report_dict keys
                        report_dict['Allocated'] = []
                        report_dict['Free'] = []
                        free_report_dict = {}
                       
                        for each_location in lab_names_list:
                            lab_data = LabModel.objects.filter(Name__icontains=each_location)
                            counts_dict = {}
                            if each_location not in free_report_dict:
                                free_report_dict[each_location] = []
                            non_siv_count = 0
                            allocated_count = 0
                            free_count = 0
                            pse_count = 0
                            clss_count = 0
                            c4s_count = 0
                            free_report_lab_dict = {}
                            non_siv_report_lab_dict = {}
                            
                            for each_lab in lab_data:
                                if each_lab.BenchDetails is not None and "TOE" not in each_lab.Name and "SRR-1-CRD-15-VPG_LINUX" not in each_lab.Name:
                                    if each_lab.Name not in free_report_lab_dict:
                                        free_report_lab_dict[each_lab.Name] = []

                                    for each_row_no in range(len(each_lab.BenchDetails)):
                                        for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                            seat = each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]
                                            if seat['team'] == team: 
                                                is_allocated = seat['IsAllocated']
                                                label_no = seat['labelNo']
                                                lab_name = each_lab.Name
                                                rack_details = seat['RackDetail']
                                                if is_allocated and seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                                    allocated_count += 1
                                                    master_count += 1
                                                    if label_no:
                                                        if label_no != 'A16-Rack':
                                                            bench_labels.add((label_no, lab_name))
                                                        
                                                if not seat['IsAllocated']:
                                                    if seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                                        free_count += 1
                                                        # print("free_count",free_count)
                                                        master_count += 1
                                                        free_report_lab_dict.setdefault(each_lab.Name, []).append(seat['labelNo'])
                            if free_report_lab_dict:
                                free_report_dict[each_location].append(free_report_lab_dict)

                            counts_dict['category'] = each_location
                            counts_dict['Allocated'] = allocated_count
                            counts_dict['Free'] = free_count + pse_count + clss_count + c4s_count
                            breakdown_list.append(counts_dict)

                        report_dict['Free'].append(free_report_dict)
                        report_list.append(report_dict)

                        allocated_data = []
                        for allocation in allocation_data:
                            if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData']):
                                    filtered_allocation = {
                                        key: value for key, value in allocation.items() if key != 'BenchData'
                                    }
                                    filtered_allocation['BenchData'] = [bench for bench in allocation['BenchData'] if bench != 'A16-Rack' and not bench.startswith('Rack')]
                                    allocated_data.append(filtered_allocation)
                        if allocated_data:
                            report_dict['Allocated'] = allocated_data

                        if breakdown_list:
                            master_dict['value'] = master_count
                            master_dict['breakdown'] = breakdown_list
                        if report_list:
                            master_dict['Report'] = report_list
                        if master_count > 0:
                            master_list.append(master_dict)

                    else:
                        if each_category == "Allocated":
                            for each_location in lab_names_list:
                                lab_data = LabModel.objects.filter(Name__icontains=each_location)
                                location_allocated_count = 0  # Initialize count for each location
                                
                                for each_lab in lab_data:
                                    if each_lab.BenchDetails is not None and "TOE" not in each_lab.Name and "SRR-1-CRD-15-VPG_LINUX" not in each_lab.Name:
                                        lab_bench_labels = set()
                                        for each_row_no in range(len(each_lab.BenchDetails)):
                                            for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                                seat = each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]
                                                if seat['team'] == team:
                                                    is_allocated = seat['IsAllocated']
                                                    label_no = seat['labelNo']
                                                    lab_name = each_lab.Name
                                                    if is_allocated and label_no != 'A16-Rack' and seat.get('dir') != 'Rack':
                                                        location_allocated_count += 1
                                                        master_count += 1
                                                        if label_no or label_no != 'A16-Rack':
                                                            bench_labels.add((label_no, lab_name))
                                counts_dict = {
                                    'category': each_location,
                                    'value': location_allocated_count
                                }
                                breakdown_list.append(counts_dict)
                            allocated_data = []
                            for allocation in allocation_data:
                                if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData']):
                                        filtered_allocation = {
                                            key: value for key, value in allocation.items() if key != 'BenchData'
                                        }
                                        filtered_allocation['BenchData'] = [bench for bench in allocation['BenchData'] if bench != 'A16-Rack' and not bench.startswith('Rack')]
                                        allocated_data.append(filtered_allocation)
                            # print(f"Filtered Allocation Data for {each_category}: {filtered_allocation_data}")
                            
                            master_dict['Report'] = allocated_data

                        else:
                            report_dict = {}
                            for each_location in lab_names_list:
                                psecount = 0
                                clsscount = 0
                                c4scount = 0
                                report_category_dict = {}
                                if each_category != "Allocated":
                                    if each_location not in report_dict.keys():
                                        report_dict[each_location] = []
                                lab_data = LabModel.objects.filter(Name__icontains=each_location)
                                counts_dict = {}
                                count = 0

                                for each_lab in lab_data:
                                    if each_lab.BenchDetails is not None and "TOE" not in each_lab.Name and "SRR-1-CRD-15-VPG_LINUX" not in each_lab.Name:
                                        if each_lab.Name not in report_category_dict:
                                            report_category_dict[each_lab.Name] = []
                                        for each_row_no in range(len(each_lab.BenchDetails)):
                                            for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                                seat = each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]
                                                if seat['team'] == team:
                                                    if each_category == 'Free' and not seat['IsAllocated']:
                                                        if seat.get('dir') != 'Rack' and seat.get('labelNo') != 'A16-Rack':
                                                            count += 1
                                                            master_count += 1
                                                            report_category_dict.setdefault(each_lab.Name, []).append(seat['labelNo'])

                                counts_dict["category"] = each_location
                                counts_dict["value"] = count + psecount + clsscount+c4scount
                                if each_category != "Allocated":
                                    report_dict[each_location].append(report_category_dict)
                                breakdown_list.append(counts_dict)

                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        if each_category != "Allocated":
                            master_dict['Report'] = report_dict
                        if master_count >= 0:
                            master_list.append(master_dict)

            return Response(master_list, status=status.HTTP_200_OK)
        except Exception as e:
            print(traceback.format_exc())
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class TeamDrillDownView(APIView):
    def post(self, request):
        try:
            teams = request.data.get('team', None)
            is_all_teams = teams == 'CCG'
            
            # Fetch all lab names
            lab_data = LabModel.objects.values_list('Name', 'BenchDetails')
            
            # Filter and exclude lab names containing "TOE"
            lab_names_list = sorted(set(['-'.join(str(name).split('-')[0:2]) for name, bench_details in lab_data if bench_details and not any("TOE" in str(name) for name in bench_details)]))
            
            # Fetch distinct program names
            teams_list = TeamsModel.objects.filter().values('TeamName')
            teams_list = sorted(list(set([each_team['TeamName'] for each_team in teams_list])))
            print("team_list",teams_list)
            filtered_teams_list = teams_list.copy()
            teams_list.insert(0, 'All')
            
            # Fetch all allocation data once
            allocation_data = AllocationDetailsModel.objects.filter(status='allocated').select_related('Location').values(
                'id', 'Program', 'Sku', 'Team', 'Function', 'Vendor', 'FromWW', 'ToWW', 'Duration', 'AllocatedTo', 'Remarks', 'approvedBy', 'Location__Name', 'BenchData',
                'Function', 'Department'
            )
            
            # Initialize data structures
            bench_labels = set()
            all_breakdown_dict = defaultdict(lambda: defaultdict(int))
            all_report = []

            # Process bench details and populate all_breakdown_dict and bench_labels
            for each_location in lab_names_list:
                for name, bench_details in lab_data:
                    if name.startswith(each_location) and bench_details:
                        for row in bench_details:
                            for seat in row.get('seats', []):
                                if seat['team'] == teams or (is_all_teams and seat['team'] != 'Non-SIV'):
                                    label_no = seat.get('labelNo')
                                    if seat.get('AllocationData'):
                                        program = seat['AllocationData'][0]['Team']
                                        all_breakdown_dict[each_location][program] += 1
                                        if label_no:
                                            bench_labels.add((label_no, name))

            # Filter all_breakdown_dict to include only teams present in teams_list
            filtered_all_breakdown_dict = {
                location: {program: count for program, count in breakdown.items() if program in teams_list}
                for location, breakdown in all_breakdown_dict.items()
            }

            # Create "All" category entry in master_list
            all_value = sum(filtered_all_breakdown_dict[location][program] for location in filtered_all_breakdown_dict for program in filtered_all_breakdown_dict[location])

            all_breakdown = [
                {
                    'category': location,
                    **{program: filtered_all_breakdown_dict[location][program] for program in filtered_all_breakdown_dict[location]}
                }
                for location in filtered_all_breakdown_dict
            ]

            # Ensure teams_list order is preserved and "All" category is first
            teams_list.insert(0, 'All')
            all_report = [
                allocation for allocation in allocation_data
                if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
            ]
            
            all_master_dict = {
                'category': "All",
                'value': all_value,
                'breakdown': all_breakdown,
                'Report': all_report
            }
            master_list = [all_master_dict]
            
            # Process each program sku and populate master_list
            for each_program_sku in filtered_teams_list:
                if each_program_sku == "All":
                    continue  # Skip processing "All" program
                
                program_breakdown_dict = defaultdict(int)
                filtered_allocation_data = []
                
                for each_location in lab_names_list:
                    for name, bench_details in lab_data:
                        if name.startswith(each_location) and bench_details:
                            for row in bench_details:
                                for seat in row.get('seats', []):
                                    if seat['team'] == teams or (is_all_teams and seat['team'] != 'Non-SIV'):
                                        label_no = seat.get('labelNo')
                                        if seat.get('AllocationData') and seat['AllocationData'][0]['Team'] == each_program_sku:
                                            program_breakdown_dict[each_location] += 1
                                            if label_no:
                                                bench_labels.add((label_no, name))
                
                # Filter allocation data for this specific program
                filtered_allocation_data = [
                    allocation for allocation in allocation_data
                    if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
                    and allocation['Team'] == each_program_sku
                ]
                
                if sum(program_breakdown_dict.values()) > 0:
                    program_master_dict = {
                        'category': each_program_sku,
                        'value': sum(program_breakdown_dict.values()),
                        'breakdown': [
                            {'category': location, 'value': program_breakdown_dict[location]}
                            for location in program_breakdown_dict
                        ],
                        'Report': filtered_allocation_data
                    }
                    master_list.append(program_master_dict)
            
            return Response(master_list, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(str(e))
            print(traceback.format_exc())
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ProgramDrillDownView(APIView):
    def post(self, request):
        try:
            teams = request.data.get('team', None)
            is_all_teams = teams == 'CCG'
            
            # Fetch all lab names
            lab_data = LabModel.objects.values_list('Name', 'BenchDetails')
            
            # Filter and exclude lab names containing "TOE"
            lab_names_list = sorted(set(['-'.join(str(name).split('-')[0:2]) for name, bench_details in lab_data if bench_details and not any("TOE" in str(name) for name in bench_details)]))
            
            # Fetch distinct program names
            sku_list = SkuModel.objects.select_related('ProgramName__ProgramShortName').filter().values('ProgramName__ProgramShortName')
            program_sku_list = [each_program_sku['ProgramName__ProgramShortName'] for each_program_sku in sku_list]
            program_sku_list = [*set(program_sku_list)]
            filter_program_sku_list = program_sku_list.copy()
            program_sku_list.insert(0, "All")
            # Fetch all allocation data once
            allocation_data = AllocationDetailsModel.objects.filter(status='allocated').select_related('Location').values(
                'id', 'Program', 'Sku', 'Team', 'Function', 'Vendor', 'FromWW', 'ToWW', 'Duration', 'AllocatedTo', 'Remarks', 'approvedBy', 'Location__Name', 'BenchData',
                'Function', 'Department'
            )
            
            # Initialize data structures
            bench_labels = set()
            all_breakdown_dict = defaultdict(lambda: defaultdict(int))
            all_report = []
            
            # Process bench details and populate all_breakdown_dict and bench_labels
            for each_location in lab_names_list:
                for name, bench_details in lab_data:
                    if name.startswith(each_location) and bench_details:
                        for row in bench_details:
                            for seat in row.get('seats', []):
                                if seat['team'] == teams or (is_all_teams and seat['team'] != 'Non-SIV'):
                                    label_no = seat.get('labelNo')
                                    if seat.get('AllocationData'):
                                        program = seat['AllocationData'][0]['Program']
                                        if program != "ADL,RPL,MTL,ARL,LNL...":
                                            all_breakdown_dict[each_location][program] += 1
                                            if label_no and program != "ADL,RPL,MTL,ARL,LNL...":
                                                bench_labels.add((label_no, name))
            
            # Create "All" category entry in master_list
            all_value = sum(all_breakdown_dict[location][program] for location in all_breakdown_dict for program in all_breakdown_dict[location])
            all_breakdown = []
            for location in all_breakdown_dict:
                breakdown_entry = {
                    'category': location,
                    **{program: count for program, count in all_breakdown_dict[location].items() if program != "ADL,RPL,MTL,ARL,LNL..."}
                }
                all_breakdown.append(breakdown_entry)
            all_report = [
                allocation for allocation in allocation_data
                if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
            ]
            
            all_master_dict = {
                'category': "All",
                'value': all_value,
                'breakdown': all_breakdown,
                'Report': all_report
            }
            master_list = [all_master_dict]
            
            # Process each program sku and populate master_list
            for each_program_sku in program_sku_list:
                if each_program_sku == "All":
                    continue  # Skip processing "All" program
                
                program_breakdown_dict = defaultdict(int)
                filtered_allocation_data = []
                
                for each_location in lab_names_list:
                    for name, bench_details in lab_data:
                        if name.startswith(each_location) and bench_details:
                            for row in bench_details:
                                for seat in row.get('seats', []):
                                    if seat['team'] == teams or (is_all_teams and seat['team'] != 'Non-SIV'):
                                        label_no = seat.get('labelNo')
                                        if seat.get('AllocationData') and seat['AllocationData'][0]['Program'] == each_program_sku:
                                            program_breakdown_dict[each_location] += 1
                                            if label_no:
                                                bench_labels.add((label_no, name))
                
                # Filter allocation data for this specific program
                filtered_allocation_data = [
                    allocation for allocation in allocation_data
                    if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
                    and allocation['Program'] == each_program_sku
                ]
                
                if sum(program_breakdown_dict.values()) > 0:
                    program_master_dict = {
                        'category': each_program_sku,
                        'value': sum(program_breakdown_dict.values()),
                        'breakdown': [
                            {'category': location, 'value': program_breakdown_dict[location]}
                            for location in program_breakdown_dict
                        ],
                        'Report': filtered_allocation_data
                    }
                    master_list.append(program_master_dict)
            
            return Response(master_list, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(str(e))
            print(traceback.format_exc())
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class ProgramDrillDownView(APIView):
#     def get(self, request):
#         """API to get drill down data for Program vs Location chart"""
#         try:
#             lab_filter_query = LabModel.objects.filter().values('Name')
#             lab_filter_query_list = [each_query['Name'] for each_query in lab_filter_query if "TOE" not in each_query['Name']]
#             lab_data = LabModel.objects.filter(Name__in=lab_filter_query_list).values('Name')
#             lab_names_list = sorted(list(set(['-'.join(str(each_lab['Name']).split('-')[0:2]) for each_lab in lab_data])))
#             sku_list = SkuModel.objects.select_related('ProgramName__ProgramShortName').filter().values('ProgramName__ProgramShortName')
#             program_sku_list = [each_program_sku['ProgramName__ProgramShortName'] for each_program_sku in sku_list]
#             program_sku_list = [*set(program_sku_list)]
#             filter_program_sku_list = program_sku_list.copy()
#             program_sku_list.insert(0, "All")
            
#             master_list = []
#             allocation_data = AllocationDetailsModel.objects.filter(status="allocated").order_by('-created').values(
#                 'id', 'Program', 'Sku', 'Vendor', 'FromWW', 'ToWW', "Duration", "AllocatedTo", "NumberOfbenches", "Remarks",
#                 "Team", "Location__Name", "BenchData", "approvedBy")
            
#             for each_program_sku in program_sku_list:
#                 if each_program_sku == "All":
#                     master_dict = {}
#                     master_count = 0 
#                     breakdown_list = []
#                     report_data_list = [each_query for each_query in allocation_data]
                    
#                     for each_location in lab_names_list:
#                         lab_data = LabModel.objects.filter(Name__icontains=each_location)
#                         breakdown_dict = {}
#                         breakdown_dict['category'] = each_location
#                         count = 0
                        
#                         for each_filter_program_sku in filter_program_sku_list:
#                             breakdown_dict[each_filter_program_sku] = 0
#                             program = each_filter_program_sku
                            
#                             for each_lab in lab_data:
#                                 if each_lab.BenchDetails is not None and "TOE" not in each_lab.Name:
#                                     for each_row_no in range(len(each_lab.BenchDetails)):
#                                         for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
#                                             if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
#                                                 if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == program:
#                                                     breakdown_dict[each_filter_program_sku] += 1
#                                                     master_count += 1
                                                    
#                             if breakdown_dict[each_filter_program_sku] == 0:
#                                 breakdown_dict.pop(each_filter_program_sku)
#                         breakdown_list.append(breakdown_dict)
                    
#                     if breakdown_list:
#                         master_dict['category'] = str(each_program_sku)
#                         master_dict['value'] = master_count
#                         master_dict['breakdown'] = breakdown_list
#                         master_dict['Report'] = report_data_list
#                         master_list.append(master_dict)
                
#                 else:
#                     master_dict = {}
#                     master_count = 0
#                     breakdown_list = []
#                     program = each_program_sku
#                     report_data_list = [each_query for each_query in allocation_data if each_query['Program'] == program]
                    
#                     for each_location in lab_names_list:
#                         lab_data = LabModel.objects.filter(Name__icontains=each_location)
#                         breakdown_dict = {}
#                         count = 0
                        
#                         for each_lab in lab_data:
#                             if each_lab.BenchDetails is not None and "TOE" not in each_lab.Name:
#                                 for each_row_no in range(len(each_lab.BenchDetails)):
#                                     for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
#                                         if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
#                                             if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == program:
#                                                 count += 1
#                                                 master_count += 1
                                                
#                         if count != 0:
#                             breakdown_dict['category'] = each_location
#                             breakdown_dict['value'] = count
#                             breakdown_list.append(breakdown_dict)
                    
#                     if breakdown_list:
#                         master_dict['category'] = each_program_sku
#                         master_dict['value'] = master_count
#                         master_dict['breakdown'] = breakdown_list
#                         master_dict['Report'] = report_data_list
#                         master_list.append(master_dict)
            
#             return Response(master_list, status=status.HTTP_200_OK)
#         except Exception as e:
#             logger_error.error(str(e))
#             return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ProgramVendorView(APIView):
    def post(self, request):
        """
        API to get drilldown chart data for Program vs Vendor chart
        """
        try:
            team = request.data.get('team', None)
            is_all_teams = team == 'CCG'

            # Fetch and process SKUs
            sku_list = SkuModel.objects.values_list('ProgramName__ProgramShortName', flat=True).distinct()
            program_sku_list = sorted(sku_list)
            filter_program_sku_list = program_sku_list.copy()
            program_sku_list.insert(0, "All")

            # Fetch vendor list
            vendor_list = VendorsModel.objects.values_list('VendorName', flat=True).distinct()

            # Fetch lab data
            lab_data = LabModel.objects.all()

            master_list = []
            
            for each_program_sku in program_sku_list:
                master_dict = {'category': each_program_sku, 'value': 0, 'breakdown': []}
                master_count = 0
                breakdown_list = []

                relevant_programs = filter_program_sku_list if each_program_sku == "All" else [each_program_sku]

                for each_vendor in vendor_list:
                    breakdown_dict = defaultdict(int)

                    for program in relevant_programs:
                        for each_lab in lab_data:
                            if each_lab.BenchDetails and "TOE" not in each_lab.Name:
                                for row in each_lab.BenchDetails:
                                    for seat in row['seats']:
                                        if seat['team'] == team or is_all_teams and seat['team'] != 'Non-SIV':
                                            # Check AllocationData in seats
                                            if seat['AllocationData']:
                                                allocation = seat['AllocationData'][0]
                                                if allocation['Program'] == program and allocation['Vendor'] == each_vendor:
                                                    breakdown_dict[program] += 1
                                                    master_count += 1
                                            # Check AllocationData in RackDetail
                                            if seat['RackDetail']:
                                                for rack in seat['RackDetail']:
                                                    if rack['AllocationData']:
                                                        allocation = rack['AllocationData'][0]
                                                        if allocation['Program'] == program and allocation['Vendor'] == each_vendor:
                                                            breakdown_dict[program] += 1
                                                            master_count += 1

                    # Remove zero-count programs and add to breakdown_list
                    breakdown_dict = {k: v for k, v in breakdown_dict.items() if v > 0}
                    if breakdown_dict:
                        breakdown_dict['category'] = each_vendor
                        breakdown_list.append(breakdown_dict)

                if master_count > 0:  # Only add to master_list if there is relevant data
                    master_dict['value'] = master_count
                    master_dict['breakdown'] = breakdown_list
                    master_list.append(master_dict)

            return Response(master_list, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetBuildingNamesView(APIView):
    def get(self,request):
        """ List all the locations available in the database"""
        try:
            lab_data = LabModel.objects.filter().values('Name')
            building_list =list(set(['-'.join(str(each_lab['Name']).split('-')[0:2]) for each_lab in lab_data]))
            lab_list = list(set([  '-'.join(str(each_lab['Name']).split('-')[2:]) for each_lab in lab_data]))
            return Response({"Data":building_list},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetProgramSkuVendorDropdownNamesView(APIView):
    def post(self, request):
        """ Lists all the Program and Sku names available in database"""
        try:
            location = request.data['location']
            lab_data = LabModel.objects.filter(Name__icontains=location)
            vendor_list = []
            program_sku_list = []
            if lab_data:
                for each_lab_data in lab_data:
                    for each_bench_row in each_lab_data.BenchDetails:
                        for each_bench_column_no in range(len(each_bench_row['seats'])):
                            if each_bench_row['seats'][each_bench_column_no]['AllocationData'] is not None:
                                if each_bench_row['seats'][each_bench_column_no]['AllocationData'] is not None:
                                    program = each_bench_row['seats'][each_bench_column_no]['AllocationData'][0]['Program']
                                    sku = each_bench_row['seats'][each_bench_column_no]['AllocationData'][0]['SKU']
                                    program_name = str(program) + '-' + str(sku)
                                    vendor = each_bench_row['seats'][each_bench_column_no]['AllocationData'][0]['Vendor']
                                    vendor_list.append(str(vendor))
                                    program_sku_list.append(program_name)
            vendor_list = list(set(vendor_list))
            program_sku_list = list(set(program_sku_list))
            return Response({"Data":{"VendorList":vendor_list,"ProgramSkuList":program_sku_list}})
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AllocatedUserList(APIView):
    def get(self, request):
        try:
            users_list = AllocationDetailsModel.objects.filter(status='allocated').values('AllocatedTo')
            users_list = sorted(list(set([ each_team['AllocatedTo'][0]['Name'] for each_team in users_list])))
            filtered_user_list = users_list.copy()
            users_list.insert(0,'All')
            return Response({"UserList": filtered_user_list}, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserBasedLocationDrillDown(APIView):
    def post(self, request):
        try:
            team = request.data.get('team', None)
            users = request.data.get('user', 'All').split(',')
            users = [user.strip().lower() for user in users]
            is_all_teams = team == 'CCG'

            # Fetch lab names excluding those with "TOE"
            lab_filter_query = LabModel.objects.filter().values('Name')
            lab_names_list = sorted(list(set(['-'.join(str(each_lab['Name']).split('-')[0:2]) for each_lab in lab_filter_query if "TOE" not in each_lab['Name']])))

            # Fetch distinct program names
            program_sku_list = list(set(SkuModel.objects.values_list('ProgramName__ProgramShortName', flat=True)))
            program_sku_list.insert(0, "All")

            master_dict = {}
            for program_sku in program_sku_list:
                master_dict[program_sku] = {'value': 0, 'breakdown': defaultdict(int), 'Report': []}

            # Fetch allocation data to be used for report generation
            allocation_data = AllocationDetailsModel.objects.filter(status='allocated').select_related('Location').values(
                'id', 'Program', 'Sku', 'Team', 'Function', 'Vendor', 'FromWW', 'ToWW', 'Duration', 'AllocatedTo', 'Remarks', 'approvedBy', 'Location__Name', 'BenchData',
                'Function', 'Department'
            )

            bench_labels = set()
            relevant_labs = set()
            for each_location in lab_names_list:
                lab_data = LabModel.objects.filter(Name__icontains=each_location)

                for each_lab in lab_data:
                    if each_lab.BenchDetails and "TOE" not in each_lab.Name:
                        for row in each_lab.BenchDetails:
                            for seat in row['seats']:
                                label_no = seat.get('labelNo')

                                if seat['team'] == team or is_all_teams and seat['team'] != 'Non-SIV':
                                    allocation_Data = seat.get('AllocationData', [])  # Ensure allocation_data is not None
                                    if allocation_Data is not None:
                                        for alloc_data in allocation_Data:
                                            programs = alloc_data.get('Program', '').split(',')
                                            for program in programs:
                                                program = program.strip()  # Remove spaces
                                                if 'Who' in alloc_data and alloc_data['Who']:
                                                    allocated_user = alloc_data['Who'][0]['Name'].strip().lower()
                                                    if 'all' in users or allocated_user in users:
                                                        bench_data_length = 1
                                                        if label_no:
                                                            bench_labels.add((label_no, each_lab.Name))

                                                        if program in master_dict:
                                                            master_dict[program]['value'] += bench_data_length
                                                            master_dict[program]['breakdown'][each_location] += bench_data_length
                                                            master_dict['All']['value'] += bench_data_length
                                                            master_dict['All']['breakdown'][each_location] += bench_data_length

            # Filter the allocation data once based on relevant labs and bench labels
            filtered_allocation_data = [
                allocation for allocation in allocation_data
                if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
            ]

            # Distribute the filtered data to the relevant program categories
            for allocation in filtered_allocation_data:
                programs = allocation['Program'].split(',')
                for program in programs:
                    program = program.strip()  # Remove spaces
                    if program in master_dict:
                        master_dict[program]['Report'].append(allocation)
                    master_dict['All']['Report'].append(allocation)

            # Construct response data, ensuring only non-empty data is included
            master_list = [
                {
                    'category': category,
                    'value': data['value'],
                    'breakdown': [{'category': lab, 'value': count} for lab, count in data['breakdown'].items()],
                    'Report': data['Report']
                } for category, data in master_dict.items() if data['value'] > 0
            ]

            return Response(master_list, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            print(traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UserBasedTeamDrillDown(APIView):
    def post(self, request):
        try:
            team = request.data.get('team', None)
            users = request.data.get('user', 'All').split(',')
            users = [user.strip().lower() for user in users]
            is_all_teams = team == 'CCG'

            # Fetch and process SKUs
            sku_list = SkuModel.objects.values_list('ProgramName__ProgramShortName', flat=True).distinct()
            program_sku_list = sorted(sku_list)
            filter_program_sku_list = program_sku_list.copy()
            program_sku_list.insert(0, "All")

            # Fetch teams list
            teams_list = TeamsModel.objects.filter().values_list('TeamName', flat=True).distinct()
            teams_list = sorted(list(teams_list))
            filtered_teams_list = teams_list.copy()

            bench_labels = set()
            relevant_labs = set()

            # Fetch allocation data to be used for report generation
            allocation_data = AllocationDetailsModel.objects.filter(status='allocated').select_related('Location').values(
                'id', 'Program', 'Sku', 'Team', 'Function', 'Vendor', 'FromWW', 'ToWW', 'Duration', 'AllocatedTo', 'Remarks', 'approvedBy', 'Location__Name', 'BenchData', 'Function', 'Department'
            )

            # Fetch lab data
            lab_data = LabModel.objects.all()

            master_list = []

            for each_program_sku in program_sku_list:
                master_dict = {'category': each_program_sku, 'value': 0, 'breakdown': [], 'Report': []}
                master_count = 0
                breakdown_list = []

                relevant_programs = filter_program_sku_list if each_program_sku == "All" else [each_program_sku]

                for each_team in teams_list:
                    breakdown_dict = defaultdict(int)

                    for program in relevant_programs:
                        for each_lab in lab_data:
                            if each_lab.BenchDetails and "TOE" not in each_lab.Name:
                                for row in each_lab.BenchDetails:
                                    for seat in row['seats']:
                                        label_no = seat.get('labelNo')
                                        if seat['team'] == each_team or is_all_teams and seat['team'] != 'Non-SIV':
                                            # Check AllocationData in seats
                                            if seat['AllocationData']:
                                                for allocation in seat['AllocationData']:
                                                    programs = allocation.get('Program', '').split(',')
                                                    if program in programs and allocation['Team'] == each_team:
                                                        allocated_user = allocation['Who'][0]['Name'].strip().lower()
                                                        if 'all' in users or allocated_user in users:
                                                            breakdown_dict[program] += 1
                                                            master_count += 1
                                                            if label_no:
                                                                bench_labels.add((label_no, each_lab.Name))
                                                                # relevant_labs.add(each_lab.Name)

                                            # Check AllocationData in RackDetail
                                            # if seat['RackDetail']:
                                            #     for rack in seat['RackDetail']:
                                            #         label_no = rack.get('labelNo')
                                            #         shelf_no = rack.get('shelfNo')
                                            #         if rack['AllocationData']:
                                            #             allocation = rack['AllocationData'][0]
                                            #             programs = allocation.get('Program', '').split(',')
                                            #             if program in programs and allocation['Team'] == each_team:
                                            #                 allocated_user = allocation['Who'][0]['Name'].strip().lower()
                                            #                 if 'all' in users or allocated_user in users:
                                            #                     breakdown_dict[program] += 1
                                            #                     master_count += 1
                                            #                     if label_no is not None and shelf_no is not None:
                                            #                         combined_label = label_no + '-' + shelf_no
                                            #                         bench_labels.add(combined_label)
                                            #                         relevant_labs.add(each_lab.Name)

                    # Remove zero-count programs and add to breakdown_list
                    breakdown_dict = {k: v for k, v in breakdown_dict.items() if v > 0}
                    if breakdown_dict:
                        breakdown_dict['category'] = each_team
                        breakdown_list.append(breakdown_dict)

                if each_program_sku == "All":
                    filtered_allocation_data = [
                        allocation for allocation in allocation_data
                        if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
                    ]
                else:
                    filtered_allocation_data = [
                        allocation for allocation in allocation_data
                        if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
                        and allocation['Program'] in relevant_programs
                    ]

                if master_count > 0:  # Check if there is any data for this category
                    master_dict['value'] = master_count
                    master_dict['breakdown'] = breakdown_list
                    master_dict['Report'] = filtered_allocation_data
                    master_list.append(master_dict)

            return Response(master_list, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
  
class UserBasedProgramDrillDown(APIView):
    def post(self, request):
        try:
            team = request.data.get('team', None)
            users = request.data.get('user', 'All').split(',')
            users = [user.strip().lower() for user in users]
            is_all_teams = team == 'CCG'
            bench_labels = set()
            relevant_labs = set()

            # Fetch and process SKUs
            sku_list = SkuModel.objects.values_list('ProgramName__ProgramShortName', flat=True).distinct()
            program_sku_list = sorted(sku_list)
            filter_program_sku_list = program_sku_list.copy()
            program_sku_list.insert(0, "All")

            # Fetch allocation data to be used for report generation
            allocation_data = AllocationDetailsModel.objects.filter(status='allocated').select_related('Location').values(
                'id', 'Program', 'Sku', 'Team', 'Function', 'Vendor', 'FromWW', 'ToWW', 'Duration', 'AllocatedTo', 'Remarks', 'approvedBy', 'Location__Name', 'BenchData', 'Function', 'Department'
            )

            # Fetch vendor list
            vendor_list = VendorsModel.objects.values_list('VendorName', flat=True).distinct()

            # Fetch lab data
            lab_data = LabModel.objects.all()

            master_list = []

            for each_program_sku in program_sku_list:
                master_dict = {'category': each_program_sku, 'value': 0, 'breakdown': [], 'Report': []}
                master_count = 0
                breakdown_list = []

                relevant_programs = filter_program_sku_list if each_program_sku == "All" else [each_program_sku]

                for each_vendor in vendor_list:
                    breakdown_dict = defaultdict(int)

                    for program in relevant_programs:
                        for each_lab in lab_data:
                            if each_lab.BenchDetails and "TOE" not in each_lab.Name:
                                for row in each_lab.BenchDetails:
                                    for seat in row['seats']:
                                        if seat['team'] == team or is_all_teams and seat['team'] != 'Non-SIV':
                                            label_no = seat.get('labelNo')
                                            # Check AllocationData in seats
                                            if seat['AllocationData']:
                                                for allocation in seat['AllocationData']:
                                                    programs = allocation.get('Program', '').split(',')
                                                    if program in programs and allocation['Vendor'] == each_vendor:
                                                        allocated_user = allocation['Who'][0]['Name'].strip().lower()
                                                        if 'all' in users or allocated_user in users:
                                                            breakdown_dict[program] += 1
                                                            master_count += 1
                                                            if label_no:
                                                                bench_labels.add((label_no, each_lab.Name))
                                                                # relevant_labs.add(each_lab.Name)

                                            # Check AllocationData in RackDetail
                                            # if seat['RackDetail']:
                                            #     for rack in seat['RackDetail']:
                                            #         label_no = rack.get('labelNo')
                                            #         shelf_no = rack.get('shelfNo')
                                            #         if rack['AllocationData']:
                                            #             allocation = rack['AllocationData'][0]
                                            #             programs = allocation.get('Program', '').split(',')
                                            #             if program in programs and allocation['Vendor'] == each_vendor:
                                            #                 allocated_user = allocation['Who'][0]['Name'].strip().lower()
                                            #                 if 'all' in users or allocated_user in users:
                                            #                     breakdown_dict[program] += 1
                                            #                     master_count += 1
                                            #                     if label_no is not None and shelf_no is not None:
                                            #                         combined_label = f"{label_no}-{shelf_no}"
                                            #                         bench_labels.add(combined_label,ea)
                                            #                         # relevant_labs.add(each_lab.Name)

                    # Remove zero-count programs and add to breakdown_list
                    breakdown_dict = {k: v for k, v in breakdown_dict.items() if v > 0}
                    if breakdown_dict:
                        breakdown_dict['category'] = each_vendor
                        breakdown_list.append(breakdown_dict)

                # Filter allocation data based on bench labels and relevant labs
                if each_program_sku == "All":
                    filtered_allocation_data = [
                        allocation for allocation in allocation_data
                        if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
                    ]
                else:
                    filtered_allocation_data = [
                        allocation for allocation in allocation_data
                        if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData'])
                        and allocation['Program'] in relevant_programs
                    ]

                if breakdown_list:
                    if master_count > 0:
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        master_dict['Report'] = filtered_allocation_data
                        master_list.append(master_dict)

            return Response(master_list, status=status.HTTP_200_OK)

        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FunctionDrillDownView(APIView):
    def post(self, request):
        """
        API to get drilldown chart data for Program vs Function chart
        """
        try:
            team = request.data.get('team', None)
            is_all_teams = team == 'CCG'
            if team is None:
                return Response([], status=status.HTTP_200_OK)

            # Fetch and process SKUs
            sku_list = SkuModel.objects.values_list('ProgramName__ProgramShortName', flat=True).distinct()
            program_sku_list = sorted(sku_list)
            filter_program_sku_list = program_sku_list.copy()
            program_sku_list.insert(0, "All")

            # Fetch function list
            function_list = FunctionModel.objects.values_list('Function', flat=True).distinct()

            # Fetch lab data
            lab_data = LabModel.objects.all()

            # Prepare allocation data
            allocation_data = AllocationDetailsModel.objects.filter(status="allocated").order_by('-created').values(
                'id', 'Program', 'Sku', 'Vendor', 'FromWW', 'ToWW', "Duration", "AllocatedTo", "Remarks",
                "Team", "Location__Name", "BenchData", "approvedBy", 'Function', 'Department'
            )

            master_list = []
            bench_labels = set()
            relevant_labs = set()

            for each_program_sku in program_sku_list:
                master_dict = {'category': each_program_sku, 'value': 0, 'breakdown': [], 'Report': []}
                master_count = 0
                breakdown_list = []

                relevant_programs = filter_program_sku_list if each_program_sku == "All" else [each_program_sku]

                for each_function in function_list:
                    breakdown_dict = defaultdict(int)
                    count = 0

                    for program in relevant_programs:
                        for each_lab in lab_data:
                            if each_lab.BenchDetails and "TOE" not in each_lab.Name:
                                for row in each_lab.BenchDetails:
                                    for seat in row['seats']:
                                        if seat['team'] == team or is_all_teams:
                                            allocation = seat.get('AllocationData')
                                            label_no = seat.get('labelNo')
                                            if allocation:
                                                if allocation[0]['Program'] == program and allocation[0]['Function'] == each_function:
                                                    breakdown_dict[program] += 1
                                                    master_count += 1
                                                    if label_no:
                                                        bench_labels.add(label_no)
                                                        relevant_labs.add(each_lab.Name)

                                            # if seat['RackDetail']:
                                            #     for rack in seat['RackDetail']:
                                            #         label_no = rack.get('labelNo')
                                            #         shelf_no = rack.get('shelfNo')
                                            #         if rack['AllocationData']:
                                            #             if rack['AllocationData'][0]['Program'] == program and rack['AllocationData'][0]['Function'] == each_function:
                                            #                 breakdown_dict[program] += 1
                                            #                 master_count += 1
                                            #                 if label_no is not None and shelf_no is not None:
                                            #                     combined_label = label_no + '-' + shelf_no
                                            #                     bench_labels.add(combined_label)
                                            #                     relevant_labs.add(each_lab.Name)

                    breakdown_dict = {k: v for k, v in breakdown_dict.items() if v > 0}
                    if breakdown_dict:
                        breakdown_dict['category'] = each_function
                        breakdown_list.append(breakdown_dict)

                if each_program_sku == "All":
                    filtered_allocation_data = [
                        allocation for allocation in allocation_data
                        if any(bench_label in allocation['BenchData'] for bench_label in bench_labels)
                        and allocation['Location__Name'] in relevant_labs
                    ]
                else:
                    filtered_allocation_data = [
                        allocation for allocation in allocation_data
                        if any(bench_label in allocation['BenchData'] for bench_label in bench_labels)
                        and allocation['Location__Name'] in relevant_labs
                        and allocation['Program'] in relevant_programs
                    ]

                if master_count >= 0:  # Only add to master_list if there is relevant data
                    master_dict['value'] = master_count
                    master_dict['breakdown'] = breakdown_list
                    master_dict['Report'] = filtered_allocation_data  # Assign report data list
                    master_list.append(master_dict)

            return Response(master_list, status=status.HTTP_200_OK)

        except Exception as e:
            logger_error.error(str(e))
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 
#-------------------Allocate Page View----------------------------------
class ListAllLocationsView(APIView):
    def get(self,request):
        """
            Lists all lab locations
        """
        lab_locations = LabModel.objects.all().values_list('Name').distinct()
        labs = [lab[0] for lab in lab_locations]
        return Response({'LabLocations':labs}, status=status.HTTP_200_OK)

class LabdetailsView(APIView):
    """
    View to get the details of the requested lab for the Approve page.
    """
    def post(self, request):
        lab_name = request.data.get('LabName')
        
        if not lab_name:
            logger_error.error("LabName not provided in request.")
            return Response("LabName is required", status=status.HTTP_400_BAD_REQUEST)

        try:
            lab_details = LabModel.objects.filter(Name=str(lab_name)).values()
            if not lab_details:
                logger_error.error(f"Lab with name {lab_name} does not exist.")
                return Response("Info! Lab Does Not Exist", status=status.HTTP_404_NOT_FOUND)
            
            lab_data = dict(lab_details[0])
            allocated_counts = {'SIV': 0, 'PSE': 0, 'CLSS': 0, 'C4S': 0, 'Non-SIV': 0}
            total_counts = {'SIV': 0, 'PSE': 0, 'CLSS': 0, 'C4S': 0, 'Non-SIV': 0}
            rack_count = 0
            if lab_data.get('BenchDetails'):
                for bench_row in lab_data['BenchDetails']:
                    for seat in bench_row['seats']:
                        if seat['IsAllocated']:
                            allocated_counts[seat['team']] += 1
                        # if seat.get('RackDetail'):
                        #     for rack_detail in seat['RackDetail']:
                        #         if rack_detail['IsAllocated']:
                        #             allocated_counts[seat['team']] += 1
                        if seat['dir'] == 'Rack' or seat['labelNo'] == 'A16-Rack':
                            rack_count += 1
                        team = seat.get('team')
                        if team in total_counts:
                            total_counts[team] += 1
                        if seat['team'] in ['SIV', 'PSE', 'CLSS', 'C4S'] and seat['dir'] == 'Rack' or seat['labelNo'] == 'A16-Rack':
                            total_counts[team] -= 1
                
                for team in total_counts:
                    lab_data[f'{team}Counts'] = total_counts[team] 
                
                total_allocated = sum(allocated_counts.values())
                # total_free = sum(total_counts[team] - allocated_counts[team] for team in total_counts)
                total_free = sum(total_counts[team] - allocated_counts[team] for team in total_counts if not (seat['dir'] == 'Rack' and seat['labelNo'] == 'A16-Rack'))
                
                lab_data["Allocated"] = total_allocated
                lab_data["Free"] = total_free
                lab_data['Rack'] = rack_count
                lab_data["NumberOfWorkbenches"] = sum(total_counts[team] for team in total_counts if team != 'Non-SIV')
                if lab_name == "SRR-1-CRD-15-VPG_LINUX":
                    lab_data['NumberOfWorkbenches'] = 0
                    lab_data['Free'] = 0
                    lab_data['Allocated'] = 0
                    for team in total_counts:
                        lab_data[f'{team}Counts'] = 0

                return Response(lab_data, status=status.HTTP_200_OK)
            else:
                logger_error.error(f"BenchDetails not found for lab {lab_name}")
                return Response("Info! Lab Does Not Exist", status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger_error.error(f"An error occurred: {e}", str(e))
            return Response("Error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BookBenchView(APIView):
    def post(self, request):
        """
            API for Booking the Bench
        """
        try:
            data = request.data
            # validation of allocated to field
            if data['AllocatedTo']:
                for each_data in data['AllocatedTo']:
                    try:
                        Name = each_data['Name']
                        if isinstance(Name,str):
                            pass
                        else:
                            return Response("Enter Valid Name for AllocatedToField",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except KeyError:
                        return Response("Enter Valid Name for AllocatedToField",status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    try:
                        email = each_data['Email']
                        if '@intel.com' in email:
                            pass
                        else:
                            return Response("Enter Valid Email for AllocatedToField",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except KeyError:
                        return Response("Enter Valid Name for AllocatedToField",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    try:
                        WWID = each_data['WWID']
                        if isinstance(WWID,int):
                            pass
                        else:
                            return Response("Enter Valid WWID for AllocatedToField",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except KeyError:
                        return Response("Enter Valid WWID for AllocatedToField",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response("Allocated To Details Not Valid",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if data['RequestedBy']:
                for each_data in data['RequestedBy']:
                    try:
                        Name = each_data['Name']
                        if isinstance(Name,str):
                            pass
                        else:
                            return Response("Enter Valid Name for RequestedBy",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except KeyError:
                        return Response("Enter Valid Name for RequestedBy",status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    try:
                        email = each_data['Email']
                        if '@intel.com' in email:
                            pass
                        else:
                            return Response("Enter Valid Email for RequestedBy",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except KeyError:
                        return Response("Enter Valid Name for RequestedBy",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    try:
                        WWID = each_data['WWID']
                        if isinstance(WWID,int):
                            pass
                        else:
                            return Response("Enter Valid WWID for RequestedBy",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except KeyError:
                        return Response("Enter Valid WWID for RequestedBy",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response("Allocated To Details Not Valid",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if data['NotifyTo'] is not None and data['NotifyTo']:
                try:
                    for each_mail in data['NotifyTo']:
                        if '@intel.com' in each_mail:
                            pass
                        else:
                            return Response("Enter Valid Email for NotifyTo Field",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    return Response("Enter Valid Email for NotifyTo Field",status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                pass
            try:
                lab_data = LabModel.objects.get(Name=data['LabName']) 
                lab_max_benches = lab_data.NumberOfWorkbenches

                # Save the Allocation request in allocations Model
                try:
                    #all_allocation_query = AllocationDetailsModel.objects.filter().order_by('id')
                    max_id = AllocationDetailsModel.objects.aggregate(Max('id'))['id__max']
                    # if all_allocation_query is not None:
                    #     id = int(all_allocation_query[0].id) + 1
                    #     print(id)
                    if max_id is not None:
                        id = int(max_id) + 1
   
                    else:
                        id = 1
                except Exception:
                    id = 1
                # Check if the requested benches are available for booking
                for each_bench_request in data['BenchData']:
                    for each_bench_row in lab_data.BenchDetails:
                        for each_bench_column in range(len(each_bench_row['seats'])):
                            if (each_bench_row['seats'][each_bench_column]['labelNo'] == each_bench_request):
                                if(each_bench_row['seats'][each_bench_column]['IsRequested'] == False and \
                                each_bench_row['seats'][each_bench_column]['IsAllocated'] == False):
                                    pass
                                else:
                                    return Response("Benches Not Available",status=status.HTTP_200_OK)
                if len(set(data['BenchData'])) != len(data['BenchData']):
                    return Response("BenchData should contain only unique values", status=status.HTTP_200_OK)
            except LabModel.DoesNotExist:
                    return Response("Lab DoesNotExist!!",status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger_error.error(str(e))
                return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                allocation_query = AllocationDetailsModel.objects.get(Program=data['Program'], Sku=data['Sku'], Vendor=data['Vendor'], \
                    AllocatedTo=data['AllocatedTo'], NotifyTo=data['NotifyTo'], FromWW=data['FromWW'], ToWW=data['ToWW'], \
                    NumberOfbenches=data['NumberOfBenches'], Team=data['Team'],Function=data['Function'],Department=data['Department'], Remarks=data['Remarks'], Location=lab_data, \
                    BenchData=data['BenchData'], Duration=data['Duration'], status='requested')
                return Response("Allocation Exists", status=status.HTTP_200_OK)
            except AllocationDetailsModel.DoesNotExist:
                allocation_detail = AllocationDetailsModel(id=id,Program=data['Program'],Sku=data['Sku'],Vendor=data['Vendor'],\
                    AllocatedTo=data['AllocatedTo'],NotifyTo=data['NotifyTo'],FromWW=data['FromWW'],ToWW=data['ToWW'],NumberOfbenches=data['NumberOfBenches'],
                    Team=data['Team'],Function=data['Function'],Department=data['Department'],AllocatedDate=None,Remarks=data['Remarks'],Location=lab_data,
                    IsAllocated=data['IsAllocated'],IsRequested=data['IsRequested'],BenchData=data['BenchData'],
                    Duration=data['Duration'],created=timezone.now(),status='requested',DeallocatedBenchData=[],RequestedBy=data['RequestedBy'],DeallocatedBy=data['DeallocatedBy'])

                # To Do : Send Mail for the Request is recieved
                program = data["Program"]
                sku = data['Sku']
                vendor = data['Vendor']
                allocatedTo = data['AllocatedTo']
                fromWW = data['FromWW']
                toWW = data['ToWW']
                numberofbenches = data['NumberOfBenches']
                location = data['LabName']
                remarks = data['Remarks']
                bench_data = data["BenchData"]
                team = data['Team']
                function = data['Function']
                Department=data['Department']
                duration = data['Duration']
                RequestedBy=data['RequestedBy']
                # deallocatedby = data['DeallocatedBy']
                message = "This email is a confirmation of your Lab Bench <b>Submitted<b>  "
                subject = "Bench Request Submitted for "
                try:
                    #NotifyTo is a list 
                    if data['NotifyTo'] is not None and data['NotifyTo']:
                        notifyTo = data['NotifyTo']
                        notify_persons = notifyTo
                        notify_emails = notifyTo
                    else:
                        notifyTo = None
                        notify_persons =[]
                        notify_emails = []
                except KeyError:
                    notifyTo = None
                    notify_persons =[]
                    notify_emails = []
                
                mail_data = {
                            "User":allocatedTo[0]['Name'],
                            "WWID":allocatedTo[0]['WWID'],
                            "id":id,
                            "program":program,
                            "sku":sku,
                            "lab_name":location,
                            'department':Department,
                            "vendor":vendor,
                            "allocatedto":allocatedTo[0]['Name'],
                            "notifyto":','.join(notify_persons),
                            "requestedBy":RequestedBy[0]['Name'],
                            "fromww":fromWW,
                            "toww":toWW,
                            "duration":duration,
                            "remarks":remarks,
                            "team":team,
                            "function":function,
                            "numberofbenches":numberofbenches,
                            "message":message,
                            "subject":subject,
                            "deallocatedby":None
                        }
                
                bench_data = []
                rack_shelf_data = []

                if 'BenchData' in data and data['BenchData']:
                    for each_bench in data['BenchData']:
                        if 'Rack' in each_bench:
                            rack_shelf_data.append(each_bench)
                        else:
                            bench_data.append(each_bench)

                mail_data["bench_data"] = bench_data
                mail_data["Rack-Shelf"] = rack_shelf_data
                
                TO.append(str(allocatedTo[0]['Email']))
                RequestedBy_email = data['RequestedBy'][0]['Email'] if data.get('RequestedBy') else None
                print(RequestedBy_email)
                Cc = []
                if RequestedBy_email:
                    Cc.append(RequestedBy_email)
                
                if notify_persons:
                    Cc.extend(notify_persons)
                try:
                    Cc = Cc + CC
                    print(Cc)
                    mail = Email(FROM, TO, Cc, mail_data)
                except Exception:
                    print(traceback.format_exc())
                mail.sendmail()
                allocation_detail.save()
                TO.pop()
                # To save the requested benches in LabModel block the requested benches
                for each_bench_request in data['BenchData']:
                    print(each_bench_request)
                    try:
                        query = LabModel.objects.get(Q(Name=data['LabName']))
                        if each_bench_request.startswith("Rack"):
                            rack_label, shelf_label = each_bench_request.split('-')  # Split bench data into rack and shelf labels
                            print("Processing Rack:", each_bench_request)
                            print('Rack_label', rack_label)
                            print('Shelf_label', shelf_label)
                            # Find the specific rack and shelf indicated in BenchData
                            for each_bench_row in query.BenchDetails:
                                for each_bench_column in each_bench_row['seats']:
                                    if each_bench_column['labelNo'] == rack_label:
                                        print("Found specified rack and shelf:", each_bench_request)
                                        # Update RackDetail for the specified rack and shelf
                                        # if each_bench_column['dir'] == 'Rack':
                                        for each_rack_detail in each_bench_column['RackDetail']:
                                            if each_rack_detail['shelfNo'] == shelf_label:
                                                each_rack_detail['id'] = id
                                                each_rack_detail['IsAllocated'] = data['IsAllocated']
                                                each_rack_detail['IsRequested'] = data['IsRequested']
                                                each_rack_detail['labelNo'] = rack_label
                                                each_rack_detail['AllocationData'] = None        
                                                all_rack_detail_requested = all(detail['IsRequested'] for detail in each_bench_column['RackDetail'])
                                        each_bench_column['IsRequested'] = all_rack_detail_requested
                            query.save()
                        else:
                            print("Processing Bench:", each_bench_request)
                            # Find the specific bench indicated in BenchData
                            for each_bench_row in query.BenchDetails:
                                for each_bench_column in each_bench_row['seats']:
                                    if each_bench_column['labelNo'] == each_bench_request:
                                        print("Found specified bench:", each_bench_request)
                                        each_bench_column['IsRequested'] = data['IsRequested']
                                        each_bench_column['IsAllocated'] = data['IsAllocated']
                                        each_bench_column['AllocationData'] = None
                                        each_bench_column['RackDetail'] = None
                            query.save()
                    except LabModel.DoesNotExist:
                        return Response("Lab DoesNotExist!!", status=status.HTTP_404_NOT_FOUND)
                return Response("Allocation Request Added Successfully",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            print(traceback.format_exc())
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeallocateBenchesView(APIView):
    def get(self, request):
        """ API to list all allocations"""
        try:
            allocated_data = AllocationDetailsModel.objects.filter(IsAllocated__in=['True']).values(
                'id', 'Program', 'Sku', 'Vendor', 'FromWW', 'ToWW', 'Duration', 'AllocatedTo', 'NotifyTo', 
                'NumberOfbenches', 'Remarks', 'Team', 'Function', 'Department', 'IsAllocated', 'IsRequested', 
                'Location__Name', 'BenchData', 'AllocatedDate', 'status', 'DeallocatedBy')
            allocated_data_list = [each_allocation for each_allocation in allocated_data]
            return Response(allocated_data_list, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

    def post(self, request):
        """ API to deallocate benches manually"""
        data = request.data

        # CHANGES
        user_name = data[0]["DeallcationUserInfo"]["name"]
        user_email = data[0]["DeallcationUserInfo"]["emailId"]
        allocation_time = data[0]["DateandTime"]

        try:
            lab_name = data[0]['LabName']
            reason = data[0]['Reason']

            lab_data = LabModel.objects.get(Q(Name=lab_name))
            deallocated_benches = []

            for each_data in data:
                id = each_data['id']
                allocation_data = AllocationDetailsModel.objects.get(id=id)
                for bench_data in each_data['BenchData']:  # Iterate over each bench
                    if bench_data in allocation_data.BenchData:
                        allocation_data.BenchData.remove(bench_data)
                        allocation_data.DeallocatedBenchData.append(bench_data)
                        allocation_data.DeallocatedBy = user_name
                        allocation_data.deallocatedDate = allocation_time
                        allocation_data.save()
                        deallocated_benches.append(bench_data)
                    # If all benches are deallocated
                    if not allocation_data.BenchData:
                        allocation_data.IsAllocated = False
                        allocation_data.IsRequested = False
                        allocation_data.status = "complete"
                        allocation_data.BenchData = allocation_data.DeallocatedBenchData
                        allocation_data.Reason = f"{bench_data}: {reason} {allocation_data.Reason}"
                        allocation_data.DeallocatedBy = user_name
                        allocation_data.deallocatedDate = datetime.now()
                        allocation_data.save()

                    if '-' in bench_data:  # Check if it's in the format "Rack 7-Shelf 2"
                        rack_label, shelf_label = bench_data.split('-')  # Split bench data into rack and shelf labels
                        for each_bench_row in lab_data.BenchDetails:
                            for each_bench_column in each_bench_row['seats']:
                                if each_bench_column['labelNo'] == rack_label:
                                    if 'RackDetail' in each_bench_column:
                                        for rack_detail in each_bench_column['RackDetail']:
                                            if rack_detail['shelfNo'] == shelf_label:
                                                rack_detail['IsRequested'] = False
                                                rack_detail['IsAllocated'] = False
                                                rack_detail['AllocationData'] = None
                                        all_rack_benches_allocated = all(
                                            detail['IsAllocated'] for detail in each_bench_column['RackDetail'])
                                        all_rack_benches_requested = all(
                                            detail['IsRequested'] for detail in each_bench_column['RackDetail'])
                                        each_bench_column['IsAllocated'] = all_rack_benches_allocated
                                        each_bench_column['IsRequested'] = all_rack_benches_requested
                        lab_data.save()
                    else:
                        for each_bench_row in lab_data.BenchDetails:
                            for each_bench_column_no in range(len(each_bench_row['seats'])):
                                if each_bench_row['seats'][each_bench_column_no]['labelNo'] == bench_data:
                                    each_bench_row['seats'][each_bench_column_no]['IsRequested'] = False
                                    each_bench_row['seats'][each_bench_column_no]['IsAllocated'] = False
                                    each_bench_row['seats'][each_bench_column_no]['AllocationData'] = None
                        lab_data.save()

            notify_persons = []
            if allocation_data.NotifyTo is not None:
                notify_persons = allocation_data.NotifyTo
                notify_emails = allocation_data.NotifyTo
            else:
                notifyTo = None
                notify_persons = []
                notify_emails = []

            message = f"This email is a confirmation of your Lab Bench <b>Deallocated<b> for reason {reason}"
            subject = "Bench request Deallocated for "
            mail_data = {
                "User": allocation_data.AllocatedTo[0]['Name'],
                "WWID": allocation_data.AllocatedTo[0]['WWID'],
                "program": allocation_data.Program,
                "sku": allocation_data.Sku,
                "lab_name": lab_name,
                'department': allocation_data.Department,
                "vendor": allocation_data.Vendor,
                "allocatedto": allocation_data.AllocatedTo[0]['Name'],
                "notifyto": ','.join(notify_persons),
                "requestedBy": allocation_data.RequestedBy[0]['Name'],
                "fromww": str(allocation_data.FromWW),
                "toww": str(allocation_data.ToWW),
                "duration": allocation_data.Duration,
                "remarks": allocation_data.Remarks,
                "team": allocation_data.Team,
                "function": allocation_data.Function,
                "id": id,
                "numberofbenches": len(deallocated_benches),
                "bench_data": deallocated_benches,  # Updated to include all deallocated benches
                "message": message,
                "subject": subject,
                "deallocatedby": allocation_data.DeallocatedBy
            }
            rack_shelf_benches = [bench for bench in deallocated_benches if '-' in bench]
            other_benches = [bench for bench in deallocated_benches if '-' not in bench]

            mail_data['Rack-Shelf'] = rack_shelf_benches
            mail_data['bench_data'] = other_benches

            TO = [str(allocation_data.AllocatedTo[0]['Email'])]
            if notify_emails:
                Cc = notify_emails
            else:
                Cc = [user_email]

            Cc = Cc + CC  # Add any additional CC if required
            mail = Email(FROM, TO, Cc, mail_data)
            mail.sendmail()
            
            return Response("Success", status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetProgramDetailsView(APIView):
    def get(self, request):
        """"is released by you
            API to list all the Programs available in the database
        """
        try:
            programs_list = []
            program_data = ProgramsModel.objects.filter().values('ProgramShortName')
            program_list = [each_program['ProgramShortName'] for each_program in program_data]
            return Response({"ProgramName":program_list}, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetSKUDetailsView(APIView):
    def post(self, request):
        """
        API to list all the SKU's available for the given program in database
        """
        try:
            program_name = request.data['ProgramShortName']
            SkuDetails = SkuModel.objects.filter(ProgramName__ProgramShortName=program_name).values('SkuName')
            sku_list = [each_sku['SkuName'] for each_sku in SkuDetails]
            return Response(sku_list,status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetVendorDetails(APIView):
    def get(self, request):
        """
            Lists all the vendors present in the database
        """
        try:
            vendors_list = []
            query = VendorsModel.objects.all().values_list('VendorName')
            for each_vendor in query:
                vendors_list.append(each_vendor[0])
            vendors_list = list(set(vendors_list))
            return Response({"Vendors":vendors_list},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetTeamNamesView(APIView):
    def get(self, request):
        """ API to list all the team names in the database"""
        try:
            query = TeamsModel.objects.all().values_list('TeamName')
            teams_list = []
            for each_team in query:
                teams_list.append(each_team[0])
            teams_list = list(set(teams_list))
            return Response({"TeamName":teams_list}, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetFunctionView(APIView):
    def post(self, request):
        """
        API to list all the Functions available for the given team in the database
        """
        try:
            team_name = request.data.get('TeamName')  # Use get() to avoid KeyError if 'TeamName' is missing
            if team_name:
                function_details = FunctionModel.objects.filter(TeamName__TeamName=team_name).values('Function')
                function_list = [each_function['Function'] for each_function in function_details]
                return Response({"FunctionList":function_list}, status=status.HTTP_200_OK)
            else:
                return Response("TeamName is required in the request data", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# Approve Page

class ApproveViewPage(APIView):
    def get(self, request):
        """
            View that Lists all Bench Request
        """
        try:
            pending_data = AllocationDetailsModel.objects.filter(Q(IsAllocated__in=[False]) & Q(IsRequested__in=[True])).order_by('-created').values('id','Program','Sku','Vendor','FromWW',
            'ToWW','Duration','AllocatedTo','NotifyTo','NumberOfbenches','Team','Function','Department','Remarks','IsAllocated','IsRequested','Location__Name','BenchData','RequestedBy','RequestedDate','DeallocatedBy','deallocatedDate')
            if pending_data is not None:
                #serializer = ApproveViewSerializer(pending_data,many=True)
                return Response(pending_data, status.HTTP_200_OK)
            else:
                return Response("No Match for Allocation Data!!",status=status.HTTP_404_NOT_FOUND)
        except AllocationDetailsModel.DoesNotExist:
            logger_error.error(str("Allocation Data not Exists!!"))
            return Response("Allocation Data not Exists!!",status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """This method stores the Approved requests from Approved page"""
        data = request.data["requestIdList"]
        approved_by = request.data['approvedBy']
        try:
            for each_data in data:
                # This If Statement executes when the request gets approved
                if True:
                    id = each_data
                    allocation_query = AllocationDetailsModel.objects.get(id=id)
                    print(allocation_query)
                    program = allocation_query.Program
                    sku = allocation_query.Sku
                    vendor = allocation_query.Vendor
                    allocatedTo = allocation_query.AllocatedTo
                    fromWW = allocation_query.FromWW
                    toWW = allocation_query.ToWW
                    numberofbenches = allocation_query.NumberOfbenches
                    location = allocation_query.Location.Name
                    remarks = allocation_query.Remarks
                    team = allocation_query.Team
                    function = allocation_query.Function
                    department = allocation_query.Department
                    duration = allocation_query.Duration
                    bench_data = allocation_query.BenchData
                    print(allocation_query.BenchData)
                    RequestedBy = allocation_query.RequestedBy
                    deallocatedby = allocation_query.DeallocatedBy
                    message = "This email is a confirmation of your Lab Bench <b>Approved<b>  "
                    subject = "Bench Request Approved for "
                    # Save the Allocated status to allocations Model
                    try:
                        query = AllocationDetailsModel.objects.get(Q(id=id))
                        if not query.IsAllocated:
                            query.IsAllocated = True
                            query.IsRequested = False
                            query.AllocatedDate = datetime.now()
                            query.status='allocated'
                            query.approvedBy = approved_by
                            # # To DO : Send a mail that the request been approved
                            try:
                                requested_by_email = ""
                                if query.RequestedBy:
                                    requested_by_email = query.RequestedBy[0]['Email']
                                if requested_by_email == approved_by:
                                    notify_persons = [approved_by]
                                else:
                                    notify_persons = query.NotifyTo if query.NotifyTo else []
                                notify_emails = notify_persons
                            except KeyError:
                                notify_emails = []
                            
                            
                            mail_data = {
                                "User":allocatedTo[0]['Name'],
                                "WWID":allocatedTo[0]['WWID'],
                                "id":id,
                                "program":program,
                                "sku":sku,
                                "lab_name":location,
                                'department':department,
                                "vendor":vendor,
                                "allocatedto":allocatedTo[0]['Name'],
                                "notifyto":','.join(notify_persons),
                                "requestedBy":RequestedBy[0]['Name'],
                                "fromww":fromWW,
                                "toww":toWW,
                               "duration":duration,
                                "remarks":remarks,
                                "team":team,
                                "function":function,
                                "numberofbenches":numberofbenches,
                                "message":message,
                                "subject":subject,
                                "deallocatedby":""
                            }
                            
                            bench_data = []
                            rack_shelf_data = []
                            if "BenchData" in allocation_query.__dict__ and allocation_query.BenchData:
                                for each_bench in allocation_query.BenchData:
                                    if 'Rack' in each_bench:
                                        rack_shelf_data.append(each_bench)
                                    else:
                                        bench_data.append(each_bench)

                            mail_data["bench_data"] = bench_data
                            mail_data["Rack-Shelf"] = rack_shelf_data

                            TO.append(str(allocatedTo[0]['Email']))
                            if notify_emails:
                                Cc = notify_emails
                            else:
                                Cc=[]
                            Cc = Cc+CC
                            mail = Email(FROM,TO,Cc,mail_data)
                            mail.sendmail()
                            query.save()
                            TO.pop()
                            # Assign the benches to the requested persons once approved

                            for each_bench_request in allocation_query.BenchData:
                                print("Processing BenchData:", each_bench_request)
                                try:
                                    # Check if Bench Exists. If exists, change the bench status, else create new bench.
                                    lab_query = LabModel.objects.get(Q(Name=location))
                                    if '-' in each_bench_request:  # Check if it's in the format "Rack 7-Shelf 2"
                                        rack_label, shelf_label = each_bench_request.split('-')  # Split bench data into rack and shelf labels
                                        for each_bench_row in lab_query.BenchDetails:
                                            for each_bench_column in each_bench_row['seats']:
                                                if each_bench_column['labelNo'] == rack_label:
                                                    print("each_bench_column",each_bench_column)
                                                    if 'RackDetail' in each_bench_column:
                                                        # all_rack_detail_allocated = True  # Flag to track if all RackDetail items are allocated
                                                        for rack_detail in each_bench_column['RackDetail']:
                                                            print("rackdetail", rack_detail)
                                                            if rack_detail['shelfNo'] == shelf_label:
                                                                temp_dict = {
                                                                    'id': id,
                                                                    'Program': program,
                                                                    'SKU': sku,
                                                                    'Vendor': vendor,
                                                                    'Who': allocatedTo,
                                                                    'FromWW': fromWW,
                                                                    'ToWW': toWW,
                                                                    'Team': team,
                                                                    'Duration': duration,
                                                                    'Remarks': remarks,
                                                                    'Function':function,
                                                                    'Department':department
                                                                }
                                                                rack_detail['AllocationData'] = [temp_dict]
                                                                rack_detail['IsRequested'] = False
                                                                rack_detail['IsAllocated'] = True
                                                                print("updated detail", rack_detail)
                                                                all_rack_benches_allocated = all(detail['IsAllocated'] for detail in each_bench_column['RackDetail'])
                                                                all_rack_detail_requested = all(detail['IsRequested'] for detail in each_bench_column['RackDetail'])
                                                        each_bench_column['IsAllocated'] = all_rack_benches_allocated
                                                        each_bench_column['IsRequested'] = all_rack_detail_requested
                                        lab_query.save()
                                    else: 
                                        for each_bench_row in lab_query.BenchDetails:
                                            for each_bench_column in each_bench_row['seats']:
                                                if each_bench_column['labelNo'] == each_bench_request:
                                                    each_bench_column['IsRequested'] = False
                                                    each_bench_column['IsAllocated'] = True
                                                    temp_dict = {
                                                        'id': id,
                                                        'Program': program,
                                                        'SKU': sku,
                                                        'Vendor': vendor,
                                                        'Who': allocatedTo,
                                                        'FromWW': fromWW,
                                                        'ToWW': toWW,
                                                        'Team': team,
                                                        'Duration': duration,
                                                        'Remarks': remarks,
                                                        'Function':function,
                                                        'Department':department
                                                    }
                                                    each_bench_column['AllocationData'] = [temp_dict]
                                        lab_query.save()
                                                   
                                except LabModel.DoesNotExist:
                                    print("Lab not found")
                    except AllocationDetailsModel.DoesNotExist:
                        pass  
            return Response("Success",status=status.HTTP_200_OK)       
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class RejectAPIView(APIView):
    def post(self, request):
        """
            API for Rejecting multiple bench requests
        """
        data = request.data["requestIdList"]
        reason = request.data["Reason"]
        approved_by = request.data["rejectedBy"]
        try:
            for each_data in data:
                if True:
                    # If the request is Rejected
                    id = each_data
                    allocation_query = AllocationDetailsModel.objects.get(id=id)
                    program = allocation_query.Program
                    sku = allocation_query.Sku
                    vendor = allocation_query.Vendor
                    allocatedTo = allocation_query.AllocatedTo
                    fromWW = allocation_query.FromWW
                    toWW = allocation_query.ToWW
                    duration = allocation_query.Duration
                    numberofbenches = allocation_query.NumberOfbenches
                    location = allocation_query.Location.Name
                    remarks = allocation_query.Remarks
                    team = allocation_query.Team
                    function = allocation_query.Function
                    department = allocation_query.Department
                    bench_data = allocation_query.BenchData
                    requestedBy = allocation_query.RequestedBy
                    deallocatedBy = allocation_query.DeallocatedBy
                    query = AllocationDetailsModel.objects.get(id=id)
                    query.IsAllocated = False
                    query.IsRequested = False
                    query.AllocatedDate = timezone.now()
                    query.status='rejected'
                    query.Reason = reason
                    query.RejectedBy = approved_by
                    query.RejectedDate = datetime.now()
                    message = "This email is a confirmation of your Lab Bench <b>Rejected<b> for Reason <b>" + reason + "</b>"
                    subject = "Bench request Rejected for "
                    try:
                        if allocation_query.NotifyTo is not None and allocation_query.NotifyTo:
                            notifyTo = allocation_query.NotifyTo
                            notify_persons = allocation_query.NotifyTo
                            notify_emails = allocation_query.NotifyTo
                        else:
                            notifyTo = None
                            notify_persons = []
                            notify_emails = []
                    except KeyError:
                        notifyTo = None
                        notify_persons = []
                        notify_emails = []

                    mail_data = {
                        "User":allocatedTo[0]['Name'],
                        "WWID":allocatedTo[0]['WWID'],
                        "id":id,
                        "program":program,
                        "sku":sku,
                        "lab_name":location,
                        'department':department,
                        "vendor":vendor,
                        "allocatedto":allocatedTo[0]['Name'],
                        "notifyto":','.join(notify_persons),
                        "fromww":fromWW,
                        "toww":toWW,
                        "duration":duration,
                        "remarks":remarks,
                        "team":team,
                        "function":function,
                        "requestedBy":requestedBy[0]['Name'],
                        "deallocatedby":None,
                        "numberofbenches":numberofbenches,
                        "message":message,
                        "subject":subject
                    }
                    bench_data = []
                    rack_shelf_data = []
                    if "BenchData" in allocation_query.__dict__ and allocation_query.BenchData:
                        for each_bench in allocation_query.BenchData:
                            if 'Rack' in each_bench:
                                    rack_shelf_data.append(each_bench)
                            else:
                                    bench_data.append(each_bench)
                    mail_data["bench_data"] = bench_data
                    mail_data["Rack-Shelf"] = rack_shelf_data

                        
                    TO.append(str(allocatedTo[0]['Email']))
                    if notify_emails:
                        Cc = notify_emails
                    else:
                        Cc = []
                    Cc = Cc+CC
                    mail = Email(FROM,TO,Cc,mail_data)
                    mail.sendmail()
                    query.save()
                    TO.pop()
                    # Change the IsRequested status after rejecting the request
                    # bench_data = allocation_query.BenchData
                    for each_bench_request in allocation_query.BenchData:
                        try:
                            lab_query = LabModel.objects.get(Q(Name=location))
                            if '-' in each_bench_request:  # Check if it's in the format "Rack 7-Shelf 2"
                                rack_label, shelf_label = each_bench_request.split('-')  # Split bench data into rack and shelf labels
                                for each_bench_row in lab_query.BenchDetails:
                                    for each_bench_column in each_bench_row['seats']:
                                        if each_bench_column['labelNo'] == rack_label:
                                            if 'RackDetail' in each_bench_column:
                                                all_rack_benches_allocated = all(detail['IsAllocated'] for detail in each_bench_column['RackDetail'])
                                                all_rack_benches_requested = all(detail['IsRequested'] for detail in each_bench_column['RackDetail'])
                                                for rack_detail in each_bench_column['RackDetail']:
                                                    if rack_detail['shelfNo'] == shelf_label:
                                                        rack_detail['IsRequested'] = False
                                                        rack_detail['IsAllocated'] = False
                                                        rack_detail['AllocationData'] = None
                                                
                                                each_bench_column['IsAllocated'] = all_rack_benches_allocated
                                                each_bench_column['IsRequested'] = all_rack_benches_requested
                                lab_query.save()
                            else:
                                for each_bench_row in lab_query.BenchDetails:
                                    for each_bench_column in each_bench_row['seats']:
                                        if each_bench_column['labelNo'] == each_bench_request:
                                            each_bench_column['IsRequested'] = False
                                            each_bench_column['IsAllocated'] = False
                                            each_bench_column['AllocationData'] = None
                                lab_query.save()
                        except LabModel.DoesNotExist:
                            pass
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            error_message = str(e)  # Extract the error message
            logger_error.error(error_message)  # Log the error message
            return Response(error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  # Return the error message as response
        
class AllocationReportView(APIView):
    def get(self,request):
        """ API to get all allocation details"""
        try:
            allocation_data = AllocationDetailsModel.objects.filter(isAllocated__in=[True]).values().order_by('-created')
            if allocation_data:
                return Response([],status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_404_NOT_FOUND)

class AddApproverUserView(APIView):
    def get(self,request):
        """ APi to list all the approvers """
        try:
            User_data = ApproverUserModel.objects.filter().values()
            if User_data:
                user_response = [each_user for each_user in User_data]
                return Response(user_response,status=status.HTTP_200_OK)
            else:
                return Response([],status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """ API to add new approver to approver details page"""
        try:
            data = request.data
            WWID = data['wwid']
            Name = data['name']
            Email = data['emailId']
            Idsid = data['idsid']
            Badge = data["employeeBadgeType"]
            DisplayName = data["displayName"]
            try:
                query = ApproverUserModel.objects.get(WWID=WWID)
                return Response("User Exists",status=status.HTTP_200_OK)
            except ApproverUserModel.DoesNotExist:
                ApproverUserModel.objects.create(WWID=WWID,Name=Name,Email=Email,Idsid=Idsid,Badge=Badge,DisplayName=DisplayName,\
                                                  LastLoggedOn=timezone.localtime(),CreatedOn=timezone.localtime(),IsActive=True)
            return Response("Added Successfully",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteApproverUserView(APIView):
    def post(self, request):
        """ API to delete the approver from Approver table"""
        data = request.data
        WWID = data['WWID']
        try:
            ApproverUserModel.objects.get(WWID=WWID).delete()
            return Response("Deleted Successfully",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class EditAPIView(APIView):
    def post(self, request):
        # data = request.data["id"]
        data1 = request.data

        try:
            for each_data in data1:
                if True:
                    id = each_data["id"]
                    allocation_query = AllocationDetailsModel.objects.get(id=id)
                    allocation_query.Program = each_data['Program']
                    allocation_query.Sku = each_data['Sku']
                    allocation_query.Vendor = each_data['Vendor']
                    allocation_query.FromWW = each_data['FromWW']
                    allocation_query.Function = each_data['Function']
                    allocation_query.Department = each_data['Department']
                    # allocation_query.AllocatedTo = each_data['AllocatedTo']
                    # allocation_query.NotifyTo = each_data['NotifyTo']
                    allocation_query.FromWW = each_data['FromWW']
                    allocation_query.NumberOfbenches = each_data['NumberOfbenches']
                    allocation_query.BenchData = each_data['BenchData']
                    allocation_query.ToWW = each_data['ToWW']
                    allocation_query.Duration = each_data['Duration']
                    allocation_query.Team = each_data['Team']
                    allocation_query.Remarks = each_data['Remarks']
                    # allocation_query.RequestedBy = each_data['RequestedBy']
                    # allocation_query.DeallocatedBy = each_data['DeallocatedBy']
                    allocation_query.save()

            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Report PAge
class ReportPageView(APIView):
    def post(self, request):
        try:
            team = request.data.get('team', None)
            pending_data_list = self.get_pending_data_list(team)
            
            if pending_data_list:
                self.format_dates(pending_data_list)
                return Response(pending_data_list, status=status.HTTP_200_OK)
            else:
                return Response([], status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            print(traceback.format_exc())
            logger_error.error(f"An error occurred while processing the request: {e}", exc_info=True)
            return Response("An error occurred while processing the request.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_pending_data_list(self, team):
        pending_data_dict = {}  # Use a dictionary to store unique entries
        lab_models = LabModel.objects.all()

        if team == "CCG":
            teams = set()
            for lab_model in lab_models:
                for bench_detail in lab_model.BenchDetails or []:
                    for seat in bench_detail.get('seats', []):
                        if seat.get('team') and seat.get('team') != 'Non-SIV':
                            teams.add(seat.get('team'))

            for team_name in teams:
                if team_name != 'Non-SIV':  # Exclude 'Non-SIV' team
                    self.get_pending_data_for_team(team_name, lab_models, pending_data_dict)

        else:
            self.get_pending_data_for_team(team, lab_models, pending_data_dict)

        return list(pending_data_dict.values())  # Convert the dictionary back to a list

    def format_dates(self, pending_data_list):
        for item in pending_data_list:
            if 'AllocatedDate' in item:
                allocated_date_obj = item['AllocatedDate']
                if isinstance(allocated_date_obj, datetime):
                    date_with_offset = allocated_date_obj + timedelta(hours=5, minutes=30, seconds=10)
                    item.update(
                        AllocatedDate=date_with_offset.strftime('%d-%m-%Y %H:%M:%S'),
                        RequestedDate=date_with_offset.strftime('%d-%m-%Y %H:%M:%S'),
                        deallocatedDate=date_with_offset.strftime('%d-%m-%Y %H:%M:%S'),
                        RejectedDate=date_with_offset.strftime('%d-%m-%Y %H:%M:%S')
                    )
                elif isinstance(allocated_date_obj, str):
                    # Convert string to datetime object
                    try:
                        allocated_date_obj = datetime.strptime(allocated_date_obj, '%Y-%m-%d %H:%M:%S.%f%z')
                    except ValueError:
                        # Handle if the string format is different
                        pass  # Add your handling code here
                    else:
                        # Perform the addition and formatting
                        date_with_offset = allocated_date_obj + timedelta(hours=5, minutes=30, seconds=10)
                        item.update(
                            AllocatedDate=date_with_offset.strftime('%d-%m-%Y %H:%M:%S'),
                            RequestedDate=date_with_offset.strftime('%d-%m-%Y %H:%M:%S'),
                            deallocatedDate=date_with_offset.strftime('%d-%m-%Y %H:%M:%S'),
                            RejectedDate=date_with_offset.strftime('%d-%m-%Y %H:%M:%S')
                        )
                else:
                    # Handle other cases or raise an error if necessary
                    pass  # Add your handling code here for other cases

    def get_pending_data_for_team(self, team, lab_models, pending_data_dict):
        bench_labels = set()
        relevant_labs = set()
        allocation_data = AllocationDetailsModel.objects.filter(status="allocated").order_by('-created').values(
            'id', 'Program', 'Sku', 'Vendor', 'FromWW',
            'ToWW', 'Duration', 'AllocatedTo', 'NumberOfbenches', 'Remarks', 'Team','Function' ,'Department','IsAllocated', 'IsRequested', 'Location__Name', 'BenchData', 
            'AllocatedDate', 'status', 'approvedBy', 'RejectedBy', 'RequestedBy', 'RequestedDate', 'RejectedDate', 'DeallocatedBy', 'deallocatedDate', 'Reason'
        )
        
        for lab_model in lab_models:
            for bench_detail in lab_model.BenchDetails or []:
                for seat in bench_detail.get('seats', []):
                    seat_team = seat.get('team')
                    if team == 'CCG':
                        if seat_team and seat_team != 'Non-SIV':
                            rack_details = seat['RackDetail']
                            if seat.get('IsAllocated'):
                                label_no = seat.get('labelNo')
                                if label_no:
                                    bench_labels.add((label_no, lab_model.Name))
                    elif team:
                        if seat_team == team:
                            rack_details = seat['RackDetail']
                            if seat.get('IsAllocated'):
                                label_no = seat.get('labelNo')
                                if label_no:
                                    bench_labels.add((label_no, lab_model.Name))
                                    
                            # elif rack_details:
                            #     for rack_detail in rack_details:
                            #         if rack_detail['IsAllocated']:
                            #             label_no = rack_detail.get('labelNo')
                            #             shelf_no = rack_detail.get('shelfNo')
                            #             if label_no is not None and shelf_no is not None:
                            #                 combined_label = label_no + '-' + shelf_no
                            #                 bench_labels.add(combined_label)
                            #                 relevant_labs.add(lab_model.Name)

        for allocation in allocation_data:
            if any((bench_label, allocation['Location__Name']) in bench_labels for bench_label in allocation['BenchData']):
                if allocation['id'] not in pending_data_dict:
                    pending_data_dict[allocation['id']] = allocation
                else:
                    print(f"Duplicate found: Allocation ID {allocation['id']} is already in the dictionary")

#-----------MASTER PAGE API's ---------------------------
class AddProgramView(APIView):
    def get(self,request):
        """API To list all Programs"""
        try:
            query = ProgramsModel.objects.filter().values()
            programs_list = []
            if query:
                programs_list = [ each_query for each_query in query]
            return Response(programs_list,status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self,request):
        """ API to add new program to the database"""
        data = request.data
        program = data['ProgramName']
        programshortname = data['ProgramShortName']
        try:
            # if program exists create new skew
            program_filter = ProgramsModel.objects.get(Q(ProgramName=program))
            if (program_filter is not None) :
                return Response({"result":{"status":False,"message":"Program Already Exist"}},status=status.HTTP_200_OK)
        except ProgramsModel.DoesNotExist:
            try:
                program_short_name_filter = ProgramsModel.objects.get(Q(ProgramShortName=programshortname))
                if program_short_name_filter is not None:
                    return Response({"result":{"status":False,"message":"ProgramShortName Already Exist"}},status=status.HTTP_200_OK)
            except ProgramsModel.DoesNotExist:
                program_query = ProgramsModel(ProgramName=program,ProgramShortName=programshortname)
                program_query.save()
                return Response({"result":{"status":True,"message":"Program Added Successfully"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            print(e)
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EditDeleteProgramView(APIView):
    """ API for Editing and Deleting the Program"""
    def put(self,request):
        """ API to edit the program"""
        data = request.data
        id = data['id']
        try:
            programname = data['ProgramName']
        except Exception:
            programname = None
        try:
            programshortname = data['ProgramShortName']
        except Exception:
            programshortname = None

        try:
            query = ProgramsModel.objects.get(id=id)
            if (programname is  not None ) and (query.ProgramName==programname):
                pass
            else:
                try:
                    existing_program_check_query = ProgramsModel.objects.get(ProgramName=programname)
                    if existing_program_check_query:
                        return Response({"result":{"status":False,"message":"ProgramName Already Exists!!"}},status=status.HTTP_200_OK)
                except ProgramsModel.DoesNotExist:
                    query.ProgramName=programname
            if (programshortname is not None) and (query.ProgramShortName!=programshortname):
                try:
                    existing_program_shortname = ProgramsModel.objects.get(ProgramShortName=programshortname)
                    if existing_program_shortname:
                        return Response({"result":{"status":False,"message":"ProgramShortName Already Exists!!"}},status=status.HTTP_200_OK)
                except ProgramsModel.DoesNotExist:
                    query.ProgramShortName=programshortname
            query.save()
            return Response({"result":{"status":True,"message":'Program Edited Successfully'}},status=status.HTTP_200_OK)
        except ProgramsModel.DoesNotExist:
            logger_error.error(str('Program not exist'))
            return Response({"result":{"status":False,"message":'Program not exist'}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self,request):
        """ API to delet the program"""
        data = request.data
        id = data['id']
        try:
            ProgramsModel.objects.get(id=id).delete()
            return Response({"result":{"status":True,"message":"Deleted Successfully"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AddSkuView(APIView):
    def get(self,request):
        """ API to list all the Sku's in the database"""
        try:
            skulist = []
            skudata = SkuModel.objects.filter().values('id','ProgramName__ProgramShortName','SkuName')
            skulist = [ each_sku for each_sku in skudata]
            return Response(skulist,status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            """ API to add new Sku to the Database """
            data = request.data
            programshortname = data['ProgramShortName']
            skuname = data['SkuName']  
            try:
                sku_query = SkuModel.objects.get(Q(ProgramName__ProgramShortName=programshortname) & Q(SkuName=skuname))
                if sku_query:
                    return Response({"result":{"status":False,"message":"Sku Already Exists"}},status=status.HTTP_200_OK)
            except SkuModel.DoesNotExist:
                try:
                    programs_query = ProgramsModel.objects.get(ProgramShortName=programshortname)
                    if programs_query is not None:
                        sku_query = SkuModel(ProgramName=programs_query,SkuName=skuname)
                        sku_query.save()
                        return Response({"result":{"status":True,"message":'Sku Added Successfully'}},status=status.HTTP_201_CREATED)
                    else:
                        return Response({"result":{"status":False,"message":"Cannot Add Sku"}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except ProgramsModel.DoesNotExist:
                    programs_query = ProgramsModel(ProgramShortName=programshortname)
                    programs_query.save()
                    skuquery = SkuModel(ProgramName=programs_query,SkuName=skuname)
                    skuquery.save()
                    return Response({"result":{"status":True,"message":'Sku Added Successfully'}},status=status.HTTP_201_CREATED)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EditDeleteSkuView(APIView):
    """ API for Editing and Deleting the Sku"""
    def put(self,request):
        """ API for editing the SKU"""
        data = request.data
        id = data['id']
        skuname = data['SkuName']
        programshortname = data['ProgramShortName']
        try:
            query = SkuModel.objects.get(Q(id=id) & Q(ProgramName__ProgramShortName=programshortname))
            query.SkuName = skuname
            query.save()
            return Response({"result":{"status":True,"message":"Sku Edited Successfully"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        """ API for deleting the SKU"""
        data = request.data
        id = data['id']
        try:
            SkuModel.objects.get(id=id).delete()
            return Response({"result":{"status":True,"message":"Sku Deleted Successfully"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AddTeamView(APIView):
    def get(self,request):
        """ API to list all the teams in the Database"""
        try:
            team_data = TeamsModel.objects.all().values()
            if team_data is not None:
                team_list = [each_team for each_team in team_data]
                return Response(team_list,status=status.HTTP_200_OK)
            else:
                return Response([],status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        """ API to add a new team to the database"""
        data = request.data
        team_name = data['TeamName']
        try:
            query = TeamsModel.objects.all().values('TeamName')
            query_list = [each_query['TeamName'] for each_query in query]
            if team_name not in query_list:
                team_data = TeamsModel(TeamName=team_name)
                team_data.save()
                return Response({"result":{"status":True,"message":"Team Added Successfully"}},status=status.HTTP_200_OK)
            else:
                return Response({"result":{"status":False,"message":"Team Already Exists"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self,request):
        """ API to edit the team in the database"""
        data = request.data
        team_id = data['id']
        try:
            team_query = TeamsModel.objects.get(id=team_id)
            team_query.TeamName = data['TeamName']
            team_query.save()
            return Response({"result":{"status":True,"message":" Team Edited Successfully"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteTeam(APIView):
    def post(self,request):
        """ API to delete the Team in the Database"""
        data = request.data
        team_id = data['id']
        try:
            TeamsModel.objects.get(id=team_id).delete()
            return Response({"result":{"status":True,"message":"Deleted Successfully"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AddVendorView(APIView):
    def get(self,request):
        """ API to list all vendors"""
        try:
            vendor_data = VendorsModel.objects.all().values()
            if vendor_data is not None:
                vendor_list = [each_vendor for each_vendor in vendor_data]
                return Response(vendor_list,status=status.HTTP_200_OK)
            else:
                return Response([],status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        """ API to add new vendor to the database"""
        try:
            data = request.data
            vendor = data['VendorName']
            query = VendorsModel.objects.all().values('VendorName')
            query_list = [each_query['VendorName'] for each_query in query]
            if vendor not in query_list:
                vendor_data = VendorsModel(VendorName=vendor)
                vendor_data.save()
                return Response({"result":{"status":True,"message":"Vendor Added Successfully"}},status=status.HTTP_200_OK)
            else:
                return Response({"result":{"status":False,"message":"Vendor Already Exists"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self,request):
        """ APi to edit the vendor information"""
        data = request.data
        vendor_id = data['id']
        try:
            query = VendorsModel.objects.get(id=vendor_id)
            query.VendorName = data['VendorName']
            query.save()  
            return Response({"result":{"status":True,"message":"Vendor Edited Successfully"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":False,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)    

class DeleteVendor(APIView):
    def post(self,request):
        """ API to delete vendor data from database"""
        data = request.data
        vendor_id = data['id']
        try:
            VendorsModel.objects.get(id=vendor_id).delete()
            return Response({"result":{"status":True,"message":" Venodr Deleted Successfully"}},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result":{"status":True,"message":e}},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AddFunctionView(APIView):
    def get(self, request):
        """API to list all the functions in the database"""
        try:
            function_list = FunctionModel.objects.values('id', 'TeamName__TeamName', 'Function')
            return Response(function_list, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            """API to add a new function to the database"""
            data = request.data
            team_name = data.get('TeamName')
            function_name = data.get('FunctionName')
            team_query, created = TeamsModel.objects.get_or_create(TeamName=team_name)
            if FunctionModel.objects.filter(TeamName=team_query, Function=function_name).exists():
                return Response("Function already exists for this team", status=status.HTTP_400_BAD_REQUEST)
            FunctionModel.objects.create(TeamName=team_query, Function=function_name)
            return Response('Function added successfully', status=status.HTTP_201_CREATED)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"result": {"status": False, "message": str(e)}}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EditDeleteFunctionView(APIView):
    """API for Editing and Deleting Functions"""
    def put(self, request):
        """API for editing a function"""
        data = request.data
        function_id = data.get('id')
        function_name = data.get('Function')
        team_name = data.get('TeamName')
        try:
            if not all([function_id, function_name, team_name]):
                return Response("Missing required parameters", status=status.HTTP_400_BAD_REQUEST)
            function_instance = FunctionModel.objects.get(id=function_id, TeamName__TeamName=team_name)
            function_instance.Function = function_name
            function_instance.save()
            return Response("Function edited successfully", status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """API for deleting a function"""
        data = request.data
        function_id = data.get('id')
        try:
            if not function_id:
                return Response("Function ID is required", status=status.HTTP_400_BAD_REQUEST)
            function_instance = FunctionModel.objects.get(id=function_id)
            function_instance.delete()
            return Response("Function deleted successfully", status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# User-Details

class RoleCheck(APIView):
    def post(self, request):
        idsid = request.data.get('userName')
        try:
            user_details = UserModel.objects.filter(Idsid=idsid).values(
                'Email', 'Name', 'Idsid', 'WWID', 'Badge', 'DisplayName', 'Role__role_name'
            )
            if user_details:
                user_detail = user_details[0]
                response_data = {
                    'emailId': user_detail['Email'],
                    'name': user_detail['Name'],
                    'idsid': user_detail['Idsid'],
                    'wwid': user_detail['WWID'],
                    'employeeBadgeType': user_detail['Badge'],
                    'displayName': user_detail['DisplayName'],
                    'role': user_detail['Role__role_name'],
                    'avatarURL': 'https://photoisa.intel.com/Photo/{}.jpg'.format(user_detail['Email']),
                    'domain': None,
                    'comments': None,
                    'isApplicationAccess': True,
                    'programAccesses': None,
                    'Role': user_detail['Role__role_name']
                }
                return Response(response_data)
            else:
                return Response({'error': 'User not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class AddUserView(APIView):
    def get(self,request):
        """ API to list all users in database"""
        try:
            user_data = UserModel.objects.filter().values('WWID','Idsid','Name','DisplayName','Email','Role__role_name','Badge','LastLoggedOn')
            if user_data:
                user_list = [each_query for each_query in user_data]
                return  Response(user_list,status=status.HTTP_200_OK)
            else:
                return Response("No User data",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self,request):
        """ API to add new user to the database"""
        data = request.data
        WWID = data['wwid']
        Name = data['name']
        Email = data['emailId']
        Role = data['role']
        Idsid = data['idsid']
        Badge = data["employeeBadgeType"]
        DisplayName = data["displayName"]
        try:
            try:
                user_check_query = UserModel.objects.get(WWID=WWID)
                if user_check_query:
                    return Response("User Already Exists",status=status.HTTP_200_OK)
                else:
                    return Response("Cannot check User",status=status.HTTP_200_OK)
            except UserModel.DoesNotExist:
                role_query = UserRolesModel.objects.get(role_name=Role)
                user = UserModel(WWID=WWID,Name=Name,Idsid=Idsid,DisplayName=DisplayName,Email=Email,Role=role_query,Badge=Badge,LastLoggedOn=datetime.now(),CreatedOn=datetime.now(),IsActive=True)
                user.save()
                return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self,request):
        """ API to edit user roles in the database"""
        data = request.data
        WWID = data['WWID']
        Role = data['Role']
        try:
            role_query = UserRolesModel.objects.get(role_name=Role)
            user = UserModel.objects.get(WWID=WWID)
            user.Role=role_query
            user.save()
            user = UserModel.objects.get(WWID=WWID)
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteUserView(APIView):
    def post(self,request):
        """ API to delete a user from database"""
        data = request.data
        WWID = data['WWID']
        try:
            UserModel.objects.get(WWID=WWID).delete()
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AddUserRequestView(APIView):
    def get(self,request):
        """ API to list all user requests"""
        try:
            User_data = UserRequestModel.objects.filter(IsRequested__in=[True]).values('RequestId','WWID','Name','Idsid','DisplayName','Email','Role__role_name','Badge','ApprovedOn','CreatedOn').order_by('-CreatedOn')
            if User_data:
                user_response = [each_user for each_user in User_data]
                return Response(user_response,status=status.HTTP_200_OK)
            else:
                return Response([],status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self, request):
        """ API to add new user request """
        data = request.data
        try:
            WWID = data['wwid']
            Name = data['name']
            Email = data['emailId']
            Role = data['role']
            Idsid = data['idsid']
            Badge = data["employeeBadgeType"]
            DisplayName = data["displayName"]
            try:
                user_check_query = UserModel.objects.get(WWID=WWID)

                id = len(UserRequestModel.objects.filter().values())+1
                if user_check_query:
                    return Response("User Already Exists",status=status.HTTP_200_OK)
                else:
                    return Response("Cannot check User",status=status.HTTP_200_OK)
            except UserModel.DoesNotExist:
                try:
  
                    user_check = UserRequestModel.objects.get(WWID=WWID, status="created")
                    id = len(UserRequestModel.objects.filter().values())+1
                    if user_check:
                        return Response("User Already Exists",status=status.HTTP_200_OK)
                    else:
                        return Response("Cannot check User",status=status.HTTP_200_OK)
                    
                except UserRequestModel.DoesNotExist:
                    role_query = UserRolesModel.objects.get(role_name=Role)
                    if not UserRequestModel.objects.filter():
                        id = 1
                    else: 
                        id = len(UserRequestModel.objects.filter().values())+1
                    user = UserRequestModel(RequestId=id,WWID=WWID,Name=Name,Idsid=Idsid,DisplayName=DisplayName,Email=Email,
                                            Role=role_query,Badge=Badge,ApprovedOn=datetime.now(tz=timezone.utc),
                                            CreatedOn=datetime.now(tz=timezone.utc),ApprovedBy=None,IsActive=True,status='created',
                                            IsAdded=False,IsRequested=True)
                    user.save()
                    message = f"Your Request for Adding the User {WWID} is Recieved "
                    subject = "User Add request Submitted for "
                    mail_data = {
                                "User":Name,
                                "WWID":WWID,
                                "id":id,
                                "Name":Name,
                                "Email":Email,
                                "Role":Role,
                                "message":message,
                                "subject":subject,
                                "id":id,

                            }
                    TO.append(Email)
                    mail = UserModuleMail(From=FROM,To=TO,CC=CC,data=mail_data)
                    mail.sendmail()
                    TO.pop()
                # TO DO: ADD A MAIL TO SEND Request to add user Recieved                 
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # def post(self, request):
    #     """ API to add new user request """
    #     data = request.data
    #     try:
    #         WWID = data['wwid']
    #         Name = data['name']
    #         Email = data['emailId']
    #         Role = data['role']
    #         Idsid = data['idsid']
    #         Badge = data["employeeBadgeType"]
    #         DisplayName = data["displayName"]
    #         try:
    #             print("1")
    #             user_check_query = UserModel.objects.get(WWID=WWID)
    #             print("2")
    #             #user_check = UserRequestModel.objects.get(WWID=WWID)
    #             print(user_check_query)
    #             id = len(UserRequestModel.objects.filter().values())+1
    #             if user_check_query:
    #                 return Response("User Already Exists",status=status.HTTP_200_OK)
    #             else:
    #                 return Response("Cannot check User",status=status.HTTP_200_OK)
    #         except UserModel.DoesNotExist:
    #             try:
    #                 user_check = UserRequestModel.objects.get(WWID=WWID)
    #                 print("2")
    #                 #user_check = UserRequestModel.objects.get(WWID=WWID)
    #                 print(user_check)
    #                 id = len(UserRequestModel.objects.filter().values())+1
    #                 if user_check:
    #                     return Response("User Already Exists",status=status.HTTP_200_OK)
    #                 else:
    #                     return Response("Cannot check User",status=status.HTTP_200_OK)

    #             except UserRequestModel.DoesNOTExist:
    #                 print("5")
    #                 role_query = UserRolesModel.objects.get(role_name=Role)
    #                 if not UserRequestModel.objects.filter():
    #                     id = 1
    #                 else: 
    #                     id = len(UserRequestModel.objects.filter().values())+1
                        
    #                 user = UserRequestModel(RequestId=id,WWID=WWID,Name=Name,Idsid=Idsid,DisplayName=DisplayName,Email=Email,
    #                                             Role=role_query,Badge=Badge,ApprovedOn=datetime.now(),
    #                                             CreatedOn=datetime.now(),ApprovedBy=None,IsActive=True,status='created',
    #                                             IsAdded=False,IsRequested=True)
    #                 user.save()

    #             # role_query = UserRolesModel.objects.get(role_name=Role)
    #             # if not UserRequestModel.objects.filter():
    #             #     id = 1
    #             # else: 
    #             #     id = len(UserRequestModel.objects.filter().values())+1
                    
    #             # user = UserRequestModel(RequestId=id,WWID=WWID,Name=Name,Idsid=Idsid,DisplayName=DisplayName,Email=Email,
    #             #                             Role=role_query,Badge=Badge,ApprovedOn=datetime.now(),
    #             #                             CreatedOn=datetime.now(),ApprovedBy=None,IsActive=True,status='created',
    #             #                             IsAdded=False,IsRequested=True)
                
    #             # message = f"Your Request for Adding the User {WWID} is Recieved "
    #             # subject = "User Add request Submitted for "
    #             # mail_data = {
    #             #             "User":Name,
    #             #             "WWID":WWID,
    #             #             "id":id,
    #             #             "Name":Name,
    #             #             "Email":Email,
    #             #             "Role":Role,
    #             #             "message":message,
    #             #             "subject":subject,
    #             #             "id":id,
    #             #         }
    #             # TO.append(Email)
    #             # user.save()
    #             # mail = UserModuleMail(From=FROM,To=TO,CC=CC,data=mail_data)
    #             # mail.sendmail()
    #             # TO.pop()
    #             # TO DO: ADD A MAIL TO SEND Request to add user Recieved. 
    #         return Response("Success",status=status.HTTP_200_OK)
    #     except Exception as e:
    #         logger_error.error(str(e))
    #         return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetUserRoles(APIView):
    def get(self,request):
        """ APi to list all roles in the database"""
        try:
            user_roles = UserRolesModel.objects.filter().values('role_name')
            user_roles = [each_role['role_name'] for each_role in user_roles]
            return Response({"Roles":user_roles},status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CurrentUserDataView(APIView):
    def post(self,request):
        """ API to get the current user who is accessing the application"""
        data = request.data
        token = data['token']
        user_data = GetUserData(token)
        idsid = user_data['idsid']
        try:
            user_details = UserModel.objects.filter(Idsid=idsid).values('Role__role_name')
            if user_details:
                user_data['Role'] = user_details[0]['Role__role_name']
                user_data_update = UserModel.objects.get(Idsid=idsid)
                user_data_update.LastLoggedOn=timezone.now()
                user_data_update.save()
                try:
                    approver_user_query = ApproverUserModel.objects.get(Idsid=idsid)
                    approver_user_query.LastLoggedOn=timezone.now()
                    approver_user_query.save()
                except ApproverUserModel.DoesNotExist:
                    pass
                return Response(user_data,status=status.HTTP_200_OK)
            else:
                user_data['Role'] = None
                return Response(user_data,status=status.HTTP_200_OK)
        except UserModel.DoesNotExist:
            logger_error.error(str("User Not Exist"))
            return Response("User Not Exist",status=status.HTTP_404_NOT_FOUND)

# Approver's-Detail
class ApproveUserView(APIView):
    def post(self,request):
        """ API to approve the user requests"""
        each_data = request.data
        try:
            for data in each_data:
                id = data['RequestId']
                approved_by = data['ApprovedBy']
                user_request_data  = UserRequestModel.objects.get(RequestId=id)
                user_request_data.ApprovedBy = approved_by
                user_request_data.ApprovedOn = timezone.localtime()
                role_id = user_request_data.Role_id
                user_request_data.status='approved'
                user_request_data.IsAdded=True
                user_request_data.IsRequested=False
                user_request_data.save()
                role = UserRolesModel.objects.get(role_id=role_id)
                role_name = role.role_name
                try:
                    existing_user_check = UserModel.objects.get(WWID=user_request_data.WWID)
                    if existing_user_check:
                        return Response("Success",status=status.HTTP_200_OK)
                except UserModel.DoesNotExist:
                    WWID = user_request_data.WWID
                    Name = user_request_data.Name
                    Idsid=user_request_data.Idsid
                    DisplayName=user_request_data.DisplayName
                    Email=user_request_data.Email
                    Badge = user_request_data.Badge
                    add_user_data = UserModel(WWID=WWID,Name=Name,
                            Idsid=Idsid,DisplayName=DisplayName,
                            Email=Email,Role = role,Badge=Badge,
                            LastLoggedOn=timezone.localtime(),CreatedOn=timezone.localtime(),IsActive=True)
                    message = f"Your Request for Adding the User {WWID} is Approved by {approved_by}  "
                    subject = "User Add request Approved for "
                    mail_data = {
                            "User":Name,
                            "WWID":WWID,
                            "id":id,
                            "Name":Name,
                            "Email":Email,
                            "Role":role_name,
                            "message":message,
                            "subject":subject,
                            "id":id,
                        }
                    TO.append(Email)
                    add_user_data.save()
                    user_request_data.save()
                    mail = UserModuleMail(From=FROM,To=TO,CC=CC,data=mail_data)
                    mail.sendmail()
                    TO.pop()
                    # To CReaTE a Mail that request is approved
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RejectUserView(APIView):
    def post(self,request):
        """ API to reject the user request """
        each_data = request.data
        try:
            for data in each_data:
                id = data['RequestId']
                approved_by = data['ApprovedBy']
                reason = data['Reason']
                user_request_data  = UserRequestModel.objects.get(RequestId=id)
                role_data = UserRolesModel.objects.get(role_id=user_request_data.Role_id)
                user_request_data.ApprovedBy = approved_by
                user_request_data.Reason = reason
                user_request_data.IsRequested = False
                user_request_data.status = 'rejected'
                user_request_data.save()
                WWID = user_request_data.WWID
                Name = user_request_data.Name
                Email=user_request_data.Email
                message = f"Your Request for Adding the User {WWID} is <b> Rejected </b> by {approved_by} for reason <b>{reason}</b> "
                subject = "User Add request Rejected for "
                mail_data = {
                            "User":Name,
                            "WWID":WWID,
                            "id":id,
                            "Name":Name,
                            "Email":Email,
                            "Role":role_data.role_name,
                            "message":message,
                            "subject":subject,
                            "id":id,
                        }
                TO.append(Email)
                user_request_data.save()
                mail = UserModuleMail(From=FROM,To=TO,CC=CC,data=mail_data)
                mail.sendmail()
                TO.pop()
                UserRequestModel.objects.get(RequestId=id).delete()

            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Suggestions Page
class GetSuggestionsView(APIView):
    def post(self,request):
        """ APi to get the suggestions based on WWID"""
        try:
            WWID = request.data['wwid']
            role = request.data['Role']
            if role!='Admin':
                query = SuggestionsModel.objects.filter(suggestion_by={'WWID':WWID}).values('id','suggestion_by','created_date','suggestion','status','resolved_date','closing_comments')
            else:
                query = SuggestionsModel.objects.filter().values('id','suggestion_by','created_date','suggestion','status','resolved_date','closing_comments')
            return Response(query,status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SuggestionsView(APIView):        
    def post(self,request):
        """ API to add new suggestion"""
        try:
            data = request.data
            suggestion_by = data['SuggestionBy']
            suggestion = data['Suggestion']
            id  = len(SuggestionsModel.objects.filter())+1
            suggestion_data = SuggestionsModel(id=id,suggestion_by=suggestion_by,suggestion=suggestion,\
                                               status='Open',created_date=timezone.now(),resolved_date=None)
            message = f"<p> Thank you for your valuable feedback on LabSpaceManagement Tool.<p>\
            <p> Your feedback has been Recieved <p>\
            <p style ='color:red'><b> Feedback: </b>{suggestion}</p>\
            "
            subject = "Suggestion for Improvement from "
            Email = suggestion_by[0]['Email']
            mail_data = {
                            "User":suggestion_by[0]['Name'],
                            "WWID":suggestion_by[0]['WWID'],
                            "id":id,
                            "Name":suggestion_by[0]['Name'],
                            "message":message,
                            "subject":subject,
                            "id":id,
                        }
            TO.append(Email)
            mail = SuggestionsMail(From=FROM,To=TO,CC=CC,data=mail_data)
            mail.sendmail()
            suggestion_data.save()
            TO.pop()
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self,request):
        "API to edit the status of the suggestion"
        try:
            data = request.data
            id = data['id']
            comment_status = data['status']
            closing_comment = data['comments']
            query = SuggestionsModel.objects.get(id=id)
            query.status=comment_status
            query.closing_comments = closing_comment
            query.resolved_date = timezone.now()
            query.save()
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetAllocationView(APIView):
    def post(self, request):
        """ API to list all allocations for given id"""
        try:
            id = request.data['id']
            allocation_request = AllocationDetailsModel.objects.filter(id=id).values('id','Program','Sku','Vendor','FromWW',
            'ToWW','Duration','AllocatedTo','NotifyTo','NumberOfbenches','Remarks','Team','IsAllocated','IsRequested','Location__Name','BenchData','AllocatedDate','status','Department','Function')
            allocation_response = [each_allocation for each_allocation in allocation_request]
            return Response(allocation_response,status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ValidateUserMail(APIView):
    def post(self,request):
        """ Validate the user emails in the CC field while booking benches """
        try:
            mail = request.data['mail']
            response_mail = str(validate_user_mail(mail))
            response_dict = {
                "emailId": str(response_mail),
                "name": None,
                "idsid": None,
                "wwid": None,
                "employeeBadgeType": None,
                "avatarURL": None,
                "role": None,
                "domain": None,
                "comments": None,
                "displayName": None,
                "isApplicationAccess": False,
                "programAccesses": None
            }
            return Response(response_dict,status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(e)
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExtendAllocation(APIView):
    def post(self, request):
        """ API to extend the bench """
        data = request.data
        try:
            id = data['id']
            location = data['LabName']
            toWW = data['ToWW']
            duration=data['Duration']
            remarks = data['Remarks']
            allocation_query = AllocationDetailsModel.objects.get(id=id)
            BenchData = allocation_query.BenchData
            if allocation_query.status == 'allocated':
                allocation_query.ToWW = toWW
                allocation_query.Duration=duration
                allocation_query.AllocatedDate = timezone.now()
                allocation_query.Remarks = remarks
                allocation_query.save()
                
            lab_query = LabModel.objects.get(Q(Name=location))
            for each_bench_request in BenchData:
                for each_bench_row in lab_query.BenchDetails:
                    for each_bench_column_no in range(len(each_bench_row['seats'])):
                        if each_bench_row['seats'][each_bench_column_no]['labelNo'] == each_bench_request and \
                            allocation_query.status =='allocated':
                            each_bench_row['seats'][each_bench_column_no]['IsRequested'] = False
                            each_bench_row['seats'][each_bench_column_no]['IsAllocated'] = True
                            if each_bench_row['seats'][each_bench_column_no]['AllocationData'] is not None:
                                each_bench_row['seats'][each_bench_column_no]['AllocationData'][0]['ToWW'] = str(toWW)
                            lab_query.save()
                            
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# FORECAST PAGE APIS
class BoardAPI(APIView):
    queryset = BoardAllocationDataModel.objects.all()
    def get(self, request, id=None):
        if id is None:
            # If no 'id' is provided, retrieve all items
            data = BoardAllocationDataModel.objects.all()
            serializer = BoardAllocationDataModelSerializer(data, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Retrieve a specific record by its ID
            try:
                board = self.queryset.get(pk=id)
                # Convert OrderedDict fields to JSON in the serializer
                serializer = BoardAllocationDataModelSerializer(board)
                response_data = serializer.data

                return Response(response_data, status=status.HTTP_200_OK)
            except BoardAllocationDataModel.DoesNotExist:
                return Response("Record not found", status=status.HTTP_404_NOT_FOUND)
    def put(self, request, id):
        # Update an existing record by its ID using a PUT request
        try:
            board = self.queryset.get(pk=id)
            # Remove fields from request data that should not be updated
            fields_to_exclude = ["createdBy", "createdDate", "modifiedBy", "modifiedDate", "deletedBy", "deletedDate", "isdeleted"]
            cleaned_request_data = {key: value for key, value in request.data.items() if key not in fields_to_exclude}
            # Check for duplicates based on the updated data (excluding specified fields)
            existing_records = BoardAllocationDataModel.objects.exclude(pk=id).filter(
                Q(Program=cleaned_request_data['Program']) & Q(Sku=cleaned_request_data['Sku']) & Q(Team=cleaned_request_data['Team']) & Q(Vendor=cleaned_request_data['Vendor']) &
                Q(TotalBoard=cleaned_request_data['TotalBoard']) & Q(year=cleaned_request_data['year'])
            )
            for record in existing_records:
                if all(record.__dict__[month] == cleaned_request_data[month] for month in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']):
                    # Duplicate record found, return a response with a duplicate message
                    return Response("Duplicate record found", status=status.HTTP_200_OK)
            # If no duplicate was found or if the record being updated matches itself, proceed with the update
            serializer = BoardAllocationDataModelSerializer(board, data=cleaned_request_data)
            if serializer.is_valid():
                serializer.save()
                return Response("Updated Successfully", status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BoardAllocationDataModel.DoesNotExist:
            return Response("Record not found", status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        """ API to add new board allocation data """
        try:
            program = request.data['Program']
            sku = request.data['Sku']
            team = request.data['Team']
            vendor = request.data['Vendor']
            total_board = request.data['TotalBoard']
            year = request.data['year']

            existing_records = BoardAllocationDataModel.objects.filter(
                Q(Program=program) & Q(Sku=sku) & Q(Team=team) & Q(Vendor=vendor) & Q(TotalBoard=total_board) & Q(year=year)
            )
            for record in existing_records:
                # Check for duplicates based on month-specific data
                if all(record.__dict__[month] == request.data[month] for month in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']):
                    # Duplicate record found, return a response with a duplicate message
                    return Response("Duplicate record found", status=status.HTTP_200_OK)
            # If the loop did not break, it means no duplicate was found, insert the record
            serializer = BoardAllocationDataModelSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()  # Save the data to the database
                return Response("Added Successfully", status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    def delete(self, request, id):
        # Delete a specific record by its ID
        try:
            instance = BoardAllocationDataModel.objects.get(pk=id)
            instance.isdeleted = True
            instance.save()
            response_data = 'Record deleted successfully'
            return Response(response_data, status=status.HTTP_200_OK)
        except BoardAllocationDataModel.DoesNotExist:
            return Response('Record not found', status=status.HTTP_404_NOT_FOUND)

class excelUpload(APIView):       
    def recursive_dict_compare(self, dict1, dict2, exclude_keys=None):
        if exclude_keys is None:
            exclude_keys = ["createdBy", "createdDate", "modifiedBy", "modifiedDate", "deletedBy", "deletedDate", "isdeleted"]
        for key, value in dict1.items():
            if key not in dict2:
                return False
            if key in exclude_keys:
                continue  # Skip comparison for excluded keys
            if isinstance(value, dict):
                if not self.recursive_dict_compare(value, dict2[key], exclude_keys):
                    return False
            elif value != dict2[key]:
                return False
        return True

    def post(self, request):
        try:
            excel_data_array = request.data
            response_data = {'inserted': 0, 'duplicates': 0}

            for item_data in excel_data_array:
                existing_record = BoardAllocationDataModel.objects.filter(
                    Program=item_data['Program'],
                    Sku=item_data['Sku'],
                    Team=item_data['Team'],
                    Vendor=item_data['Vendor'],
                    TotalBoard=item_data['TotalBoard'],
                    year=item_data['year'],
                )
                for record in existing_record:
                    if self.recursive_dict_compare(item_data, record.__dict__, exclude_keys=["createdBy", "createdDate", "modifiedBy", "modifiedDate", "deletedBy", "deletedDate", "isdeleted"]):
                        for month, values in item_data.items():
                            if isinstance(values, dict):
                                for field, val in values.items():
                                    setattr(record, f"{month}_{field}", val)
                        record.save()
                        response_data['duplicates'] += 1
                        break
                else:
                    serializer = BoardAllocationDataModelSerializer(data=item_data)
                    if serializer.is_valid():
                        serializer.save()
                        response_data['inserted'] += 1
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            if response_data['duplicates'] > 0:
                response_message = {'message': f'{response_data["duplicates"]} duplicate record(s) and {response_data["inserted"]} records inserted'}
            else:
                response_message = {'message': f'{response_data["inserted"]} record(s) inserted'}
            return Response(response_message, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        
class YearListAPI(APIView):
    def get(self, request):
        years = sorted(BoardAllocationDataModel.objects.values_list('year', flat=True).distinct())
        current_year = datetime.now().year
        year_data = {}
        for year in years:
            data = BoardAllocationDataModel.objects.filter(year=year)
            serializer = BoardAllocationDataModelSerializer(data, many=True)
            year_data[str(year)] = serializer.data
        # Check if the current year's data is available, if not, return an empty list for that year
        if current_year not in years:
            year_data[str(current_year)] = []
        return Response(year_data, status=status.HTTP_200_OK)
    
class YearWiseData(APIView):  
    def post(self, request):
        # Get the year from the request data
        try:
            year = request.data.get('year') 
            if not year:
                return Response("Year not provided in the request data", status=status.HTTP_400_BAD_REQUEST)        
            data = BoardAllocationDataModel.objects.filter(year=year)
            serializer = BoardAllocationDataModelSerializer(data, many=True)
            serialized_data = serializer.data  # Convert queryset to list of dictionaries
            filtered_data = [item for item in serialized_data if not item['isdeleted']]
            return Response(filtered_data, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class ForecastSummary(APIView):
    def get_allocated_count(self, lab_names_list):
        allocated_count = 0
        for each_location in lab_names_list:
            lab_data = LabModel.objects.filter(Name__icontains=each_location)
            for each_lab in lab_data:
                if (each_lab.BenchDetails is not None) and ("TOE" not in each_lab.Name):
                    for each_row_no in range(len(each_lab.BenchDetails)):
                        for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] and \
                                    each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
                                allocated_count += 1
                            elif not each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] and \
                                    each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
                                # Include free seats in the count
                                allocated_count += 1
        return allocated_count

    def process_record(self, records, allocated_count, year):
        current_year = datetime.now().year
        monthly_data = [
            {
                "category": month,
                "intel": sum(int(record[month]['boardsIntelBench'] or 0) + int(record[month]['boardIntelRack'] or 0) for record in records),
                "ODC": sum(int(record[month]['boardsODCBench'] or 0) + int(record[month]['boardsODCRack'] or 0) for record in records),
                "WSE_BENCH_Allocation": allocated_count if int(year) == current_year else 0,
                "Bench_Demand_Intel": sum(int(record[month]['boardsIntelBench'] or 0) for record in records),
                "Rack_Demand_Intel": sum(int(record[month]['boardIntelRack'] or 0) for record in records),
                "Bench_Demand_ODC": sum(int(record[month]['boardsODCBench'] or 0) for record in records),
                "Rack_Demand_ODC": sum(int(record[month]['boardsODCRack'] or 0) for record in records),
                "Total_Bench_Intel" :round(sum(int(record[month]['boardsIntelBench'] or 0) / 1.5 for record in records)),
                "Total_Rack_Intel" : 0,
            }
            for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        ]
        total_board_sum = sum(int(record.get('TotalBoard', 0)) for record in records)
        intel_count = sum(month_data["intel"] for month_data in monthly_data)
        odc_count = sum(month_data["ODC"] for month_data in monthly_data)
        result = {
            year: monthly_data,
            "TotalBoard": total_board_sum,
            "Intel_count":intel_count,
            "ODC_count":odc_count,
        }
        return result

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            year = data.get('year', 2023)  # Default year is 2023
            program = data.get('Program', 'All')
            sku = data.get('Sku', 'All')
            # team = data.get('Team', 'All')
            id = data.get('id')

            lab_filter_query = LabModel.objects.filter().values('Name')
            lab_filter_query_list = [each_query['Name'] for each_query in lab_filter_query if "TOE" not in each_query['Name']]
            lab_data = LabModel.objects.filter(Name__in=lab_filter_query_list).values('Name')
            lab_names_list = sorted(list(set(['-'.join(str(each_lab['Name']).split('-')[0:2]) for each_lab in lab_data])))

            allocated_count = self.get_allocated_count(lab_names_list)

            if id is not None:
                try:
                    board = BoardAllocationDataModel.objects.get(pk=id, year=year)
                    serializer = BoardAllocationDataModelSerializer(board)
                    response_data = serializer.data
                    return Response(self.process_record([response_data], allocated_count, year), status=status.HTTP_200_OK)
                except BoardAllocationDataModel.DoesNotExist:
                    return Response("Record not found for the specified year", status=status.HTTP_404_NOT_FOUND)
            else:
                if program == 'All':
                    data = BoardAllocationDataModel.objects.filter(year=year)
                else:
                    data = BoardAllocationDataModel.objects.filter(year=year, Program=program)

                if sku != 'All':
                    data = data.filter(Sku=sku)

                # if team != 'All':
                #     data = data.filter(Team=team)

                serializer = BoardAllocationDataModelSerializer(data, many=True)
                serialized_data = serializer.data
                filtered_data = [item for item in serialized_data if not item.get('isdeleted', False)]

                if not data.exists():
                    empty_data = self.process_empty_record(year)
                    return Response(empty_data, status=status.HTTP_200_OK)

                combined_record = self.process_record(filtered_data, allocated_count, year)
                return Response(combined_record, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def process_empty_record(self, year):
        empty_data = [
            {
                "category": month,
                "intel": 0,
                "ODC": 0,
                "WSE_BENCH_Allocation": 0,
                "Bench_Demand_Intel": 0,
                "Rack_Demand_Intel": 0,
                "Bench_Demand_ODC": 0,
                "Rack_Demand_ODC": 0,
                "Total_Bench_Intel":0,
                "Total_Rack_Intel":0
            }
            for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        ]
        total_board_sum = 0
        result = {
            year: empty_data,
            "TotalBoard": total_board_sum
        }
        return result

        
class ForecastSummaryRVP(APIView):
    def process_record(self, records):
        result = []
        monthly_totals = {month: {'Bench_Demand_Intel': 0, 'Rack_Demand_Intel': 0, 'Bench_Demand_ODC': 0, 'Rack_Demand_ODC': 0, 'Total': 0} for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
        for record in records:
            for month in monthly_totals:
                monthly_totals[month]['Total'] += sum(int(record[month][key] or 0) for key in ['boardsIntelBench', 'boardIntelRack', 'boardsODCBench', 'boardsODCRack'])
                monthly_totals[month]['Bench_Demand_Intel'] += int(record[month]['boardsIntelBench'] or 0)
                monthly_totals[month]['Rack_Demand_Intel'] += int(record[month]['boardIntelRack'] or 0)
                monthly_totals[month]['Bench_Demand_ODC'] += int(record[month]['boardsODCBench'] or 0)
                monthly_totals[month]['Rack_Demand_ODC'] += int(record[month]['boardsODCRack'] or 0)
        for month, total_data in monthly_totals.items():
            result.append({
                "category": month,
                "Bench_Demand_Intel": total_data['Bench_Demand_Intel'],
                "Rack_Demand_Intel": total_data['Rack_Demand_Intel'],
                "Bench_Demand_ODC": total_data['Bench_Demand_ODC'],
                "Rack_Demand_ODC": total_data['Rack_Demand_ODC'],
                # "intel": sum(int(record[month]['boardsIntelBench'] or 0) + int(record[month]['boardIntelRack'] or 0) for record in records),
                # "ODC": sum(int(record[month]['boardsODCBench'] or 0) + int(record[month]['boardsODCRack'] or 0) for record in records),
                "Total": total_data['Total'],
                "Total_Bench_Intel" :round(sum(int(record[month]['boardsIntelBench'] or 0) / 1.5 for record in records)),
                "Total_Rack_Intel" : 0,
            })
        return result

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            year = data.get('year', '2023')
            program = data.get('Program', 'All')
            sku = data.get('Sku', 'All')
            # team=data.get('Team','ALl')
            board_id = data.get('id')

            if board_id is not None:
                try:
                    board = BoardAllocationDataModel.objects.get(pk=board_id)
                    serializer = BoardAllocationDataModelSerializer(board)
                    response_data = [serializer.data]
                except BoardAllocationDataModel.DoesNotExist:
                    return Response("Record not found", status=status.HTTP_404_NOT_FOUND)
            else:
                if program == 'All':
                    data = BoardAllocationDataModel.objects.filter(year=year)
                else:
                    data = BoardAllocationDataModel.objects.filter(year=year, Program=program)

                if sku != 'All':
                    data = data.filter(Sku=sku)

                # if team != 'All':
                #     data = data.filter(Team=team)
                # Check if there is any data for the specified year
                if not data.exists():
                    return Response({year: []}, status=status.HTTP_200_OK)
                serializer = BoardAllocationDataModelSerializer(data, many=True)
                serialized_data = serializer.data  # Convert queryset to list of dictionaries
                filtered_data = [item for item in serialized_data if not item['isdeleted']]
                response_data = filtered_data

            output_data = {year: self.process_record(response_data)}
            return Response(output_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ForecastSummaryTable(APIView):
    def call_api(self):
        url = "https://labspaceapi.apps1-bg-int.icloud.intel.com/home/GetDrillDownChartData/"
        try:
            response = requests.get(url, verify=False)
            if response.status_code == 200:
                data = response.json()
                # Filter data for categories "Free" and "Allocated"
                filtered_data = [item for item in data if item["category"] in ["Free", "Allocated"]]
                return filtered_data
            else:
                print("Failed to call API:", response.status_code)
                return None
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return None

    def process_record(self, records, total_sum):
        result = []
        monthly_totals = {month: {'Bench_Demand_Intel': 0, 'Rack_Demand_Intel': 0, 'Bench_Demand_ODC': 0, 'Rack_Demand_ODC': 0, 'Total': 0} for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
                
        for record in records:
            for month in monthly_totals:
                monthly_totals[month]['Bench_Demand_Intel'] += int(record[month]['boardsIntelBench'] or 0)
                monthly_totals[month]['Rack_Demand_Intel'] += int(record[month]['boardIntelRack'] or 0)
                monthly_totals[month]['Bench_Demand_ODC'] += int(record[month]['boardsODCBench'] or 0)
                monthly_totals[month]['Rack_Demand_ODC'] += int(record[month]['boardsODCRack'] or 0)
                monthly_totals[month]['Total'] += sum(int(record[month][key] or 0) for key in ['boardsIntelBench', 'boardIntelRack', 'boardsODCBench', 'boardsODCRack'])
        for month, total_data in monthly_totals.items():
            total = total_data['Total']
            result.append({
                "category": month,
                "Bench_Demand_Intel": total_data['Bench_Demand_Intel'],
                "Rack_Demand_Intel": total_data['Rack_Demand_Intel'],
                "Bench_Demand_ODC": total_data['Bench_Demand_ODC'],
                "Rack_Demand_ODC": total_data['Rack_Demand_ODC'],
                "Total": total,
                "Intel_percentage": f"{round((total_data['Bench_Demand_Intel'] + total_data['Rack_Demand_Intel']) / total * 100, 2)}%" if total != 0 else "0%",
                "ODC_percentage": f"{round((total_data['Bench_Demand_ODC'] + total_data['Rack_Demand_ODC']) / total * 100, 2)}%" if total != 0 else "0%",
                "Total_Bench_Intel" : round(total_data['Bench_Demand_Intel'] / 2),
                "Total_Rack_Intel" : 0,
                "WSE_BENCH_allocation": total_sum,  # Use the total_sum here
                "GAP/Demand": round(total_data['Bench_Demand_Intel'] / 1.5) - total_sum
            })
        return result

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            year = data.get('year', '2023')
            board_id = data.get('id')
            programs = data.get('Program', 'All').split(',')
            skus = data.get('Sku', 'All').split(',')
            teams = data.get('Team','All').split(',')
            if board_id is not None:
                try:
                    board = BoardAllocationDataModel.objects.get(pk=board_id)
                    serializer = BoardAllocationDataModelSerializer(board)
                    response_data = [serializer.data]
                except BoardAllocationDataModel.DoesNotExist:
                    return Response("Record not found", status=status.HTTP_404_NOT_FOUND)
            else:
                data = BoardAllocationDataModel.objects.filter(year=year)
                if 'All' not in programs:
                    program_filters = Q()
                    for program in programs:
                        program_filters |= Q(Program=program)
                    data = data.filter(program_filters)

                if 'All' not in skus:
                    sku_filters = Q()
                    for sku in skus:
                        sku_filters |= Q(Sku=sku)
                    data = data.filter(sku_filters)

                if 'All' not in teams:
                    team_filters = Q()
                    for team in teams:
                        team_filters |= Q(Team=team)
                    data = data.filter(team_filters)
                # Check if there is any data for the specified year
                if not data.exists():
                    # Return empty data for the specified year
                    empty_data = self.process_empty_record(year)
                    return Response(empty_data, status=status.HTTP_200_OK)
                serializer = BoardAllocationDataModelSerializer(data, many=True)
                serialized_data = serializer.data  # Convert queryset to list of dictionaries
                filtered_data = [item for item in serialized_data if not item['isdeleted']]
                response_data = filtered_data
            # Calculate the total_sum using call_api() function
            api_data = self.call_api()
            total_sum = sum(item["value"] for item in api_data) if api_data else 0
            output_data = {year: self.process_record(response_data, total_sum)}
            return Response(output_data, status=status.HTTP_201_CREATED)
        except ObjectDoesNotExist:
            return Response("Record not found", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def process_empty_record(self, year):
        empty_data = [
            {
                "category": month,
                "Bench_Demand_Intel": 0,
                "Rack_Demand_Intel": 0,
                "Bench_Demand_ODC": 0,
                "Rack_Demand_ODC": 0,
                "Total": 0,
                "Intel_percentage": "0%",
                "ODC_percentage":"0%",
                "Total_Bench_Intel" : 0,
                "Total_Rack_Intel" : 0,
                "WSE_BENCH_allocation": 0,
                "GAP/Demand": 0
            }
            for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        ]
        result = {
            year: empty_data
        }
        return result

        
class ForecastQuaterWiseSummary(APIView):
    def process_record(self, records, year):
        quarterly_data = {
            "Q1": {"intel": 0, "ODC": 0,"Bench_Demand_Intel":0,"Rack_Demand_Intel":0,"Bench_Demand_ODC":0,"Rack_Demand_ODC":0},
            "Q2": {"intel": 0, "ODC": 0,"Bench_Demand_Intel":0,"Rack_Demand_Intel":0,"Bench_Demand_ODC":0,"Rack_Demand_ODC":0},
            "Q3": {"intel": 0, "ODC": 0,"Bench_Demand_Intel":0,"Rack_Demand_Intel":0,"Bench_Demand_ODC":0,"Rack_Demand_ODC":0},
            "Q4": {"intel": 0, "ODC": 0,"Bench_Demand_Intel":0,"Rack_Demand_Intel":0,"Bench_Demand_ODC":0,"Rack_Demand_ODC":0},
        }
        for record in records:
            if record["year"] == year:
                for quarter, months in [("Q1", ["January", "February", "March"]),
                                        ("Q2", ["April", "May", "June"]),
                                        ("Q3", ["July", "August", "September"]),
                                        ("Q4", ["October", "November", "December"])]:
                    for month in months:
                        # Handle potential empty strings during conversion to integers
                        quarterly_data[quarter]["intel"] += int(record[month]['boardsIntelBench'] or 0) + int(record[month]['boardIntelRack'] or 0)
                        quarterly_data[quarter]["ODC"] += int(record[month]['boardsODCBench'] or 0) + int(record[month]['boardsODCRack'] or 0)
                        quarterly_data[quarter]["Bench_Demand_Intel"] += int(record[month]['boardsIntelBench'] or 0)
                        quarterly_data[quarter]["Rack_Demand_Intel"] += int(record[month]['boardIntelRack'] or 0)
                        quarterly_data[quarter]["Bench_Demand_ODC"] += int(record[month]['boardsODCBench'] or 0)
                        quarterly_data[quarter]["Rack_Demand_ODC"] += int(record[month]['boardsODCRack'] or 0)
        result = {
            year: [
                {
                    "category": quarter,
                    "intel": quarterly_data[quarter]["intel"],
                    "intel_average_value": int(quarterly_data[quarter]["intel"] / 3),
                    "intel_average_percentage": round((int(quarterly_data[quarter]["intel"] / 3) / (quarterly_data[quarter]["intel"] / 3 + quarterly_data[quarter]["ODC"] / 3)) * 100, 2) if quarterly_data[quarter]["intel"] != 0 else 0,
                    "ODC": quarterly_data[quarter]["ODC"],
                    "ODC": quarterly_data[quarter]["ODC"],
                    "ODC_average_value": int(quarterly_data[quarter]["ODC"] / 3),
                    "ODC_average_percentage": round((int(quarterly_data[quarter]["ODC"] / 3) / (quarterly_data[quarter]["intel"] / 3 + quarterly_data[quarter]["ODC"] / 3)) * 100, 2) if quarterly_data[quarter]["ODC"] != 0 else 0,
                    "Bench_Demand_Intel":quarterly_data[quarter]["Bench_Demand_Intel"],
                    "Rack_Demand_Intel":quarterly_data[quarter]["Rack_Demand_Intel"],
                    "Bench_Demand_ODC":quarterly_data[quarter]["Bench_Demand_ODC"],
                    "Rack_Demand_ODC":quarterly_data[quarter]["Rack_Demand_ODC"],
                    "intel_percentage": round((quarterly_data[quarter]["intel"] / (quarterly_data[quarter]["intel"] + quarterly_data[quarter]["ODC"])) * 100,2) if (quarterly_data[quarter]["intel"] + quarterly_data[quarter]["ODC"]) != 0 else 0,
                    "ODC_percentage": round((quarterly_data[quarter]["ODC"] / (quarterly_data[quarter]["intel"] + quarterly_data[quarter]["ODC"])) * 100, 2) if (quarterly_data[quarter]["intel"] + quarterly_data[quarter]["ODC"]) != 0 else 0,
                    "Total_Bench_Intel" :round(quarterly_data[quarter]["Bench_Demand_Intel"]  / 1.5),
                    "Total_Rack_Intel" : 0,
                }
                for quarter in ["Q1", "Q2", "Q3", "Q4"]
            ]
        }

        if not result[year]:
            return {}
        return result
    
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            year = data.get('year', '2023')
            board_id = data.get('id')
            program = data.get('Program', 'All')
            sku = data.get('Sku', 'All')
            # team = data.get('Team','All')
            if board_id is not None:
                try:
                    board = BoardAllocationDataModel.objects.get(pk=board_id)
                    serializer = BoardAllocationDataModelSerializer(board)
                    response_data = serializer.data
                    return Response(self.process_record([response_data], year), status=status.HTTP_200_OK)
                except BoardAllocationDataModel.DoesNotExist:
                    return Response("Record not found", status=status.HTTP_404_NOT_FOUND)
            else:
                if program == 'All':
                    data = BoardAllocationDataModel.objects.filter(year=year)
                else:
                    data = BoardAllocationDataModel.objects.filter(year=year, Program=program)

                if sku != 'All':
                    data = data.filter(Sku=sku)

                # if team != 'All':
                #     data = data.filter(Team=team)
                if not data.exists():
                    return Response({year: []}, status=status.HTTP_200_OK)

                serializer = BoardAllocationDataModelSerializer(data, many=True)
                serialized_data = serializer.data  # Convert queryset to list of dictionaries
                filtered_data = [item for item in serialized_data if not item['isdeleted']]

                # Combine records into a single dictionary
                combined_record = self.process_record(filtered_data, year)

                return Response(combined_record, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GetProgramList(APIView):
    def post(self, request):
        try:
            data = request.data
            year = data.get('year', '2023')
            if year:
                program_data = BoardAllocationDataModel.objects.filter(year=year).values('Program')
            else:
                program_data = BoardAllocationDataModel.objects.all().values('Program')
            program_list = set([each_program['Program'] for each_program in program_data])
            return Response({"Program": program_list}, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GetFunctionList(APIView):
    def post(self, request):
        try:
            data = request.data
            year = data.get('year', '2023')
            program = data.get('Program', 'All')
            sku = data.get('Sku', 'All')

            # Filtering based on input parameters
            if program != 'All' and sku != 'All':
                team_data = BoardAllocationDataModel.objects.filter(year=year, Program=program, Sku=sku).values('Team')
            elif program != 'All':
                team_data = BoardAllocationDataModel.objects.filter(year=year, Program=program).values('Team')
            elif sku != 'All':
                team_data = BoardAllocationDataModel.objects.filter(year=year, Sku=sku).values('Team')
            else:
                team_data = BoardAllocationDataModel.objects.filter(year=year).values('Team')

            # Extracting unique team names
            team_list = set([each_program['Team'] for each_program in team_data])

            return Response({"Team": list(team_list)}, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
class GetSkuList(APIView):
    def post(self, request):
        try:
            data = request.data
            year = data.get('year', 2023)  # Default year is 2023 if not provided
            program = data.get('Program', 'All')
            
            if program == 'All':
                program_data = BoardAllocationDataModel.objects.filter(year=year).values('Sku')
            else:
                program_data = BoardAllocationDataModel.objects.filter(year=year, Program=program).values('Sku')
                
            program_list = set([each_program['Sku'] for each_program in program_data])
            return Response({"Sku": program_list}, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class YearWiseComparison(APIView):
    def post(self, request):
        try:
            data = request.data
            fromyear = data.get('fromyear')
            toyear = data.get('toyear')
            program = data.get('Program', 'All')
            sku = data.get('Sku', 'All')
            team = data.get('Team', 'All')

            # Filter data based on provided parameters
            queryset = BoardAllocationDataModel.objects.all()
            if fromyear:
                queryset = queryset.filter(year__gte=fromyear)
            if toyear:
                queryset = queryset.filter(year__lte=toyear)
            if program != 'All':
                queryset = queryset.filter(Program=program)
            if sku != 'All':
                queryset = queryset.filter(Sku=sku)
            if team != 'All':
                queryset = queryset.filter(Team=team)

            # Retrieve unique sets of programs, SKUs, and teams
            program_list = queryset.values_list('Program', flat=True).distinct()
            sku_list = queryset.values_list('Sku', flat=True).distinct()
            team_list = queryset.values_list('Team', flat=True).distinct()

            return Response({"Program": program_list, "Sku": sku_list, "Team": team_list}, status=status.HTTP_200_OK)

        except Exception as e:
            # Log the error
            logger_error.error(str(e))
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AllYearsForecastSummary(APIView):
    def process_record(self, records, year):
        current_year = datetime.now().year
        monthly_data = [
            {
                "category": month,
                "intel": sum(int(record[month]['boardsIntelBench'] or 0) + int(record[month]['boardIntelRack'] or 0) for record in records),
                "ODC": sum(int(record[month]['boardsODCBench'] or 0) + int(record[month]['boardsODCRack'] or 0) for record in records),
                "Bench_Demand_Intel": sum(int(record[month]['boardsIntelBench'] or 0) for record in records),
                "Rack_Demand_Intel": sum(int(record[month]['boardIntelRack'] or 0) for record in records),
                "Bench_Demand_ODC": sum(int(record[month]['boardsODCBench'] or 0) for record in records),
                "Rack_Demand_ODC": sum(int(record[month]['boardsODCRack'] or 0) for record in records),
                "Total_Bench_Intel": round(sum(int(record[month]['boardsIntelBench'] or 0) / 1.5 for record in records)),
                "Total_Rack_Intel": 0,
                "Ramp_value":sum(int(record[month]['boardsIntelBench'] or 0) + int(record[month]['boardIntelRack'] or 0) for record in records)+
                            sum(int(record[month]['boardsODCBench'] or 0) + int(record[month]['boardsODCRack'] or 0) for record in records)
            }
            for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        ]
        result = {
            year: monthly_data,
        }
        return result
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            program = data.get('Program', 'All')
            sku = data.get('Sku', 'All')
            id = data.get('id')
            result = []
            years = set(BoardAllocationDataModel.objects.values_list('year', flat=True))

            for year in years:
                if id is not None:
                    try:
                        board = BoardAllocationDataModel.objects.get(pk=id, year=year)
                        serializer = BoardAllocationDataModelSerializer(board)
                        response_data = serializer.data
                        result.append(self.process_record([response_data],year))
                    except BoardAllocationDataModel.DoesNotExist:
                        return Response("Record not found for the specified year", status=status.HTTP_404_NOT_FOUND)
                else:
                    if program == 'All':
                        if sku == 'All':
                            data = BoardAllocationDataModel.objects.filter(year=year)
                        else:
                            data = BoardAllocationDataModel.objects.filter(year=year, Sku=sku)
                    else:
                        if sku == 'All':
                            data = BoardAllocationDataModel.objects.filter(year=year, Program=program)
                        else:
                            data = BoardAllocationDataModel.objects.filter(year=year, Program=program, Sku=sku)
                    serializer = BoardAllocationDataModelSerializer(data, many=True)
                    serialized_data = serializer.data
                    filtered_data = [item for item in serialized_data if not item['isdeleted']]
                    if not data.exists():
                        result.append(self.process_empty_record(year))
                    else:
                        combined_record = self.process_record(filtered_data,year)
                        result.append(combined_record)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def process_empty_record(self, year):
        empty_data = [
            {
                "category": month,
                "intel": 0,
                "ODC": 0,
                "Bench_Demand_Intel": 0,
                "Rack_Demand_Intel": 0,
                "Bench_Demand_ODC": 0,
                "Rack_Demand_ODC": 0,
                "Ramp_value":0
            }
            for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        ]
        result = {
            year: empty_data,
        }
        return result

# BROADCAST EMAIL PAGE       
class BroadCastEmail(APIView):
    def post(self, request):
        """API to store user list in BroadcastModel and trigger email"""
        try:
            # Parse request data
            location = request.data.get('Location', 'All').split(',')
            subject = request.data.get('Subject')
            content = request.data.get('Content')
            broadcast_by = request.data.get('BroadCast_by')
            created_date = datetime.now()
            new_users = request.data.get('NewUser', [])
            deleted_users = request.data.get('DeletedUser', [])

            user_email_set = set()
            user_info_dict = {}

            if 'All' in location:
                # Case 1: All users
                users = UserModel.objects.all().values('Email', 'Name', 'WWID')
                for user in users:
                    email = user['Email']
                    user_email_set.add(email)
                    user_info_dict[email] = {'WWID': user['WWID'], 'Name': user['Name']}
            else:
                # Case 2: Specific locations
                allocations = AllocationDetailsModel.objects.filter(status='allocated', Location__Name__in=location).select_related('Location')
                for allocation in allocations:
                    for allocated_user in allocation.AllocatedTo:
                        email = allocated_user.get('Email')
                        if email:
                            user_email_set.add(email)
                            if email not in user_info_dict:
                                user_info_dict[email] = {'WWID': allocated_user.get('WWID'), 'Name': allocated_user.get('Name')}

            # Remove deleted users from the email list
            for deleted_user in deleted_users:
                user_email_set.discard(deleted_user)

            # Add new users to the email list and user_info_dict
            for new_user in new_users:
                new_user_email = new_user.get('Email')
                if new_user_email:
                    user_email_set.add(new_user_email)
                    # Update user_info_dict with new user information
                    user_info_dict[new_user_email] = {
                        'WWID': new_user.get('WWID'),
                        'Name': new_user.get('Name')
                    }

            # Convert set to list for serialization
            user_email_list = list(user_email_set)

            # Join the location list into a comma-separated string
            location_str = ','.join(location)

            # Create BroadcastModel instance
            broadcast_instance = BroadcastModel.objects.create(
                Location=location_str,  # Use the joined string here
                Subject=subject,
                Content=content,
                BroadCast_by=broadcast_by,
                NewUser=new_users,
                User_mail_list=user_email_list,
                CreatedDate=created_date,
                DeletedUser=deleted_users
            )

            # Prepare response data
            response_data = {
                "Location": broadcast_instance.Location,
                "Subject": broadcast_instance.Subject,
                "Content": broadcast_instance.Content,
                "BroadCast_by": broadcast_instance.BroadCast_by,
                "CreatedDate": broadcast_instance.CreatedDate,
                "User_mail_list": user_email_list,
                "New_User": new_users,
                "DeletedUser": deleted_users
            }

            # Send email to each user in the User_mail_list
            # for email in user_email_list:
            #     user_info = user_info_dict[email]
            #     mail_data = {
            #         "WWID": user_info['WWID'],
            #         "User": user_info['Name'],
            #         "content": content,
            #         "subject": f"{subject} "
            #     }
            #     TO = [email]
            #     CC = []
            #     BCC = ["charux.saxena@intel.com"]
            #     mail = BroadcastMail(From=FROM, To=TO, CC=CC, data=mail_data, Bcc=BCC)
            #     mail.sendmail()

            return Response(response_data, status=201)
        except Exception as e:
            logging.error("An error occurred: %s", e)
            return Response({"error": str(e)}, status=400)

class GetBroadCastDetails(APIView):
    def remove_html_tags(self, text):
        text_content = ''
        image_urls = []  # Store image URLs in a list
        
        # Extract text content
        text_content_matches = re.findall(r'>([^<]+)<', text)
        text_content = ' '.join(text_content_matches)

        # Extract image URLs
        img_src_matches = re.findall(r'<img.*?src=(?:\"(.*?)\"|\'(.*?)\').*?>', text)
        for match in img_src_matches:
            image_urls.append(match[0] or match[1])

        return {'Content': text_content, 'Attachment': image_urls}
    
    def get(self, request):
        try:
            data = BroadcastModel.objects.all()
            formatted_data = []
            for item in data:
                created_date_with_offset = item.CreatedDate + timedelta(hours=5, minutes=30, seconds=10)
                created_date_formatted = created_date_with_offset.strftime('%d-%m-%Y %H:%M:%S')
                cleaned_data = self.remove_html_tags(item.Content)
                item_data = {
                    "id": item.id,
                    'Subject': item.Subject,
                    'Content': cleaned_data['Content'],  # Display text content here
                    'Attachment': cleaned_data['Attachment'],  # Display image URLs here
                    'NewUser': item.NewUser,
                    'BroadCast_by': item.BroadCast_by,
                    'CreatedDate': created_date_formatted,
                    'User_mail_list': item.User_mail_list,
                    'Content_with_html_tag': item.Content
                }
                formatted_data.append(item_data)
            return Response(formatted_data, status=status.HTTP_200_OK)
        except BroadcastModel.DoesNotExist:
            return Response("Record not found", status=status.HTTP_404_NOT_FOUND)

class LabList(APIView):
    def post(self, request):
        try:
            user_mail = request.data.get('User', 'All').split(',')
            if 'All' in user_mail:  # Case 1
                users = UserModel.objects.all().values_list('Email', flat=True)
                return Response({"User_Emails": list(users)}, status=status.HTTP_200_OK)
            else:  # Case 2
                allocated_users = set()
                allocations = AllocationDetailsModel.objects.filter(status='allocated', Location__Name__in=user_mail).select_related('Location')
                for allocation in allocations:
                    for allocated_user in allocation.AllocatedTo:
                        allocated_users.add(allocated_user.get('Email'))
                return Response({"Allocated_user_list": list(allocated_users)}, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        

class TestAPI(APIView):
    def get(self,request):
        response = {
            'content': "Testing API 5",
                }
        return Response(response, status=status.HTTP_200_OK)