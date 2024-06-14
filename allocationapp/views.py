
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
                        UserRolesModel,UserRequestModel,SuggestionsModel,ApproverUserModel,BoardAllocationDataModel,BroadcastModel
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
    def get(self,request,slug):
        if slug == "Location":
            try:
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
                                        if each_category == 'Allocated':
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated']==True and \
                                                each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
                                                counts += 1
                                                master_count += 1
                                        elif each_category == 'Unallocated':
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                                each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
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
                    Returns the Counts for Program/Location chart
                """

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
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                    if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == filter_program and \
                                                            each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Team'] == each_team:
                                                        breakdown_dict[each_filtered_program_sku] += 1
                                                        master_count += 1
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
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == program and \
                                                    each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Team'] == each_team:
                                                    breakdowncount += 1
                                                    master_count += 1
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
                query = LabModel.objects.filter()
                lab_filter_query = LabModel.objects.filter().values('Name')
                lab_filter_query_list = [each_query['Name'] for each_query in lab_filter_query if "TOE" not in each_query['Name']]
                lab_data = LabModel.objects.filter(Name__in=lab_filter_query_list).values('Name')
                lab_names_list = sorted(list(set([ '-'.join(str(each_lab['Name']).split('-')[0:2])   for each_lab in lab_data])))
                vendor_query = VendorsModel.objects.filter().values()
                vendor_names_list = list(set([each_vendor['VendorName'] for each_vendor in vendor_query]))
                filtered_vendor_names_list = vendor_names_list.copy()
                vendor_names_list.insert(0,"All")
                if query:
                    vendor_response_list =[]
                    
                    for each_vendor in vendor_names_list:
                        if each_vendor == "All":
                            master_dict = {}
                            master_count = 0
                            breakdown_list=[]
                            allocation_data = AllocationDetailsModel.objects.filter(status="allocated").order_by('-created').\
                                                            values('id','Program','Sku','Vendor','FromWW','ToWW',"Duration","AllocatedTo","NumberOfbenches","Remarks","Team",
                                                                   "Location__Name","BenchData","approvedBy")
                            report_data_list = [each_query for each_query in allocation_data]
                            for each_location in lab_names_list:
                                lab_data = LabModel.objects.filter(Name__icontains=each_location)
                                breakdown_dict = {}
                                count = 0
                                breakdown_dict['category'] = each_location
                                
                                for each_filtered_vendor in  filtered_vendor_names_list:
                                    breakdown_dict[each_filtered_vendor] = 0
                                    for each_lab in lab_data:
                                        if each_lab.BenchDetails is not None:
                                            for each_row_no in range(len(each_lab.BenchDetails)):
                                                for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                                    if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Vendor'] == each_filtered_vendor:
                                                                breakdown_dict[each_filtered_vendor] += 1
                                                                master_count += 1
                                breakdown_list.append(breakdown_dict)
                            if breakdown_list:
                                master_dict['category'] = each_vendor
                                master_dict['value'] = master_count
                                master_dict['breakdown'] = breakdown_list
                                master_dict['Report'] = report_data_list
                                vendor_response_list.append(master_dict)
                        else:
                            master_dict = {}
                            master_count = 0
                            breakdown_list=[]
                            report_data_list = [each_query for each_query in allocation_data if each_query['Vendor'] == each_vendor]
                            for each_location in lab_names_list:
                                lab_data = LabModel.objects.filter(Name__icontains=each_location)
                                breakdown_dict = {}
                                count = 0
                                for each_lab in lab_data:
                                    if each_lab.BenchDetails is not None:
                                        for each_row_no in range(len(each_lab.BenchDetails)):
                                            for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Vendor'] == each_vendor:
                                                            count += 1
                                                            master_count += 1
                                if count != 0:
                                    breakdown_dict["category"]= each_location
                                    breakdown_dict["value"] = count
                                breakdown_list.append(breakdown_dict)
                            if master_count!=0:
                                master_dict['category'] = each_vendor
                                master_dict['value'] = master_count
                                master_dict['breakdown'] = breakdown_list
                                master_dict['Report'] = report_data_list
                                vendor_response_list.append(master_dict)
                    return Response(vendor_response_list, status= status.HTTP_200_OK)
                else:
                    return Response({"Data":"No Data"}, status= status.HTTP_200_OK)
            except Exception as e:
                logger_error.error(str(e))
                return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    def get(self,request):
        """ API to get the drill down data for home page location vs counts(Allocated, Free, Non-SIV) chart """
        try:
            category_list = ["All", "Non-SIV", "Allocated", "Free"]
            lab_filter_query = LabModel.objects.filter().values('Name')
            lab_filter_query_list = [each_query['Name'] for each_query in lab_filter_query if "TOE" not in each_query['Name']]
            lab_data = LabModel.objects.filter(Name__in=lab_filter_query_list).values('Name')
            lab_names_list = sorted(list(set([ '-'.join(str(each_lab['Name']).split('-')[0:2])   for each_lab in lab_data])))
            master_list = []
            allocation_data = AllocationDetailsModel.objects.filter(status="allocated").order_by('-created').\
                                                            values('id','Program','Sku','Vendor','FromWW','ToWW',"Duration","AllocatedTo","NumberOfbenches","Remarks","Team",
                                                                   "Location__Name","BenchData","approvedBy")
            for each_category in category_list:
                if each_category=="All":
                    master_dict = {}
                    master_dict['category'] = each_category
                    breakdown_list = []
                    report_list = []
                    report_dict = {}
                    report_allocation_data = [each_query for each_query in allocation_data]
                    report_dict['Allocated'] = report_allocation_data
                    report_dict['Free'] = []
                    report_dict['Non-SIV'] = []
                    master_count = 0
                    free_report_dict = {}
                    non_siv_report_dict = {}
                    for each_location in lab_names_list:
                        lab_data = LabModel.objects.filter(Name__icontains=each_location)
                        counts_dict={}
                        # for free benches report
                        if each_location not in free_report_dict.keys():
                            free_report_dict[each_location] =[]

                        if each_location not in non_siv_report_dict.keys():
                            non_siv_report_dict[each_location] = []
                        non_siv_count = 0
                        allocated_count = 0
                        free_count = 0
                        free_report_lab_dict = {}
                        non_siv_report_lab_dict = {}
                        for each_lab in lab_data:
                            if (each_lab.BenchDetails is not None) and ("TOE" not in each_lab.Name):
                                if each_lab.Name not in free_report_lab_dict.keys():
                                    free_report_lab_dict[each_lab.Name] = []
                                if each_lab.Name not in non_siv_report_lab_dict.keys():
                                    non_siv_report_lab_dict[each_lab.Name] = []
                                for each_row_no in range(len(each_lab.BenchDetails)):
                                    for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                        # if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                        #     each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "Non-SIV":
                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "Non-SIV":
                                            non_siv_count += 1
                                            non_siv_report_lab_dict[each_lab.Name].append(each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['labelNo'])
                                            master_count+=1
                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] and \
                                            each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
                                            allocated_count += 1
                                            master_count += 1
                                        elif each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                            each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "Non-SIV":
                                            #allocated_count += 1
                                            master_count += 1
                                        elif each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                            each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
                                            free_count += 1
                                            master_count += 1
                                            free_report_lab_dict[each_lab.Name].append(each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['labelNo'])
                        if free_report_lab_dict:
                            free_report_dict[each_location].append(free_report_lab_dict)
                        if non_siv_report_lab_dict:
                            non_siv_report_dict[each_location].append(non_siv_report_lab_dict)
                        counts_dict['category'] = each_location
                        counts_dict['Non-SIV'] = non_siv_count
                        counts_dict['Allocated'] = allocated_count
                        counts_dict['Free'] = free_count
                        breakdown_list.append(counts_dict)
                    report_dict['Free'].append(free_report_dict)
                    report_dict['Non-SIV'].append(non_siv_report_dict)
                    report_list.append(report_dict)
                    # print(free_count + non_siv_count + allocated_count)
                    
                    # print(master_count)

                    if breakdown_list:
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                    if report_list:
                        master_dict['Report'] = report_list
                    master_list.append(master_dict)

                else:
                    # This section executes Allocated, Free, Non-SIV categories
                    master_dict={}
                    master_dict['category'] = each_category
                    breakdown_list = []
                    if each_category == "Allocated":
                        report_allocation_data = [each_query for each_query in allocation_data]
                        master_dict['Report'] = report_allocation_data
                    else:
                        report_list = []
                        report_dict = {}
                    master_count = 0
                    for each_location in lab_names_list:
                        if each_category != "Allocated":
                            if each_location not in report_dict.keys():
                                report_dict[each_location] = []
                        lab_data = LabModel.objects.filter(Name__icontains=each_location)
                        counts_dict = {}
                        count = 0
                        if each_category != "Allocated":
                            report_category_dict = {}
                            
                        for each_lab in lab_data:
                            if (each_lab.BenchDetails is not None) and ("TOE" not in each_lab.Name):
                                if each_category != "Allocated":
                                    if each_lab.Name not in report_category_dict.keys():
                                        report_category_dict[each_lab.Name] = []
                                for each_row_no in range(len(each_lab.BenchDetails)):
                                    for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                        if each_category=='Non-SIV':
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "Non-SIV":
                                                count += 1
                                                # append the seat numbers for dispalying in the report
                                                report_category_dict[each_lab.Name].append(each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['labelNo'])
                                                master_count += 1
                                        elif each_category == 'Allocated':
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated']==True and \
                                            each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
                                                count += 1
                                                master_count += 1
                                            elif each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] and \
                                            each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "Non-SIV":
                                                count += 1
                                                master_count += 1


                                        elif each_category == 'Free':
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['IsAllocated'] == False and \
                                            each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['team'] == "SIV":
                                                # append the seat numbers for dispalying in the report
                                                report_category_dict[each_lab.Name].append(each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['labelNo'])
                                                count += 1
                                                master_count += 1
                                        
                            counts_dict["category"]= each_location
                            counts_dict["value"] = count
                        if each_category != "Allocated":
                            report_dict[each_location].append(report_category_dict)
                        breakdown_list.append(counts_dict)
                    master_dict['value'] = master_count
                    master_dict['breakdown'] = breakdown_list
                    if each_category != "Allocated":
                        master_dict['Report'] = report_dict
                    master_list.append(master_dict)
            return Response(master_list,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

class TeamDrillDownView(APIView):
    def get(self,request):
        """ APi to get the drill down data for team vs location chart"""
        try:
            lab_filter_query = LabModel.objects.filter().values('Name')
            lab_filter_query_list = [each_query['Name'] for each_query in lab_filter_query if "TOE" not in each_query['Name']]
            lab_data = LabModel.objects.filter(Name__in=lab_filter_query_list).values('Name')
            lab_names_list = sorted(list(set([ '-'.join(str(each_lab['Name']).split('-')[0:2])   for each_lab in lab_data])))
            teams_list = TeamsModel.objects.filter().values('TeamName')
            teams_list = sorted(list(set([ each_team['TeamName'] for each_team in teams_list])))
            filtered_teams_list = teams_list.copy()
            teams_list.insert(0,'All')
            response_team_list = []
            allocation_data = AllocationDetailsModel.objects.filter(status="allocated").order_by('-created').\
                                                            values('id','Program','Sku','Vendor','FromWW','ToWW',"Duration","AllocatedTo","NumberOfbenches","Remarks","Team",
                                                                   "Location__Name","BenchData","approvedBy")
            for each_team in teams_list:
                if each_team == "All":
                    master_dict = {}
                    master_count=0              
                    breakdown_list = []
                    report_allocation_data = [each_query for each_query in allocation_data]
                    for each_location in lab_names_list:
                        lab_data = LabModel.objects.filter(Name__icontains=each_location)
                        breakdown_dict = {}
                        for each_filtered_team in filtered_teams_list:
                            breakdown_dict[each_filtered_team] = 0
                            for each_lab in lab_data:
                                if (each_lab.BenchDetails is not None) and ("TOE" not in each_lab.Name):
                                    for each_row_no in range(len(each_lab.BenchDetails)):
                                        for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                 if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Team'] == each_filtered_team:
                                                    if each_filtered_team not in breakdown_dict.keys():
                                                        breakdown_dict[each_filtered_team] = 1
                                                        master_count += 1
                                                    else:
                                                        breakdown_dict[each_filtered_team] += 1
                                                        master_count += 1
                            if breakdown_dict[each_filtered_team] == 0:
                                breakdown_dict.pop(each_filtered_team)
                        if breakdown_dict:
                            breakdown_dict['category'] = each_location
                            breakdown_list.append(breakdown_dict)
                    if breakdown_list:
                        master_dict['category'] = each_team
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        if report_allocation_data:
                            master_dict['Report'] = report_allocation_data
                        else:
                            master_dict['Report'] = []
                        response_team_list.append(master_dict)
                else:
                    master_dict ={}
                    master_count = 0
                    breakdown_list = []
                    report_allocation_data = [each_query for each_query in allocation_data if each_query['Team'] == each_team]
                    for each_location in lab_names_list:
                        lab_data = LabModel.objects.filter(Name__icontains=each_location)
                        breakdown_dict = {}
                        count = 0
                        for each_lab in lab_data:
                            if (each_lab.BenchDetails is not None) and ("TOE" not in each_lab.Name):
                                for each_row_no in range(len(each_lab.BenchDetails)):
                                    for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Team'] == each_team:
                                                    count += 1
                                                    master_count += 1
                        if count != 0:
                            breakdown_dict["category"]= each_location
                            breakdown_dict["value"] = count
                            breakdown_list.append(breakdown_dict)
                    if master_count != 0:
                        master_dict['category'] = each_team
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        master_dict['Report'] = report_allocation_data
                        response_team_list.append(master_dict)
            return Response(response_team_list,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProgramDrillDownView(APIView):
    def get(self, request):
        """API to get drill down data for Program vs Location chart"""
        try:
            lab_filter_query = LabModel.objects.filter().values('Name')
            lab_filter_query_list = [each_query['Name'] for each_query in lab_filter_query if "TOE" not in each_query['Name']]
            lab_data = LabModel.objects.filter(Name__in=lab_filter_query_list).values('Name')
            lab_names_list = sorted(list(set(['-'.join(str(each_lab['Name']).split('-')[0:2]) for each_lab in lab_data])))
            sku_list = SkuModel.objects.select_related('ProgramName__ProgramShortName').filter().values('ProgramName__ProgramShortName')
            program_sku_list = [each_program_sku['ProgramName__ProgramShortName'] for each_program_sku in sku_list]
            program_sku_list = [*set(program_sku_list)]
            filter_program_sku_list = program_sku_list.copy()
            program_sku_list.insert(0, "All")
            
            master_list = []
            allocation_data = AllocationDetailsModel.objects.filter(status="allocated").order_by('-created').values(
                'id', 'Program', 'Sku', 'Vendor', 'FromWW', 'ToWW', "Duration", "AllocatedTo", "NumberOfbenches", "Remarks",
                "Team", "Location__Name", "BenchData", "approvedBy")
            
            for each_program_sku in program_sku_list:
                if each_program_sku == "All":
                    master_dict = {}
                    master_count = 0 
                    breakdown_list = []
                    report_data_list = [each_query for each_query in allocation_data]
                    
                    for each_location in lab_names_list:
                        lab_data = LabModel.objects.filter(Name__icontains=each_location)
                        breakdown_dict = {}
                        breakdown_dict['category'] = each_location
                        count = 0
                        
                        for each_filter_program_sku in filter_program_sku_list:
                            breakdown_dict[each_filter_program_sku] = 0
                            program = each_filter_program_sku
                            
                            for each_lab in lab_data:
                                if each_lab.BenchDetails is not None and "TOE" not in each_lab.Name:
                                    for each_row_no in range(len(each_lab.BenchDetails)):
                                        for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == program:
                                                    breakdown_dict[each_filter_program_sku] += 1
                                                    master_count += 1
                                                    
                            if breakdown_dict[each_filter_program_sku] == 0:
                                breakdown_dict.pop(each_filter_program_sku)
                        breakdown_list.append(breakdown_dict)
                    
                    if breakdown_list:
                        master_dict['category'] = str(each_program_sku)
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        master_dict['Report'] = report_data_list
                        master_list.append(master_dict)
                
                else:
                    master_dict = {}
                    master_count = 0
                    breakdown_list = []
                    program = each_program_sku
                    report_data_list = [each_query for each_query in allocation_data if each_query['Program'] == program]
                    
                    for each_location in lab_names_list:
                        lab_data = LabModel.objects.filter(Name__icontains=each_location)
                        breakdown_dict = {}
                        count = 0
                        
                        for each_lab in lab_data:
                            if each_lab.BenchDetails is not None and "TOE" not in each_lab.Name:
                                for each_row_no in range(len(each_lab.BenchDetails)):
                                    for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == program:
                                                count += 1
                                                master_count += 1
                                                
                        if count != 0:
                            breakdown_dict['category'] = each_location
                            breakdown_dict['value'] = count
                            breakdown_list.append(breakdown_dict)
                    
                    if breakdown_list:
                        master_dict['category'] = each_program_sku
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        master_dict['Report'] = report_data_list
                        master_list.append(master_dict)
            
            return Response(master_list, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProgramVendorView(APIView):
    def get(self,request):  
        """
        API to get drilldown chart data for Proram vs Vendor chart
        """
        try:
            sku_list = SkuModel.objects.select_related('ProgramName__ProgramShortName').filter().values('ProgramName__ProgramShortName')
            program_sku_list = [each_program_sku['ProgramName__ProgramShortName'] for each_program_sku in sku_list]
            program_sku_list = [*set(program_sku_list)]
            filter_program_sku_list = program_sku_list.copy()
            program_sku_list.insert(0, "All")
            
            master_list = []
            vendor_query = VendorsModel.objects.filter().values('VendorName')
            vendor_list = [each_vendor['VendorName'] for each_vendor in vendor_query]
            lab_data = LabModel.objects.filter()
            master_list = []
            
            for each_program_sku in program_sku_list:
                if each_program_sku == "All":
                    master_dict = {}
                    master_count = 0 
                    breakdown_list = []
                    for each_vendor in vendor_list:
                        breakdown_dict={}
                        for each_filter_program_sku in filter_program_sku_list:
                            breakdown_dict[each_filter_program_sku] = 0
                            program = each_filter_program_sku
                            
                            for each_lab in lab_data:
                                if each_lab.BenchDetails is not None and "TOE" not in each_lab.Name:
                                    for each_row_no in range(len(each_lab.BenchDetails)):
                                        for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                            if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == program and \
                                                        each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Vendor'] == each_vendor:
                                                    breakdown_dict[each_filter_program_sku] += 1
                                                    master_count += 1
                            if breakdown_dict[each_filter_program_sku] == 0:
                                breakdown_dict.pop(each_filter_program_sku)
                        if breakdown_dict:
                                breakdown_dict['category'] = each_vendor
                                breakdown_list.append(breakdown_dict)
                    if breakdown_list:
                        master_dict['category'] = each_program_sku
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        master_list.append(master_dict)                        
                
                else:
                    master_dict = {}
                    master_count = 0
                    breakdown_list = []
                    program = each_program_sku
                    lab_data = LabModel.objects.filter()
                    for each_vendor in vendor_list:
                        breakdown_dict = {}
                        breakdowncount = 0
                        for each_lab in lab_data:
                            if (each_lab.BenchDetails is not None) and ("TOE" not in each_lab.Name):
                                for each_row_no in range(len(each_lab.BenchDetails)):
                                    for each_bench_no in range(len(each_lab.BenchDetails[each_row_no]['seats'])):
                                        if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData']:
                                                if each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Program'] == program and \
                                                    each_lab.BenchDetails[each_row_no]['seats'][each_bench_no]['AllocationData'][0]['Vendor'] == each_vendor:
                                                    breakdowncount += 1
                                                    master_count += 1
                        if breakdowncount != 0:
                            breakdown_dict['category'] = each_vendor
                            breakdown_dict['value'] = breakdowncount
                            breakdown_list.append(breakdown_dict)
                    if breakdown_list:
                        master_dict['category'] = each_program_sku
                        master_dict['value'] = master_count
                        master_dict['breakdown'] = breakdown_list
                        master_list.append(master_dict)
            
            return Response(master_list, status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        View For get the details of the requested lab for Approve page
    """
    def post(self, request):
        data = request.data['LabName']
        try:
            labdetail = LabModel.objects.filter(Name=str(data)).values()
            if labdetail:
                lab_data = dict(labdetail[0]) 
                # Calculate Allocated Count
                lab_data['NonSIVCounts'] = 0
                lab_data['SIVAllocated'] = 0
                lab_data['SIVFree'] = 0
                lab_data["SIVCounts"] = 0
                if labdetail[0]['BenchDetails'] is not None:
                    allocated_count = 0
                    non_siv_count = 0
                    total_siv_count = 0
                    for each_bench_row in range(len(labdetail[0]['BenchDetails'])):
                        for each_column_no in range(len(labdetail[0]['BenchDetails'][each_bench_row]['seats'])):
                            if labdetail[0]['BenchDetails'][each_bench_row]['seats'][each_column_no]['IsAllocated']:
                                allocated_count += 1
                            if labdetail[0]['BenchDetails'][each_bench_row]['seats'][each_column_no]['team'] == 'Non-SIV':
                                non_siv_count += 1
                            elif labdetail[0]['BenchDetails'][each_bench_row]['seats'][each_column_no]['team'] == 'SIV':
                                total_siv_count += 1
                    lab_data['NonSIVCounts'] = non_siv_count
                    lab_data['SIVAllocated'] = allocated_count
                    lab_data["SIVCounts"] = total_siv_count
                    #lab_data['SIVFree'] = total_siv_count-allocated_count
                    siv_free = total_siv_count - allocated_count
                    lab_data['SIVFree'] = max(siv_free, 0)
                    lab_data["NumberOfWorkbenches"] = non_siv_count + total_siv_count
                    return Response(lab_data,status=status.HTTP_200_OK)
                else:
                    logger_error.error(str("Lab Not Exist"))
                    return Response("Info! Lab Does Not Exist",status=status.HTTP_404_NOT_FOUND)
            else:
                logger_error.error(str("Lab Not Exist"))
                return Response("Info! Lab Does Not Exist",status=status.HTTP_404_NOT_FOUND)
        except LabModel.DoesNotExist:
            logger_error.error("Lab Not Exist")
            return Response("Error",status=status.HTTP_404_NOT_FOUND)

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
            except LabModel.DoesNotExist:
                    return Response("Lab DoesNotExist!!",status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger_error.error(str(e))
                return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                allocation_query = AllocationDetailsModel.objects.get(Program=data['Program'], Sku=data['Sku'], Vendor=data['Vendor'], \
                    AllocatedTo=data['AllocatedTo'], NotifyTo=data['NotifyTo'], FromWW=data['FromWW'], ToWW=data['ToWW'], \
                    NumberOfbenches=data['NumberOfBenches'], Team=data['Team'], Remarks=data['Remarks'], Location=lab_data, \
                    BenchData=data['BenchData'], Duration=data['Duration'], status='requested')
                return Response("Allocation Exists", status=status.HTTP_200_OK)
            except AllocationDetailsModel.DoesNotExist:
                allocation_detail = AllocationDetailsModel(id=id,Program=data['Program'],Sku=data['Sku'],Vendor=data['Vendor'],\
                    AllocatedTo=data['AllocatedTo'],NotifyTo=data['NotifyTo'],FromWW=data['FromWW'],ToWW=data['ToWW'],NumberOfbenches=data['NumberOfBenches'],
                    Team=data['Team'],AllocatedDate=None,Remarks=data['Remarks'],Location=lab_data,
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
                            "vendor":vendor,
                            "allocatedto":allocatedTo[0]['Name'],
                            "notifyto":','.join(notify_persons),
                            "requestedBy":RequestedBy[0]['Name'],
                            "fromww":fromWW,
                            "toww":toWW,
                            "duration":duration,
                            "remarks":remarks,
                            "team":team,
                            "numberofbenches":numberofbenches,
                            "bench_data":bench_data,
                            "message":message,
                            "subject":subject,
                            "deallocatedby":None
                        }
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
                    try:
                        # Check if Bench Exists If exists change the bench status else create new bench 
                        query = LabModel.objects.get(Q(Name=data['LabName']))
                        for each_bench_row in query.BenchDetails:
                            for each_bench_column in range(len(each_bench_row['seats'])):
                                if each_bench_row['seats'][each_bench_column]['labelNo'] == each_bench_request:
                                    each_bench_row['seats'][each_bench_column]['IsRequested'] = data['IsRequested']
                                    each_bench_row['seats'][each_bench_column]['IsAllocated'] = data['IsAllocated']
                                    each_bench_row['seats'][each_bench_column]['AllocationData'] = None
                                    query.save()
                    except LabModel.DoesNotExist:
                        return Response("Lab DoesNotExist!!",status=status.HTTP_404_NOT_FOUND)  
                return Response("Allocation Request Added Successfully",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeallocateBenchesView(APIView):
    def get(self,request):
        """ API to list all allocations"""
        try:
            allocated_data = AllocationDetailsModel.objects.filter(IsAllocated__in=['True']).values('id','Program','Sku','Vendor','FromWW',
            'ToWW','Duration','AllocatedTo','NotifyTo','NumberOfbenches','Remarks','Team','IsAllocated','IsRequested','Location__Name','BenchData','AllocatedDate','status','DeallocatedBy')
            allocated_data_list = [each_allocation for each_allocation in allocated_data]
            return  Response(allocated_data_list,status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)     
    
    def post(self,request):
        """ API to deallocate benches manually"""
        data = request.data

        # CHANGES
        user_name = data[0]["DeallcationUserInfo"]["name"]
        user_email = data[0]["DeallcationUserInfo"]["emailId"]
        allocation_time = data[0]["DateandTime"]

        # # Print the extracted values
        # print("User Name:", user_name)
        # print("Allocation Time:", allocation_time)
        try:
            lab_name = data[0]['LabName']
            reason = data[0]['Reason']
            # changes
            user_name = data[0]["DeallcationUserInfo"]["name"]
            user_email = data[0]["DeallcationUserInfo"]["emailId"]
            allocation_time = data[0]["DateandTime"]

            lab_data = LabModel.objects.get(Q(Name=lab_name))
            for each_data in data:
                id = each_data['id']
                bench_data = each_data['BenchData'][0]
                allocation_data = AllocationDetailsModel.objects.get(id=id)
                if bench_data in allocation_data.BenchData:
                    allocation_data.BenchData.remove(bench_data)
                    allocation_data.DeallocatedBenchData.append(bench_data)
                    allocation_data.DeallocatedBy = user_name
                    allocation_data.deallocatedDate = allocation_time
                    allocation_data.save()
                    # If all benches are deallocated
                    if not allocation_data.BenchData:
                        allocation_data.IsAllocated = False
                        allocation_data.IsRequested = False
                        allocation_data.status = "complete"
                        allocation_data.BenchData = allocation_data.DeallocatedBenchData
                        allocation_data.Reason = str(bench_data) + ":" +str(reason) + str(allocation_data.Reason)
                        # changes
                        allocation_data.DeallocatedBy = user_name
                        allocation_data.deallocatedDate = datetime.now()
                        allocation_data.save()
                        for each_bench_row in lab_data.BenchDetails:
                            for each_bench_column_no in range(len(each_bench_row['seats'])):
                                if each_bench_row['seats'][each_bench_column_no]['labelNo'] == bench_data:
                                    each_bench_row['seats'][each_bench_column_no]['IsRequested'] = False
                                    each_bench_row['seats'][each_bench_column_no]['IsAllocated'] = False
                                    each_bench_row['seats'][each_bench_column_no]['AllocationData'] = None
                                    lab_data.save()
                    else:
                        for each_bench_row in lab_data.BenchDetails:
                            for each_bench_column_no in range(len(each_bench_row['seats'])):
                                if each_bench_row['seats'][each_bench_column_no]['labelNo'] == bench_data:
                                    each_bench_row['seats'][each_bench_column_no]['IsRequested'] = False
                                    each_bench_row['seats'][each_bench_column_no]['IsAllocated'] = False
                                    each_bench_row['seats'][each_bench_column_no]['AllocationData'] = None
                                    lab_data.save()
                    try:
                        notify_persons = []
                        if  allocation_data.NotifyTo is not None:     
                            notify_persons = allocation_data.NotifyTo
                            notify_emails = allocation_data.NotifyTo
                        else:
                            notifyTo = None
                            notify_persons =[]
                            notify_emails = []
                    except Exception as e:
                        notifyTo = None
                        notify_persons =[]
                        notify_emails = []
                    message = f"This email is a confirmation of your Lab Bench <b>Deallocated<b> for reason {reason}"
                    subject = "Bench request Deallocated for "
                    mail_data = {
                                "User":allocation_data.AllocatedTo[0]['Name'],
                                "WWID":allocation_data.AllocatedTo[0]['WWID'],
                                "program":allocation_data.Program,
                                "sku":allocation_data.Sku,
                                "lab_name":lab_name,
                                "vendor":allocation_data.Vendor,
                                "allocatedto":allocation_data.AllocatedTo[0]['Name'],
                                "notifyto":','.join(notify_persons),
                                "requestedBy":allocation_data.RequestedBy[0]['Name'],
                                "fromww":str(allocation_data.FromWW),
                                "toww":str(allocation_data.ToWW),
                                "duration":allocation_data.Duration,
                                "remarks":allocation_data.Remarks,
                                "team":allocation_data.Team,
                                "id":id,
                                "numberofbenches":allocation_data.NumberOfbenches,
                                "bench_data":[bench_data],
                                "message":message,
                                "subject":subject,
                                "deallocatedby":allocation_data.DeallocatedBy,
                            }
                    TO.append(str(allocation_data.AllocatedTo[0]['Email']))
                    if notify_emails:
                        Cc = notify_emails
                    else:
                        Cc = []
                    Cc.append(user_email)
                    Cc = Cc+CC
                    mail = Email(FROM,TO,Cc,mail_data)
                    mail.sendmail()
                    TO.pop()           
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetProgramDetailsView(APIView):
    def get(self, request):
        """"
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

# Approve Page

class ApproveViewPage(APIView):
    def get(self, request):
        """
            View that Lists all Bench Request
        """
        try:
            pending_data = AllocationDetailsModel.objects.filter(Q(IsAllocated__in=[False]) & Q(IsRequested__in=[True])).order_by('-created').values('id','Program','Sku','Vendor','FromWW',
            'ToWW','Duration','AllocatedTo','NotifyTo','NumberOfbenches','Team','Remarks','IsAllocated','IsRequested','Location__Name','BenchData','RequestedBy','RequestedDate','DeallocatedBy','deallocatedDate')
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
                    duration = allocation_query.Duration
                    bench_data = allocation_query.BenchData
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
                                "vendor":vendor,
                                "allocatedto":allocatedTo[0]['Name'],
                                "notifyto":','.join(notify_persons),
                                "requestedBy":RequestedBy[0]['Name'],
                                "fromww":fromWW,
                                "toww":toWW,
                               "duration":duration,
                                "remarks":remarks,
                                "team":team,
                                "numberofbenches":numberofbenches,
                                "bench_data":bench_data,
                                "message":message,
                                "subject":subject,
                                "deallocatedby":""
                            }
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
                            for each_bench_request in bench_data:
                                try:
                                    # Check if Bench Exists If exists change the bench status else create new bench 
                                    lab_query = LabModel.objects.get(Q(Name=location))
                                    for each_bench_row in lab_query.BenchDetails:
                                        for each_bench_column_no in range(len(each_bench_row['seats'])):
                                            if each_bench_row['seats'][each_bench_column_no]['labelNo'] == each_bench_request:
                                                each_bench_row['seats'][each_bench_column_no]['IsRequested'] = False
                                                each_bench_row['seats'][each_bench_column_no]['IsAllocated'] = True
                                                temp_dict ={}
                                                temp_dict['id'] = id
                                                temp_dict['Program'] = program
                                                temp_dict['SKU'] = sku
                                                temp_dict['Vendor'] = vendor
                                                temp_dict['Who'] = allocatedTo
                                                temp_dict['FromWW'] = fromWW
                                                temp_dict['ToWW']  = toWW
                                                temp_dict['Team'] = team
                                                temp_dict['Duration'] = duration
                                                temp_dict['Remarks'] = remarks
                                                each_bench_row['seats'][each_bench_column_no]['AllocationData'] = [temp_dict]
                                                lab_query.save()
                                                #Since key is unique break from loop once data gets updated
                                        #Since row key is unique break from the loop once data match happened 
                                except LabModel.DoesNotExist:
                                        pass
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
                    bench_data = allocation_query.BenchData
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
                        "vendor":vendor,
                        "allocatedto":allocatedTo[0]['Name'],
                        "notifyto":','.join(notify_persons),
                        "fromww":fromWW,
                        "toww":toWW,
                        "duration":duration,
                        "remarks":remarks,
                        "team":team,
                        "numberofbenches":numberofbenches,
                        "bench_data":bench_data,
                        "message":message,
                        "subject":subject
                    }
                        
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
                    bench_data = allocation_query.BenchData
                    for each_bench_request in bench_data:
                        try:
                            # Check if Bench Exists If exists change the bench status else create new bench 
                            lab_query = LabModel.objects.get(Q(Name=location))
                            for each_bench_row in lab_query.BenchDetails:
                                for each_bench_column_no in range(len(each_bench_row['seats'])):
                                    if each_bench_row['seats'][each_bench_column_no]['labelNo'] == each_bench_request :
                                        each_bench_row['seats'][each_bench_column_no]['IsRequested'] = False
                                        each_bench_row['seats'][each_bench_column_no]['IsAllocated'] = False
                                        each_bench_row['seats'][each_bench_column_no]['AllocationData'] = None
                                        lab_query.save()
                                        #Since key is unique break from loop once data gets updated
                                    #Since row key is unique bre
                                    # ak from the loop once data match happened 
                        except LabModel.DoesNotExist:
                                pass
            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
        """
            API for Rejecting multiple bench requests
        """
        # data = request.data["id"]
        data1 = request.data

        try:
            for each_data in data1:
                if True:
                    # If the request is Rejected
                    id = each_data["id"]
                    allocation_query = AllocationDetailsModel.objects.get(id=id)
                    allocation_query.Program = each_data['Program']
                    allocation_query.Sku = each_data['Sku']
                    allocation_query.Vendor = each_data['Vendor']
                    allocation_query.FromWW = each_data['FromWW']
                    allocation_query.ToWW = each_data['ToWW']
                    allocation_query.Duration = each_data['Duration']
                    allocation_query.Team = each_data['Team']
                    allocation_query.Remarks = each_data['Remarks']
                    allocation_query.save()

            return Response("Success",status=status.HTTP_200_OK)
        except Exception as e:
            logger_error.error(str(e))
            return Response(e,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Report PAge
class ReportPageView(APIView):
     def get(self, request):
        """API used in the report page to generate all allocation data"""
        try:
            pending_data = AllocationDetailsModel.objects.filter().order_by('-created').values('id', 'Program', 'Sku', 'Vendor', 'FromWW',
                                                                                                'ToWW', 'Duration', 'AllocatedTo', 'NumberOfbenches', 'Remarks', 'Team', 'IsAllocated', 'IsRequested', 'Location__Name', 'BenchData', 'AllocatedDate', 'status', 'approvedBy', 'RejectedBy', 'RequestedBy', 'RequestedDate', 'RejectedDate', 'DeallocatedBy', 'deallocatedDate', 'Reason')
            if pending_data is not None:
                for item in pending_data:
                    # Format AllocatedDate field
                    if 'AllocatedDate' in item:
                        allocated_date_str = str(item['AllocatedDate'])  # Convert to string
                        allocated_date_obj = datetime.strptime(allocated_date_str, '%Y-%m-%d %H:%M:%S.%f%z')
                        date_with_offset = allocated_date_obj + timedelta(hours=5, minutes=30, seconds=10)
                        item['AllocatedDate'] = date_with_offset.strftime('%d-%m-%Y %H:%M:%S')
                        item['RequestedDate'] = date_with_offset.strftime('%d-%m-%Y %H:%M:%S')
                        item['deallocatedDate'] = date_with_offset.strftime('%d-%m-%Y %H:%M:%S')
                        item['RejectedDate'] = date_with_offset.strftime('%d-%m-%Y %H:%M:%S')

                return Response(pending_data, status=status.HTTP_200_OK)
            else:
                return Response([], status=status.HTTP_404_NOT_FOUND)
        except AllocationDetailsModel.DoesNotExist:
            logger_error.error(str("Allocation Data not Exists!!"))
            return Response("Allocation Data not Exists!!", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            'ToWW','Duration','AllocatedTo','NotifyTo','NumberOfbenches','Remarks','Team','IsAllocated','IsRequested','Location__Name','BenchData','AllocatedDate','status')
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
            'content': "Testing API 4",
                }
        return Response(response, status=status.HTTP_200_OK)